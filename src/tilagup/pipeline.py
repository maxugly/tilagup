"""Stage machine for a tilagup run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tilagup.agents import build_agents, pick_for_index
from tilagup.archive import (
    RunArchive,
    atomic_write_json,
    atomic_write_text,
    create_run,
    open_run,
    utc_now,
)
from tilagup.prompts_lib import (
    BASE_SYSTEM,
    DEFAULT_NEGATIVE,
    base_user_message,
    tile_user_message,
)
from tilagup.tiles import compute_tiles, export_crops, load_image_size


def _source_path(arch: RunArchive, data: dict[str, Any]) -> Path:
    rel = data["source"]["path"]
    return arch.root / rel


def stage_base_prompt(arch: RunArchive, *, force: bool = False, timeout_s: float = 300.0) -> None:
    data = arch.load()
    if data.get("base_prompt") and data["base_prompt"].get("text") and not force:
        arch.event("skip_base_prompt", reason="already_present")
        return

    cfg = data["config"]
    agents = build_agents(
        cfg.get("agent", "both"),
        agy_model=cfg.get("agy_model"),
        grok_model=cfg.get("grok_model"),
    )
    agent = pick_for_index(agents, 0)
    src = _source_path(arch, data)
    # Embed system guidance in the user prompt (CLIs take a single -p string)
    user = (
        BASE_SYSTEM
        + "\n\n"
        + base_user_message(str(src.resolve()))
    )
    arch.event("base_prompt_start", agent=agent.name)
    result = agent.complete(user, timeout_s=timeout_s)
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
    }
    used = set(data.get("agents_used") or [])
    used.add(result.agent)
    data["agents_used"] = sorted(used)
    data["stage"] = "base_prompt"
    arch.save(data)
    atomic_write_text(arch.root / "base_prompt.txt", result.text)
    arch.event("base_prompt_done", agent=result.agent, chars=len(result.text))


def stage_split(arch: RunArchive, *, force: bool = False) -> None:
    data = arch.load()
    if data.get("tiles") and not force:
        arch.event("skip_split", reason="tiles_already_present", count=len(data["tiles"]))
        return

    cfg = data["config"]
    src = _source_path(arch, data)
    w, h = load_image_size(src)
    specs = compute_tiles(
        w,
        h,
        tile_size=int(cfg.get("tile_size", 256)),
        overlap=int(cfg.get("overlap", 32)),
    )
    tiles = export_crops(src, arch.tiles_dir, specs)
    data = arch.load()
    data["tiles"] = tiles
    data["source"]["width"] = w
    data["source"]["height"] = h
    data["stage"] = "split"
    arch.save(data)
    arch.event("split_done", tiles=len(tiles), width=w, height=h)


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

    for i, tile in enumerate(tiles):
        if tile.get("prompt") and not force:
            arch.event("skip_tile_prompt", tile_id=tile["id"])
            continue
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
        # include system-ish preamble
        full = (
            "You write Stable Diffusion prompts. Reply with ONLY the prompt text.\n\n"
            + user
        )
        arch.event("tile_prompt_start", tile_id=tile["id"], agent=agent.name)
        try:
            result = agent.complete(full, timeout_s=timeout_s)
        except Exception as e:
            tile["status"] = "failed"
            tile["error"] = str(e)
            data = arch.load()
            data["tiles"][i] = tile
            arch.save(data)
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

        atomic_write_text(arch.root / tile["prompt_path"], result.text)
        atomic_write_json(
            arch.root / tile["meta_path"],
            {
                "tile_id": tile["id"],
                "prompt": result.text,
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
        arch.event(
            "tile_prompt_done",
            tile_id=tile["id"],
            agent=result.agent,
            chars=len(result.text),
        )


def stage_upscale(arch: RunArchive, *, force: bool = False) -> None:
    data = arch.load()
    if data.get("output") and Path(arch.root / data["output"]).is_file() and not force:
        arch.event("skip_upscale", reason="output_exists")
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

    arch.event("upscale_start", strength=cfg.get("strength"), scale=cfg.get("scale"))
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
        arch.event("upscale_failed", error=str(e))
        raise

    data = arch.load()
    data["output"] = out_name
    data["error"] = None
    data["stage"] = "done"
    for t in data["tiles"]:
        if t.get("status") == "prompted":
            t["status"] = "upscaled"
    arch.save(data)
    arch.event("upscale_done", output=out_name)


def run_pipeline(
    *,
    image: Path | None,
    resume: Path | None,
    runs_dir: Path,
    config: dict[str, Any],
    dry_run: bool,
    force: bool = False,
    timeout_s: float = 300.0,
) -> RunArchive:
    if resume:
        arch = open_run(resume)
        arch.event("resume", path=str(arch.root))
        # Merge CLI overrides into stored config (resume can bump strength, etc.)
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
    else:
        if image is None:
            raise ValueError("image path required unless --resume")
        cfg = dict(config)
        cfg.setdefault("negative_prompt", DEFAULT_NEGATIVE)
        cfg.setdefault("agent", "both")
        cfg["dry_run"] = dry_run
        arch = create_run(runs_dir, image, cfg)

    data = arch.load()
    stage = data.get("stage") or "init"
    want_dry = bool(dry_run or data["config"].get("dry_run"))

    # Finished dry-run: either stop, or continue to upscale if caller cleared dry_run
    if stage == "dry_run_complete" and want_dry and not force:
        arch.event("already_complete", stage=stage)
        return arch
    if stage == "done" and not force:
        arch.event("already_complete", stage=stage)
        return arch

    stage_base_prompt(arch, force=force, timeout_s=timeout_s)
    stage_split(arch, force=force)
    stage_tile_prompts(arch, force=force, timeout_s=timeout_s)

    data = arch.load()
    want_dry = bool(dry_run or data["config"].get("dry_run"))
    if want_dry:
        data["stage"] = "dry_run_complete"
        arch.save(data)
        arch.event("dry_run_complete")
        return arch

    # Continuing from a prior dry-run into SD: clear flag
    if data["config"].get("dry_run"):
        data["config"]["dry_run"] = False
        arch.save(data)

    stage_upscale(arch, force=force)
    return arch
