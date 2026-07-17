"""Prompt templates for vision agents (base + tile).

CLIP on SD1.5 / turbo only keeps ~77 tokens. Unique tile detail must come FIRST
so it is never the part that gets dropped.
"""

from __future__ import annotations


BASE_SYSTEM = """You write SHORT Stable Diffusion prompts for CLIP (max ~75 tokens).
HARD LIMIT: at most 50 words. Dense comma-separated phrases, not prose paragraphs.
Return ONLY the prompt text — no markdown, no quotes, no preamble."""


def base_user_message(image_path: str) -> str:
    return (
        f"Image path (open and inspect): {image_path}\n\n"
        "Write ONE short overall base prompt (≤50 words). "
        "Subject, main materials, lighting, palette only. Prompt only."
    )


def tile_user_message(
    *,
    image_path: str,
    base_prompt: str,
    tile_id: str,
    row: int,
    col: int,
    variation: float,
) -> str:
    if variation <= 0.15:
        drift = "Only name what is already visible in the crop."
    elif variation <= 0.4:
        drift = "Name local materials/details unique to this crop."
    elif variation <= 0.7:
        drift = "Richer local weird detail unique to this crop."
    else:
        drift = "Push micro/fractal local detail hard."

    base_snip = " ".join(base_prompt.strip().split()[:40])

    return (
        f"Style reference only (DO NOT copy wholesale into your answer):\n{base_snip}\n\n"
        f"Tile id={tile_id} row={row} col={col}.\n"
        f"Crop path (open and inspect): {image_path}\n\n"
        f"Variation ({variation:.2f}): {drift}\n\n"
        "Write ONE SHORT prompt for THIS crop (≤50 words, ≤75 CLIP tokens).\n"
        "CRITICAL ORDER:\n"
        "1) FIRST: what is unique/visible in THIS crop (the part that differs from other tiles)\n"
        "2) THEN: a few shared style words (materials/palette) if room remains\n"
        "Do NOT restate a full scene description of the whole image.\n"
        "Do NOT put shared global description before local detail.\n"
        "Comma-separated phrases preferred. Prompt only."
    )


DEFAULT_NEGATIVE = (
    "cartoon, anime, manga, painting, drawing, illustration, 3d render, "
    "plastic, doll, mutation, deformed, blurry, lowres, watermark, text, logo, "
    "panel borders, collage seams, split screen"
)
