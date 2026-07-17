"""FastSD CPU tiled upscale integration (optional dependency via FASTSDCPU_ROOT)."""

from __future__ import annotations

import os
import sys
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


def ensure_fastsd_on_path(root: Path | None = None) -> Path:
    root = root or fastsd_root()
    if root is None:
        raise RuntimeError(
            "FastSD CPU not found. Set FASTSDCPU_ROOT to your fastsdcpu checkout "
            "(directory that contains src/)."
        )
    src = str(root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    log.say(f"FastSD root: {root}")
    log.say(f"FastSD src on path: {src}")
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
) -> Path:
    """Call FastSD generate_upscaled_image with per-tile prompts. Loud the whole way."""
    ensure_fastsd_on_path()

    from state import get_context, get_settings  # type: ignore
    from models.interface_types import InterfaceType  # type: ignore
    from backend.upscale.tiled_upscale import generate_upscaled_image  # type: ignore

    context = get_context(InterfaceType.CLI)
    app_settings = get_settings()
    config = app_settings.settings

    config.lcm_diffusion_setting.strength = float(strength)
    config.lcm_diffusion_setting.prompt = base_prompt
    config.lcm_diffusion_setting.negative_prompt = negative_prompt

    log.banner(f"FastSD upscale — {len(tiles)} tiles")
    log.kv("source", source_path)
    log.kv("output", output_path)
    log.kv("strength", strength)
    log.kv("scale", scale_factor)
    log.kv("tile_size", tile_size)
    log.kv("overlap", tile_overlap)
    log.dump("base prompt for upscale", base_prompt)
    log.dump("negative prompt", negative_prompt)

    fs_tiles = []
    for i, t in enumerate(tiles):
        prompt = (t.get("prompt") or base_prompt or "").strip()
        log.progress(i, len(tiles), f"queue tile {t.get('id')} {t.get('w')}x{t.get('h')}")
        log.dump(f"upscale prompt tile {t.get('id')}", prompt)
        fs_tiles.append(
            {
                "x": int(t["x"]),
                "y": int(t["y"]),
                "w": int(t["w"]),
                "h": int(t["h"]),
                "mask_box": None,
                "prompt": prompt,
                "scale_factor": float(scale_factor),
            }
        )

    upscale_settings = {
        "source_file": str(source_path),
        "target_file": None,
        "output_format": output_path.suffix.lstrip(".").upper() or "PNG",
        "strength": float(strength),
        "scale_factor": float(scale_factor),
        "prompt": base_prompt,
        "negative_prompt": negative_prompt,
        "tile_overlap": int(tile_overlap),
        "tile_size": int(tile_size),
        "tiles": fs_tiles,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    log.say("handing off to FastSD generate_upscaled_image — its prints should also appear here")
    generate_upscaled_image(
        config,
        str(source_path),
        float(strength),
        upscale_settings=upscale_settings,
        context=context,
        tile_overlap=int(tile_overlap),
        output_path=str(output_path),
        image_format=upscale_settings["output_format"],
    )
    log.say(f"FastSD returned; output exists={output_path.is_file()} path={output_path}")
    return output_path
