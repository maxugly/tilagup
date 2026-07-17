"""Prompt templates for vision agents (base + tile)."""

from __future__ import annotations


BASE_SYSTEM = """You are writing a Stable Diffusion img2img / tiled-upscale prompt.
Look at the image carefully. Return ONLY the prompt text — no markdown, no quotes,
no preamble, no explanation. One dense paragraph of natural language is fine.
Describe subject, materials, textures, lighting, palette, and overall mood so a
diffusion model can preserve composition while enriching detail."""


def base_user_message(image_path: str) -> str:
    return (
        f"Image path (open and inspect): {image_path}\n\n"
        "Write a single overall base prompt that captures the soul and structure "
        "of this image for a later tiled upscale. Keep composition implicit "
        "(do not invent a new scene). Prompt only."
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
    # Map variation 0..1 to instruction language
    if variation <= 0.15:
        drift = (
            "Stay extremely faithful to the base. Only clarify textures already "
            "visible in this crop. Almost no invention."
        )
    elif variation <= 0.4:
        drift = (
            "Add moderate local micro-detail consistent with the base style. "
            "Do not change subject, palette family, or lighting."
        )
    elif variation <= 0.7:
        drift = (
            "Invent richer weird local detail in this crop, still clearly the same "
            "world and style as the base. No new global narrative."
        )
    else:
        drift = (
            "High variation: push strange fractal/micro structure hard in this crop, "
            "but the crop must still read as part of the same image (same materials "
            "language). Do not invent a totally different scene."
        )

    return (
        f"Full-image base prompt (LOCKED — preserve style/subject):\n{base_prompt}\n\n"
        f"This tile id={tile_id} row={row} col={col}.\n"
        f"Crop image path (open and inspect): {image_path}\n\n"
        f"Variation guidance ({variation:.2f}): {drift}\n\n"
        "Write ONE prompt for upscaling THIS crop only: start from the base meaning, "
        "then append or weave in local detail visible or implied in the crop. "
        "Return ONLY the final prompt text. No markdown, no preamble."
    )


DEFAULT_NEGATIVE = (
    "cartoon, anime, manga, painting, drawing, illustration, 3d render, "
    "plastic, doll, mutation, deformed, blurry, lowres, watermark, text, logo, "
    "panel borders, collage seams, split screen"
)
