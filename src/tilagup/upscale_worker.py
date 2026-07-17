"""Worker run under FastSD's Python (has torch/openvino). Invoked by upscale_fastsd."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _fit(text: str, max_tokens: int = 75) -> tuple[str, bool]:
    """Inline CLIP fit so worker does not depend on tilagup package install in FastSD venv."""
    text = " ".join((text or "").split()).strip()
    if not text:
        return "", False
    tok = None
    try:
        from transformers import CLIPTokenizer  # type: ignore

        tok = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
    except Exception:
        tok = None

    def n_tokens(s: str) -> int:
        if tok is not None:
            return len(tok.encode(s, add_special_tokens=False))
        return max(1, len(s.split()))

    if n_tokens(text) <= max_tokens:
        return text, False

    lo, hi = 0, len(text)
    best = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        chunk = text[:mid].rsplit(" ", 1)[0].strip(" ,;:")
        if not chunk:
            lo = mid + 1
            continue
        if n_tokens(chunk) <= max_tokens:
            best = chunk
            lo = mid + 1
        else:
            hi = mid - 1
    if not best:
        words = text.split()
        best = " ".join(words[: max(8, max_tokens // 2)])
        while best and n_tokens(best) > max_tokens:
            words = best.split()[:-1]
            best = " ".join(words)
    return best, True


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

    max_tokens = int(job.get("max_clip_tokens") or 75)

    from state import get_context, get_settings  # type: ignore
    from models.interface_types import InterfaceType  # type: ignore
    from backend.upscale.tiled_upscale import generate_upscaled_image  # type: ignore

    context = get_context(InterfaceType.CLI)
    app_settings = get_settings()
    config = app_settings.settings

    strength = float(job["strength"])
    base_prompt, base_cut = _fit(job["base_prompt"], max_tokens)
    negative_prompt, neg_cut = _fit(job["negative_prompt"], max_tokens)
    if base_cut:
        print(f"[tilagup-worker] CLIP-fit base prompt → {max_tokens} tokens", flush=True)
    if neg_cut:
        print(f"[tilagup-worker] CLIP-fit negative prompt → {max_tokens} tokens", flush=True)

    config.lcm_diffusion_setting.strength = strength
    config.lcm_diffusion_setting.prompt = base_prompt
    config.lcm_diffusion_setting.negative_prompt = negative_prompt

    tiles = job["tiles"]
    print(
        f"[tilagup-worker] tiles={len(tiles)} strength={strength} max_clip_tokens={max_tokens}",
        flush=True,
    )

    fs_tiles = []
    for i, t in enumerate(tiles):
        raw = (t.get("prompt") or job["base_prompt"] or "").strip()
        prompt, cut = _fit(raw, max_tokens)
        flag = " TRUNCATED" if cut else ""
        print(
            f"[tilagup-worker] {i+1}/{len(tiles)} id={t.get('id')} "
            f"{t['w']}x{t['h']}{flag} prompt={prompt!r}",
            flush=True,
        )
        fs_tiles.append(
            {
                "x": int(t["x"]),
                "y": int(t["y"]),
                "w": int(t["w"]),
                "h": int(t["h"]),
                "mask_box": None,
                "prompt": prompt,
                "scale_factor": float(job["scale_factor"]),
            }
        )

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
