"""FastSD CPU tiled upscale integration (optional dependency via FASTSDCPU_ROOT)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


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
    """Call FastSD generate_upscaled_image with per-tile prompts."""
    ensure_fastsd_on_path()

    from state import get_context, get_settings  # type: ignore
    from models.interface_types import InterfaceType  # type: ignore
    from backend.upscale.tiled_upscale import generate_upscaled_image  # type: ignore

    context = get_context(InterfaceType.CLI)
    app_settings = get_settings()
    config = app_settings.settings

    # Prefer OpenVINO path if already configured in settings.yaml
    config.lcm_diffusion_setting.strength = float(strength)
    config.lcm_diffusion_setting.prompt = base_prompt
    config.lcm_diffusion_setting.negative_prompt = negative_prompt

    fs_tiles = []
    for t in tiles:
        prompt = (t.get("prompt") or base_prompt or "").strip()
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
    return output_path
