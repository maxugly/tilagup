"""FastSD CPU tiled upscale — runs in FastSD's own venv (torch/openvino live there)."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from tilagup import log


def fastsd_root() -> Path | None:
    env = os.environ.get("FASTSDCPU_ROOT") or os.environ.get("FASTSD_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "src").is_dir():
            return p
    return None


def fastsd_python(root: Path) -> Path:
    """Prefer FastSD's venv python; fall back to current interpreter."""
    override = os.environ.get("FASTSDCPU_PYTHON") or os.environ.get("FASTSD_PYTHON")
    candidates = []
    if override:
        candidates.append(Path(override).expanduser())
    candidates.extend(
        [
            root / "env" / "bin" / "python",
            root / "env" / "bin" / "python3",
            root / ".venv" / "bin" / "python",
            root / ".venv" / "bin" / "python3",
        ]
    )
    for c in candidates:
        # Do NOT resolve() venv symlinks — that jumps to the base interpreter
        # and drops site-packages (torch/openvino live in the venv).
        if c.is_file() and os.access(c, os.X_OK):
            return c
    return Path(sys.executable)


def ensure_fastsd_root() -> Path:
    root = fastsd_root()
    if root is None:
        raise RuntimeError(
            "FastSD CPU not found. Set FASTSDCPU_ROOT to your fastsdcpu checkout "
            "(directory that contains src/)."
        )
    return root


def run_tiled_upscale(
    *,
    source_path: Path,
    output_path: Path,
    tiles: list[dict[str, Any]],
    base_prompt: str,
    negative_prompt: str,
    strength: float,
    scale_factor: float = 2.0,
    tile_overlap: int = 32,
    tile_size: int = 256,
    texture: str = "none",
    texture_strength: float = 1.0,
) -> Path:
    root = ensure_fastsd_root()
    py = fastsd_python(root)
    worker = Path(__file__).resolve().parent / "upscale_worker.py"
    tilagup_src = Path(__file__).resolve().parent.parent  # …/src

    log.banner(f"FastSD upscale — {len(tiles)} tiles")
    log.kv("source", source_path)
    log.kv("output", output_path)
    log.kv("strength", strength)
    log.kv("scale", scale_factor)
    log.kv("tile_size", tile_size)
    log.kv("overlap", tile_overlap)
    log.kv("texture", f"{texture} @ {texture_strength}")
    log.kv("fastsd_root", root)
    log.kv("fastsd_python", py)
    log.kv("worker", worker)
    log.dump("base prompt for upscale (pre-texture)", base_prompt)
    log.dump("negative prompt (pre-texture)", negative_prompt)

    for i, t in enumerate(tiles):
        prompt = (t.get("prompt") or base_prompt or "").strip()
        log.progress(i, len(tiles), f"queue tile {t.get('id')} {t.get('w')}x{t.get('h')}")
        log.dump(f"upscale prompt tile {t.get('id')} (pre-texture)", prompt)

    job = {
        "fastsd_src": str(root / "src"),
        "source_path": str(source_path),
        "output_path": str(output_path),
        "output_format": output_path.suffix.lstrip(".").upper() or "PNG",
        "strength": float(strength),
        "scale_factor": float(scale_factor),
        "tile_overlap": int(tile_overlap),
        "tile_size": int(tile_size),
        "base_prompt": base_prompt,
        "negative_prompt": negative_prompt,
        "tiles": tiles,
        "texture": texture or "none",
        "texture_strength": float(texture_strength),
        # SD1.5 / turbo CLIP limit is 77; leave headroom
        "max_clip_tokens": int(os.environ.get("TILAGUP_MAX_CLIP_TOKENS", "75")),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    job_path = output_path.parent / "upscale_job.json"
    job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    log.say(f"wrote job file: {job_path}")

    env = os.environ.copy()
    # so `import tilagup` is not required; worker is run as a script file
    env["PYTHONUNBUFFERED"] = "1"
    # Prefer FastSD packages; don't need tilagup on path for worker
    env.pop("VIRTUAL_ENV", None)

    cmd = [str(py), str(worker), str(job_path)]
    log.say(f">>> SPAWN FastSD worker: {' '.join(cmd)}")
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
        cwd=str(root),
    )
    log.say(f"    worker pid={proc.pid}")

    assert proc.stdout is not None and proc.stderr is not None
    streams = [proc.stdout, proc.stderr]
    last_beat = time.monotonic()
    deadline = time.monotonic() + 3600 * 6  # 6h hard ceiling
    try:
        while True:
            if proc.poll() is not None and not streams:
                break
            if time.monotonic() > deadline:
                proc.kill()
                raise TimeoutError("FastSD worker exceeded 6h")
            now = time.monotonic()
            if now - last_beat >= 15.0:
                log.say(
                    f"… ALIVE FastSD worker pid={proc.pid} "
                    f"elapsed={int(now - t0)}s"
                )
                last_beat = now
            if not streams:
                if proc.poll() is not None:
                    break
                time.sleep(0.2)
                continue
            ready, _, _ = select.select(streams, [], [], 1.0)
            for s in ready:
                line = s.readline()
                if line == "":
                    streams = [x for x in streams if x is not s]
                    continue
                tag = "out" if s is proc.stdout else "err"
                text = line.rstrip()
                log.say(f"  [fastsd:{tag}] {text}")
                # track SD tile progress for sticky ETA: "[SD Upscale] tile 3/64 …"
                if "tile " in text and "/" in text:
                    try:
                        from tilagup.job_status import get_tracker

                        tr = get_tracker()
                        if tr:
                            # … tile N/M …
                            part = text.split("tile ", 1)[1]
                            frac = part.split()[0]
                            cur_s, tot_s = frac.split("/", 1)
                            tr.stage_unit("upscale", units_done=int(cur_s))
                    except Exception:
                        pass
        rc = proc.wait()

    except Exception:
        proc.kill()
        raise

    log.say(f"<<< FastSD worker exit={rc} after {int(time.perf_counter() - t0)}s")
    if rc != 0:
        raise RuntimeError(f"FastSD worker failed with exit {rc} (see log above)")
    if not output_path.is_file():
        raise RuntimeError(f"worker exited 0 but missing output: {output_path}")
    log.say(f"output ok: {output_path} ({output_path.stat().st_size} bytes)")
    return output_path
