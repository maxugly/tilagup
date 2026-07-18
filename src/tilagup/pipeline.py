"""Stage machine for a tilagup run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tilagup import log
from tilagup.agents import build_agents, pick_for_index
from tilagup.archive import (
    RunArchive,
    atomic_write_json,
    atomic_write_text,
    create_run,
    open_run,
    utc_now,
)
from tilagup.clip_fit import token_len
from tilagup.job_status import JobTracker, get_tracker, set_tracker
from tilagup.prompts_lib import (
    BASE_SYSTEM,
    DEFAULT_NEGATIVE,
    base_user_message,
    tile_user_message,
)
from tilagup.tiles import compute_tiles, export_crops, load_image_size

# CLIP budget — agents must land under this; we retry once if not
MAX_PROMPT_TOKENS = 75
MAX_PROMPT_WORDS = 50


def _source_path(arch: RunArchive, data: dict[str, Any]) -> Path:
    rel = data["source"]["path"]
    return arch.root / rel


def stage_base_prompt(arch: RunArchive, *, force: bool = False, timeout_s: float = 300.0) -> None:
    tr = get_tracker()
    data = arch.load()
    if data.get("base_prompt") and data["base_prompt"].get("text") and not force:
        log.say("skip base prompt (already present)")
        arch.event("skip_base_prompt", reason="already_present")
        if tr:
            tr.stage_start("base_prompt")
            tr.stage_end("base_prompt", skipped=True)
        return

    if tr:
        tr.stage_start("base_prompt")
    cfg = data["config"]
    agents = build_agents(
        cfg.get("agent", "both"),
        agy_model=cfg.get("agy_model"),
        grok_model=cfg.get("grok_model"),
    )
    agent = pick_for_index(agents, 0)
    src = _source_path(arch, data)
    user = (
        BASE_SYSTEM
        + "\n\n"
        + base_user_message(str(src.resolve()))
    )
    log.banner(f"base prompt via {agent.name}")
    log.kv("image", src)
    log.kv("timeout_s", timeout_s)
    arch.event("base_prompt_start", agent=agent.name)
    result = agent.complete(user, timeout_s=timeout_s)
    result = _ensure_short_prompt(
        agent,
        result,
        kind="base",
        timeout_s=timeout_s,
    )
    attribution = {
        "agent": result.agent,
        "cli": result.cli,
        "model": result.model,
        "duration_ms": result.duration_ms,
        "created_at": utc_now(),
    }
    data = arch.load()
    data["base_prompt"] = {
        "text": result.text,
        "attribution": attribution,
        "token_len": token_len(result.text),
    }
    used = set(data.get("agents_used") or [])
    used.add(result.agent)
    data["agents_used"] = sorted(used)
    data["stage"] = "base_prompt"
    arch.save(data)
    atomic_write_text(arch.root / "base_prompt.txt", result.text)
    log.say(
        f"base prompt written words={len(result.text.split())} "
        f"clip_tokens≈{token_len(result.text)} agent={result.agent}"
    )
    log.dump("BASE PROMPT (full)", result.text)
    arch.event("base_prompt_done", agent=result.agent, chars=len(result.text))
    if tr:
        tr.stage_end("base_prompt")


def _ensure_short_prompt(agent, result, *, kind: str, timeout_s: float):
    """If agent returned a CLIP-overflow essay, one hard rewrite pass."""
    words = len(result.text.split())
    toks = token_len(result.text)
    if words <= MAX_PROMPT_WORDS and toks <= MAX_PROMPT_TOKENS:
        return result
    log.say(
        f"{kind} prompt too long (words={words} clip_tokens≈{toks}) — "
        f"asking {agent.name} to rewrite short, unique-first"
    )
    rewrite = (
        f"Rewrite this Stable Diffusion prompt to ≤{MAX_PROMPT_WORDS} words "
        f"and ≤{MAX_PROMPT_TOKENS} CLIP tokens. Keep the MOST SPECIFIC / UNIQUE "
        f"details first; drop restated global fluff. Comma phrases ok. "
        f"Return ONLY the new prompt.\n\nORIGINAL:\n{result.text}"
    )
    try:
        result2 = agent.complete(rewrite, timeout_s=timeout_s)
        log.say(
            f"rewrite: words={len(result2.text.split())} "
            f"clip_tokens≈{token_len(result2.text)}"
        )
        return result2
    except Exception as e:
        log.say(f"rewrite failed ({e}); keeping original (will CLIP-fit at upscale)")
        return result


def clear_tile_prompts(arch: RunArchive) -> int:
    """Wipe tile prompts so they can be regenerated (keeps crops + base)."""
    data = arch.load()
    n = 0
    for t in data.get("tiles") or []:
        if t.get("prompt") or t.get("status") == "prompted":
            n += 1
        t["prompt"] = None
        t["attribution"] = None
        t["status"] = "pending"
        t["error"] = None
        # remove sidecar texts so nothing stale confuses inspection
        for key in ("prompt_path", "meta_path"):
            rel = t.get(key)
            if rel:
                p = arch.root / rel
                if p.is_file():
                    p.unlink()
    data["stage"] = "split"
    data["output"] = None
    arch.save(data)
    log.say(f"cleared {n} tile prompts (crops + base kept)")
    arch.event("tile_prompts_cleared", count=n)
    return n


def stage_split(arch: RunArchive, *, force: bool = False) -> None:
    tr = get_tracker()
    data = arch.load()
    if data.get("tiles") and not force:
        log.say(f"skip split ({len(data['tiles'])} tiles already present)")
        arch.event("skip_split", reason="tiles_already_present", count=len(data["tiles"]))
        if tr:
            tr.set_n_tiles(len(data["tiles"]))
            tr.stage_start("split")
            tr.stage_end("split", skipped=True)
        return
    if tr:
        tr.stage_start("split")

    cfg = data["config"]
    src = _source_path(arch, data)
    w, h = load_image_size(src)
    tile_size = int(cfg.get("tile_size", 256))
    overlap = int(cfg.get("overlap", 32))
    log.banner("split tiles")
    log.kv("image_size", f"{w}x{h}")
    log.kv("tile_size", tile_size)
    log.kv("overlap", overlap)
    specs = compute_tiles(w, h, tile_size=tile_size, overlap=overlap)
    log.say(f"grid → {len(specs)} tiles; exporting crops…")
    tiles = export_crops(src, arch.tiles_dir, specs)
    data = arch.load()
    data["tiles"] = tiles
    data["source"]["width"] = w
    data["source"]["height"] = h
    data["stage"] = "split"
    arch.save(data)
    for t in tiles:
        log.say(
            f"  tile {t['id']}: x={t['x']} y={t['y']} w={t['w']} h={t['h']} → {t['crop_path']}"
        )
    log.say(f"split done: {len(tiles)} crops in {arch.tiles_dir}")
    arch.event("split_done", tiles=len(tiles), width=w, height=h)
    if tr:
        tr.set_n_tiles(len(tiles))
        tr.stage_end("split")


def stage_tile_prompts(
    arch: RunArchive,
    *,
    force: bool = False,
    timeout_s: float = 300.0,
) -> None:
    data = arch.load()
    base = (data.get("base_prompt") or {}).get("text")
    if not base:
        raise RuntimeError("base_prompt missing; run base stage first")

    cfg = data["config"]
    agents = build_agents(
        cfg.get("agent", "both"),
        agy_model=cfg.get("agy_model"),
        grok_model=cfg.get("grok_model"),
    )
    variation = float(cfg.get("variation", 0.35))
    tiles = data.get("tiles") or []
    if not tiles:
        raise RuntimeError("no tiles; run split first")

    total = len(tiles)
    already = sum(1 for t in tiles if t.get("prompt"))
    log.banner(f"tile prompts — {total} tiles, variation={variation}")
    log.kv("agents", ", ".join(a.name for a in agents))
    log.kv("already_done", already)
    log.kv("remaining", total - already)
    log.say("EVERY tile prints START/DONE + full prompt in THIS terminal. no tail -f.")

    tr = get_tracker()
    # Track work in this pass so --force/--reprompt doesn't show 64/64 forever
    completed_this_pass = 0
    to_do = [
        i
        for i, t in enumerate(tiles)
        if force or not t.get("prompt")
    ]
    n_todo = len(to_do)
    log.kv("to_prompt_this_pass", n_todo)
    if tr:
        tr.set_n_tiles(total)
        if n_todo == 0:
            tr.stage_start("tile_prompts", n_units=total)
            tr.stage_end("tile_prompts", skipped=True)
        else:
            tr.stage_start("tile_prompts", n_units=n_todo)

    for pass_i, i in enumerate(to_do):
        tile = tiles[i]
        n = i + 1  # absolute tile index in grid
        agent = pick_for_index(agents, i)
        crop = arch.root / tile["crop_path"]
        user = tile_user_message(
            image_path=str(crop.resolve()),
            base_prompt=base,
            tile_id=tile["id"],
            row=int(tile["row"]),
            col=int(tile["col"]),
            variation=variation,
        )
        full = BASE_SYSTEM + "\n\n" + user
        log.progress(
            completed_this_pass,
            n_todo,
            f"START {tile['id']} ({pass_i + 1}/{n_todo}) via {agent.name}",
        )
        log.say(f"    crop: {crop.name}  x={tile['x']} y={tile['y']} w={tile['w']} h={tile['h']}")
        arch.event("tile_prompt_start", tile_id=tile["id"], agent=agent.name, index=n, total=total)
        try:
            result = agent.complete(full, timeout_s=timeout_s)
            result = _ensure_short_prompt(
                agent, result, kind=f"tile {tile['id']}", timeout_s=timeout_s
            )
        except Exception as e:
            tile["status"] = "failed"
            tile["error"] = str(e)
            data = arch.load()
            data["tiles"][i] = tile
            arch.save(data)
            log.say(f"FAILED {tile['id']}: {e}")
            arch.event("tile_prompt_failed", tile_id=tile["id"], error=str(e))
            raise

        attribution = {
            "agent": result.agent,
            "cli": result.cli,
            "model": result.model,
            "duration_ms": result.duration_ms,
            "created_at": utc_now(),
        }
        tile["prompt"] = result.text
        tile["attribution"] = attribution
        tile["status"] = "prompted"
        tile["error"] = None
        tile["token_len"] = token_len(result.text)

        atomic_write_text(arch.root / tile["prompt_path"], result.text)
        atomic_write_json(
            arch.root / tile["meta_path"],
            {
                "tile_id": tile["id"],
                "prompt": result.text,
                "token_len": tile["token_len"],
                "attribution": attribution,
                "geometry": {
                    "x": tile["x"],
                    "y": tile["y"],
                    "w": tile["w"],
                    "h": tile["h"],
                    "row": tile["row"],
                    "col": tile["col"],
                },
            },
        )

        data = arch.load()
        data["tiles"][i] = tile
        used = set(data.get("agents_used") or [])
        used.add(result.agent)
        data["agents_used"] = sorted(used)
        data["stage"] = "tile_prompts"
        arch.save(data)
        completed_this_pass += 1
        if tr:
            tr.stage_unit("tile_prompts", units_done=completed_this_pass)
        log.progress(
            completed_this_pass,
            n_todo,
            f"DONE {tile['id']} agent={result.agent} "
            f"words={len(result.text.split())} clip≈{tile['token_len']}",
        )
        # Result only (not the LLM instruction boilerplate)
        log.say(f"    prompt: {result.text}")
        log.say(f"    wrote: {tile['prompt_path']}")
        arch.event(
            "tile_prompt_done",
            tile_id=tile["id"],
            agent=result.agent,
            chars=len(result.text),
            token_len=tile["token_len"],
            duration_ms=result.duration_ms,
        )

    # note skips if any
    skipped = total - n_todo
    if skipped:
        log.say(f"skipped {skipped} tiles that already had prompts (use --force / --reprompt-tiles)")
    if tr and n_todo > 0:
        tr.stage_end("tile_prompts")


def stage_upscale(arch: RunArchive, *, force: bool = False) -> None:
    tr = get_tracker()
    data = arch.load()
    if data.get("output") and Path(arch.root / data["output"]).is_file() and not force:
        log.say("skip upscale (output already exists)")
        arch.event("skip_upscale", reason="output_exists")
        if tr:
            tr.stage_start("upscale", n_units=len(data.get("tiles") or []))
            tr.stage_end("upscale", skipped=True)
        return

    missing = [t["id"] for t in data.get("tiles") or [] if not t.get("prompt")]
    if missing:
        raise RuntimeError(f"tiles missing prompts: {missing[:8]}{'…' if len(missing)>8 else ''}")

    from tilagup.upscale_fastsd import run_tiled_upscale

    cfg = data["config"]
    src = _source_path(arch, data)
    out_name = "output.png"
    out_path = arch.root / out_name
    base = data["base_prompt"]["text"]
    neg = data.get("negative_prompt") or cfg.get("negative_prompt") or DEFAULT_NEGATIVE
    n_tiles = len(data["tiles"])

    log.banner("FastSD tiled upscale")
    log.kv("strength", cfg.get("strength"))
    log.kv("scale", cfg.get("scale"))
    log.kv("tiles", n_tiles)
    log.kv("output", out_path)
    arch.event("upscale_start", strength=cfg.get("strength"), scale=cfg.get("scale"))
    if tr:
        tr.stage_start("upscale", n_units=n_tiles)
    try:
        run_tiled_upscale(
            source_path=src,
            output_path=out_path,
            tiles=data["tiles"],
            base_prompt=base,
            negative_prompt=neg,
            strength=float(cfg.get("strength", 0.28)),
            scale_factor=float(cfg.get("scale", 2.0)),
            tile_overlap=int(cfg.get("overlap", 32)),
            tile_size=int(cfg.get("tile_size", 256)),
        )
    except Exception as e:
        data = arch.load()
        data["error"] = str(e)
        data["stage"] = "upscale_failed"
        arch.save(data)
        log.say(f"upscale FAILED: {e}", err=True)
        arch.event("upscale_failed", error=str(e))
        if tr:
            tr.stage_end("upscale")
        raise

    data = arch.load()
    data["output"] = out_name
    data["error"] = None
    data["stage"] = "done"
    for t in data["tiles"]:
        if t.get("status") == "prompted":
            t["status"] = "upscaled"
    arch.save(data)
    log.say(f"upscale done → {out_path}")
    arch.event("upscale_done", output=out_name)
    if tr:
        tr.stage_end("upscale")



def run_pipeline(
    *,
    image: Path | None,
    resume: Path | None,
    runs_dir: Path,
    config: dict[str, Any],
    dry_run: bool,
    force: bool = False,
    reprompt_tiles: bool = False,
    timeout_s: float = 300.0,
) -> RunArchive:
    # sticky status + timing (TTY only for bar; always records timing.json)
    from tilagup import log as _log

    quiet = _log.is_quiet()
    tracker = JobTracker(
        dry_run=dry_run,
        agent=str(config.get("agent") or "both"),
        enabled=not quiet,
    )
    set_tracker(tracker)
    tracker.stage_start("init")

    arch: RunArchive | None = None
    try:
        arch = _run_pipeline_inner(
            image=image,
            resume=resume,
            runs_dir=runs_dir,
            config=config,
            dry_run=dry_run,
            force=force,
            reprompt_tiles=reprompt_tiles,
            timeout_s=timeout_s,
            tracker=tracker,
        )
        return arch
    finally:
        run_dir = arch.root if arch is not None else None
        tracker.finish(persist=True, run_dir=run_dir)
        set_tracker(None)


def _run_pipeline_inner(
    *,
    image: Path | None,
    resume: Path | None,
    runs_dir: Path,
    config: dict[str, Any],
    dry_run: bool,
    force: bool,
    reprompt_tiles: bool,
    timeout_s: float,
    tracker: JobTracker,
) -> RunArchive:
    if resume:
        arch = open_run(resume)
        arch.event("resume", path=str(arch.root))
        data = arch.load()
        merged = dict(data.get("config") or {})
        for k, v in config.items():
            if v is not None:
                merged[k] = v
        if dry_run:
            merged["dry_run"] = True
        elif config.get("dry_run") is False:
            merged["dry_run"] = False
        data["config"] = merged
        arch.save(data)
        log.say(f"resumed stage={data.get('stage')} dry_run={merged.get('dry_run')}")
        tracker.set_run_id(data.get("run_id") or "")
        tracker.set_n_tiles(len(data.get("tiles") or []))
        # plan must match what we will actually run (dry vs full)
        tracker.dry_run = bool(dry_run)
        tracker.stages.clear()
        tracker._build_plan()
        tracker.stage_start("init")
        tracker.stage_end("init", skipped=True)
    else:
        if image is None:
            raise ValueError("image path required unless --resume")
        cfg = dict(config)
        cfg.setdefault("negative_prompt", DEFAULT_NEGATIVE)
        cfg.setdefault("agent", "both")
        cfg["dry_run"] = dry_run
        log.banner("tilagup start")
        log.kv("image", image)
        log.kv("runs_dir", runs_dir)
        log.kv("agent", cfg.get("agent"))
        log.kv("variation", cfg.get("variation"))
        log.kv("dry_run", dry_run)
        if dry_run:
            log.say("MODE: dry-run — REAL short CLIP-safe prompts, NO upscale")
            log.say("sticky status at bottom of terminal · verbose log scrolls above")
        arch = create_run(runs_dir, image, cfg)
        tracker.set_run_id(arch.load().get("run_id") or "")
        tracker.stage_end("init")

    if reprompt_tiles:
        log.banner("reprompt tiles — wipe long prompts, regenerate unique-first shorts")
        clear_tile_prompts(arch)
        force_tiles = True
        # stay in dry-run unless user also asked for upscale
        if not dry_run and not (config.get("dry_run") is False):
            dry_run = True
            data = arch.load()
            data["config"]["dry_run"] = True
            arch.save(data)
    else:
        force_tiles = force

    data = arch.load()
    stage = data.get("stage") or "init"
    want_dry = bool(dry_run or data["config"].get("dry_run"))

    if stage == "dry_run_complete" and want_dry and not force and not reprompt_tiles:
        log.say(
            "already dry_run_complete — nothing to do "
            "(--reprompt-tiles to rewrite prompts, --continue-upscale for SD)"
        )
        arch.event("already_complete", stage=stage)
        return arch
    if stage == "done" and not force and not reprompt_tiles:
        log.say("already done — nothing to do (pass --force to redo)")
        arch.event("already_complete", stage=stage)
        return arch

    # If continuing to upscale, rebuild plan so sticky includes SD stage
    if not want_dry and tracker.dry_run:
        tracker.dry_run = False
        tracker.stages.clear()
        tracker._build_plan()
        tracker.refresh()

    stage_base_prompt(arch, force=force and not reprompt_tiles, timeout_s=timeout_s)
    stage_split(arch, force=False)  # never re-split on reprompt; crops stay
    stage_tile_prompts(arch, force=force_tiles, timeout_s=timeout_s)

    data = arch.load()
    want_dry = bool(dry_run or data["config"].get("dry_run"))
    if want_dry:
        data["stage"] = "dry_run_complete"
        arch.save(data)
        log.banner("dry-run complete")
        log.kv("run_dir", arch.root)
        log.kv("tiles", len(data.get("tiles") or []))
        log.kv("next", f"uv run up.py --resume {arch.root} --continue-upscale")
        arch.event("dry_run_complete")
        return arch

    if data["config"].get("dry_run"):
        data["config"]["dry_run"] = False
        arch.save(data)

    if "upscale" not in tracker.stages:
        tracker.dry_run = False
        tracker.stages.clear()
        tracker._build_plan()
        # mark prior stages done so ETA only counts upscale
        for name in ("init", "base_prompt", "split", "tile_prompts"):
            if name in tracker.stages:
                tracker.stages[name].status = "done"
                tracker.stages[name].t0 = tracker.t_start
                tracker.stages[name].t1 = tracker.t_start

    stage_upscale(arch, force=force)
    log.banner("all done")
    log.kv("run_dir", arch.root)
    return arch
