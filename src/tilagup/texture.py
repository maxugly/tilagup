"""Opt-in texture prompt packs applied at SD upscale time only.

Default mode is ``none`` — zero change to prompts (current behavior).
Agent dry-run files on disk are never rewritten by these packs.
"""

from __future__ import annotations

from typing import Any

TEXTURE_MODES = ("none", "grit", "smooth")

# Positive tags appended (after subject content). Keep short — CLIP is ~75 tokens.
_PACKS: dict[str, dict[str, str]] = {
    "grit": {
        "positive": (
            "heavy film grain, raw texture, micro detail, sharp grain, "
            "imperfect surface, gritty detail"
        ),
        "negative": (
            "smooth, plastic, airbrushed, soft focus, porcelain, "
            "overprocessed, glossy skin, blurry, rounded edges"
        ),
    },
    "smooth": {
        "positive": "smooth finish, clean surface, polished detail, soft gradients",
        "negative": "heavy grain, noise, gritty, dirty, chaotic noise, film grain",
    },
}


def normalize_mode(mode: str | None) -> str:
    m = (mode or "none").strip().lower()
    if m in ("off", "default", ""):
        return "none"
    if m not in TEXTURE_MODES:
        raise ValueError(f"unknown texture mode {mode!r}; use one of {TEXTURE_MODES}")
    return m


def pack_for(mode: str, strength: float) -> dict[str, str]:
    """Return positive/negative fragments for mode. strength 0 → empty; 1 → full pack."""
    mode = normalize_mode(mode)
    strength = max(0.0, min(1.0, float(strength)))
    if mode == "none" or strength <= 0.0:
        return {"positive": "", "negative": ""}

    pack = _PACKS[mode]
    if strength >= 0.99:
        return dict(pack)

    # Scale by taking a prefix of comma-separated phrases
    def scale_phrases(text: str) -> str:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if not parts:
            return ""
        n = max(1, int(round(len(parts) * strength)))
        return ", ".join(parts[:n])

    return {
        "positive": scale_phrases(pack["positive"]),
        "negative": scale_phrases(pack["negative"]),
    }


def merge_negative(base_neg: str, extra_neg: str) -> str:
    base = (base_neg or "").strip().strip(",")
    extra = (extra_neg or "").strip().strip(",")
    if not extra:
        return base
    if not base:
        return extra
    # avoid crude duplicates
    base_l = base.lower()
    add = [p.strip() for p in extra.split(",") if p.strip() and p.strip().lower() not in base_l]
    if not add:
        return base
    return base + ", " + ", ".join(add)


def apply_positive(content: str, texture_pos: str) -> str:
    content = (content or "").strip().strip(",")
    texture_pos = (texture_pos or "").strip().strip(",")
    if not texture_pos:
        return content
    if not content:
        return texture_pos
    return f"{content}, {texture_pos}"


def describe(mode: str, strength: float) -> dict[str, Any]:
    mode = normalize_mode(mode)
    pack = pack_for(mode, strength)
    return {
        "mode": mode,
        "strength": max(0.0, min(1.0, float(strength))),
        "positive": pack["positive"],
        "negative": pack["negative"],
    }
