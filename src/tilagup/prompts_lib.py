"""Prompt templates for vision agents (base + tile).

CLIP on SD1.5 / turbo only keeps ~77 tokens. Agents must stay short.
"""

from __future__ import annotations


BASE_SYSTEM = """You write SHORT Stable Diffusion prompts for CLIP (max ~75 tokens).
HARD LIMIT: at most 55 words. Prefer dense comma-separated phrases over prose.
Return ONLY the prompt text — no markdown, no quotes, no preamble.
Cover: subject, key materials, 2-3 texture words, lighting, palette, mood.
Do NOT write essays or full paragraphs."""


def base_user_message(image_path: str) -> str:
    return (
        f"Image path (open and inspect): {image_path}\n\n"
        "Write ONE short overall base prompt for this image (≤55 words, CLIP-safe). "
        "Capture subject + materials + lighting + palette. No composition essay. "
        "Prompt only."
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
        drift = "Only name textures already visible. Almost no invention."
    elif variation <= 0.4:
        drift = "Add a few local material details; same style as base."
    elif variation <= 0.7:
        drift = "Richer local weird detail, still same world/palette."
    else:
        drift = "Push micro/fractal detail hard; keep same materials language."

    # Keep the base short in the instruction too if agents rewrote long ones
    base_snip = base_prompt.strip()
    if len(base_snip.split()) > 55:
        base_snip = " ".join(base_snip.split()[:55])

    return (
        f"Style lock (do NOT paste this whole thing into your answer):\n{base_snip}\n\n"
        f"Tile id={tile_id} row={row} col={col}.\n"
        f"Crop path: {image_path}\n\n"
        f"Variation ({variation:.2f}): {drift}\n\n"
        "Write ONE SHORT prompt for THIS crop only (≤55 words, ≤75 CLIP tokens). "
        "Self-contained: subject of the crop + materials + light. "
        "Do NOT restate the full base. Do NOT write a paragraph. "
        "Comma-separated tags/phrases preferred. Prompt only."
    )


DEFAULT_NEGATIVE = (
    "cartoon, anime, manga, painting, drawing, illustration, 3d render, "
    "plastic, doll, mutation, deformed, blurry, lowres, watermark, text, logo, "
    "panel borders, collage seams, split screen"
)
