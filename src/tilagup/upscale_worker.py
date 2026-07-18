"""Worker run under FastSD's Python (has torch/openvino). Invoked by upscale_fastsd.

CLIP-fits prompts UNIQUE-FIRST so tile-specific detail is not the part that dies.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _tok():
    try:
        from transformers import CLIPTokenizer  # type: ignore

        return CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
    except Exception:
        return None


def _n(tok, s: str) -> int:
    s = " ".join((s or "").split()).strip()
    if not s:
        return 0
    if tok is not None:
        return len(tok.encode(s, add_special_tokens=False))
    return max(1, len(s.split()))


def _normalize(text: str) -> str:
    return " ".join((text or "").split()).strip(" ,;:")


def _strip_restated_base(tile_prompt: str, base_prompt: str) -> str:
    tile = _normalize(tile_prompt)
    base = _normalize(base_prompt)
    if not tile:
        return ""
    if not base:
        return tile
    if tile.lower().startswith(base.lower()):
        rest = tile[len(base) :].lstrip(" ,.;:-")
        if rest:
            return rest
    tw, bw = tile.split(), base.split()
    i = 0
    while i < len(tw) and i < len(bw) and tw[i].lower().strip(",.") == bw[i].lower().strip(",."):
        i += 1
    if i >= 12:
        rest = " ".join(tw[i:]).strip(" ,;:")
        if rest and len(rest.split()) >= 4:
            return rest
    return tile


def _head_fit(tok, text: str, max_tokens: int) -> str:
    text = _normalize(text)
    if _n(tok, text) <= max_tokens:
        return text
    lo, hi = 0, len(text)
    best = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        chunk = text[:mid].rsplit(" ", 1)[0].strip(" ,;:")
        if not chunk:
            lo = mid + 1
            continue
        if _n(tok, chunk) <= max_tokens:
            best = chunk
            lo = mid + 1
        else:
            hi = mid - 1
    if not best:
        words = text.split()
        best = " ".join(words[: max(8, max_tokens // 2)])
        while best and _n(tok, best) > max_tokens:
            words = best.split()[:-1]
            best = " ".join(words)
    return best


def fit_tile(tok, tile_prompt: str, base_prompt: str, max_tokens: int) -> tuple[str, bool, str]:
    """Return (fitted, changed, note). Unique local content first."""
    original = _normalize(tile_prompt)
    unique = _strip_restated_base(tile_prompt, base_prompt)
    unique = _normalize(unique)
    if not unique or len(unique.split()) < 3:
        unique = original
    tail_words = _normalize(base_prompt).split()[:12]
    tail = " ".join(tail_words)

    if _n(tok, unique) <= max_tokens:
        if tail and _n(tok, unique + ", " + tail) <= max_tokens:
            out = f"{unique}, {tail}"
        else:
            out = unique
        note = "unique-first"
        if out != original:
            note += "+restyle"
        return out, out != original, note

    out = _head_fit(tok, unique, max_tokens)
    return out, True, "unique-first+truncated"


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
    tok = _tok()
    print(f"[tilagup-worker] CLIP tokenizer={'yes' if tok else 'fallback-words'}", flush=True)

    from state import get_context, get_settings  # type: ignore
    from models.interface_types import InterfaceType  # type: ignore
    from backend.upscale.tiled_upscale import generate_upscaled_image  # type: ignore

    context = get_context(InterfaceType.CLI)
    app_settings = get_settings()
    config = app_settings.settings

    strength = float(job["strength"])
    base_raw = job["base_prompt"]
    base_prompt = _head_fit(tok, base_raw, max_tokens)
    negative_prompt = _head_fit(tok, job["negative_prompt"], max_tokens)
    if base_prompt != _normalize(base_raw):
        print(f"[tilagup-worker] base CLIP-fit → {_n(tok, base_prompt)} tokens", flush=True)

    config.lcm_diffusion_setting.strength = strength
    config.lcm_diffusion_setting.prompt = base_prompt
    config.lcm_diffusion_setting.negative_prompt = negative_prompt

    tiles = job["tiles"]
    print(
        f"[tilagup-worker] tiles={len(tiles)} strength={strength} max_clip_tokens={max_tokens}",
        flush=True,
    )

    # Match FastSD vanilla tile defs EXACTLY (tiled_upscale.py when tiles==[]).
    # Critical: mask_box softens only left/top (overlap with already-pasted tiles),
    # and extends to full scaled tile size on right/bottom. Passing mask_box=None
    # softens ALL four sides over transparent black → dark grid gutters.
    scale_factor = float(job["scale_factor"])
    tile_overlap = int(job["tile_overlap"])

    fs_tiles = []
    for i, t in enumerate(tiles):
        raw = (t.get("prompt") or base_raw or "").strip()
        prompt, changed, note = fit_tile(tok, raw, base_raw, max_tokens)
        flag = f" [{note}]" if changed else ""
        x = int(t["x"])
        y = int(t["y"])
        w = int(t["w"])
        h = int(t["h"])
        # Prefer offsets stored at split time; fall back like FastSD (0 on first row/col)
        x_offset = int(t["x_offset"]) if t.get("x_offset") is not None else (
            tile_overlap if x > 0 else 0
        )
        y_offset = int(t["y_offset"]) if t.get("y_offset") is not None else (
            tile_overlap if y > 0 else 0
        )
        mask_box = (
            x_offset,
            y_offset,
            int(w * scale_factor),
            int(h * scale_factor),
        )
        print(
            f"[tilagup-worker] {i+1}/{len(tiles)} id={t.get('id')} "
            f"{w}x{h} mask_box={mask_box} tok≈{_n(tok, prompt)}{flag}\n"
            f"    {prompt!r}",
            flush=True,
        )
        fs_tiles.append(
            {
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "mask_box": mask_box,
                "prompt": prompt,
                "scale_factor": scale_factor,
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
