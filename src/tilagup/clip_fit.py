"""Fit prompts into CLIP's ~77 token limit without discarding tile uniqueness.

SD1.5 / turbo CLIP keeps ~77 tokens. Long agent essays that restate the base
then append local detail lose that local detail if you naively head-truncate.
Prefer: unique local phrase first, then a short style tail from the base.
"""

from __future__ import annotations

from functools import lru_cache

DEFAULT_MAX_TOKENS = 75


@lru_cache(maxsize=1)
def _clip_tokenizer():
    try:
        from transformers import CLIPTokenizer  # type: ignore

        return CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
    except Exception:
        return None


def token_len(text: str) -> int:
    text = (text or "").strip()
    if not text:
        return 0
    tok = _clip_tokenizer()
    if tok is not None:
        return len(tok.encode(text, add_special_tokens=False))
    return max(1, len(text.split()))


def _normalize(text: str) -> str:
    return " ".join((text or "").split()).strip(" ,;:")


def _word_overlap_ratio(a: str, b: str) -> float:
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), 1)


def strip_restated_base(tile_prompt: str, base_prompt: str) -> str:
    """If the tile prompt largely restates the base, peel that off and keep the rest."""
    tile = _normalize(tile_prompt)
    base = _normalize(base_prompt)
    if not tile:
        return ""
    if not base:
        return tile

    # Exact prefix
    if tile.lower().startswith(base.lower()):
        rest = tile[len(base) :].lstrip(" ,.;:-")
        if rest:
            return rest

    # Shared long prefix by words
    tw, bw = tile.split(), base.split()
    i = 0
    while i < len(tw) and i < len(bw) and tw[i].lower().strip(",.") == bw[i].lower().strip(",."):
        i += 1
    if i >= 12:  # substantial restated base
        rest = " ".join(tw[i:]).strip(" ,;:")
        if rest and len(rest.split()) >= 4:
            return rest

    # If almost the whole tile is just the base, keep a short style version of base
    if _word_overlap_ratio(tile, base) > 0.85 and len(tw) > 40:
        return " ".join(tw[:20])

    return tile


def style_tail(base_prompt: str, max_words: int = 12) -> str:
    """Tiny style anchor from base — materials/palette words only."""
    base = _normalize(base_prompt)
    if not base:
        return ""
    words = base.split()
    return " ".join(words[:max_words]).strip(" ,;:")


def fit_clip_prompt(text: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> tuple[str, bool]:
    """Head-truncate to max_tokens (last resort). Prefer fit_tile_prompt for tiles."""
    text = _normalize(text)
    if not text:
        return "", False
    if token_len(text) <= max_tokens:
        return text, False

    lo, hi = 0, len(text)
    best = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        chunk = text[:mid].rsplit(" ", 1)[0].strip(" ,;:")
        if not chunk:
            lo = mid + 1
            continue
        if token_len(chunk) <= max_tokens:
            best = chunk
            lo = mid + 1
        else:
            hi = mid - 1
    if not best:
        words = text.split()
        best = " ".join(words[: max(8, max_tokens // 2)])
        while best and token_len(best) > max_tokens:
            words = best.split()[:-1]
            best = " ".join(words)
    return best, True


def fit_tile_prompt(
    tile_prompt: str,
    base_prompt: str = "",
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> tuple[str, bool]:
    """Build a CLIP-safe prompt that prioritizes tile-unique content.

    Order: [unique local detail] + [short base style tail]
    Truncates the style tail first if still too long; unique stays.
    """
    unique = strip_restated_base(tile_prompt, base_prompt)
    unique = _normalize(unique)
    tail = style_tail(base_prompt, max_words=12)

    # If unique is empty or still a novel, fall back to whole tile prompt
    if not unique or len(unique.split()) < 3:
        unique = _normalize(tile_prompt)

    # Prefer unique alone if it already fits
    if token_len(unique) <= max_tokens:
        if tail and token_len(unique + ", " + tail) <= max_tokens:
            combined = f"{unique}, {tail}"
            return combined, combined != _normalize(tile_prompt)
        return unique, unique != _normalize(tile_prompt)

    # Unique alone is too long — fit unique (it is the important part)
    fitted, _ = fit_clip_prompt(unique, max_tokens=max_tokens)
    return fitted, True
