"""Worker run under FastSD's Python (has torch/openvino). Invoked by upscale_fastsd."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: upscale_worker.py <job.json>", file=sys.stderr)
        return 2
    job_path = Path(args[0])
    job = json.loads(job_path.read_text(encoding="utf-8"))

    fastsd_src = job["fastsd_src"]
    if fastsd_src not in sys.path:
        sys.path.insert(0, fastsd_src)

    from state import get_context, get_settings  # type: ignore
    from models.interface_types import InterfaceType  # type: ignore
    from backend.upscale.tiled_upscale import generate_upscaled_image  # type: ignore

    context = get_context(InterfaceType.CLI)
    app_settings = get_settings()
    config = app_settings.settings

    strength = float(job["strength"])
    base_prompt = job["base_prompt"]
    negative_prompt = job["negative_prompt"]
    config.lcm_diffusion_setting.strength = strength
    config.lcm_diffusion_setting.prompt = base_prompt
    config.lcm_diffusion_setting.negative_prompt = negative_prompt

    tiles = job["tiles"]
    print(f"[tilagup-worker] tiles={len(tiles)} strength={strength}", flush=True)
    for i, t in enumerate(tiles):
        p = (t.get("prompt") or base_prompt)[:80]
        print(
            f"[tilagup-worker] queue {i+1}/{len(tiles)} "
            f"id={t.get('id')} {t['w']}x{t['h']} prompt={p!r}…",
            flush=True,
        )

    fs_tiles = [
        {
            "x": int(t["x"]),
            "y": int(t["y"]),
            "w": int(t["w"]),
            "h": int(t["h"]),
            "mask_box": None,
            "prompt": (t.get("prompt") or base_prompt or "").strip(),
            "scale_factor": float(job["scale_factor"]),
        }
        for t in tiles
    ]

    output_path = job["output_path"]
    upscale_settings = {
        "source_file": job["source_path"],
        "target_file": None,
        "output_format": job.get("output_format") or "PNG",
        "strength": strength,
        "scale_factor": float(job["scale_factor"]),
        "prompt": base_prompt,
        "negative_prompt": negative_prompt,
        "tile_overlap": int(job["tile_overlap"]),
        "tile_size": int(job["tile_size"]),
        "tiles": fs_tiles,
    }

    generate_upscaled_image(
        config,
        job["source_path"],
        strength,
        upscale_settings=upscale_settings,
        context=context,
        tile_overlap=int(job["tile_overlap"]),
        output_path=output_path,
        image_format=upscale_settings["output_format"],
    )
    print(f"[tilagup-worker] done → {output_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
