"""Fit prompts into CLIP's ~77 token limit (SD1.5 / turbo OpenVINO path)."""

from __future__ import annotations

from functools import lru_cache

# Leave headroom for BOS/EOS and model quirks
DEFAULT_MAX_TOKENS = 75


@lru_cache(maxsize=1)
def _clip_tokenizer():
    try:
        from transformers import CLIPTokenizer  # type: ignore

        return CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
    except Exception:
        return None


def token_len(text: str) -> int:
    tok = _clip_tokenizer()
    if tok is not None:
        # no special tokens in the count we care about for the free-form prompt body
        ids = tok.encode(text, add_special_tokens=False)
        return len(ids)
    # crude fallback: ~0.75 words/token is optimistic; use word count as upper bound
    return max(1, len(text.split()))


def fit_clip_prompt(text: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> tuple[str, bool]:
    """Return (prompt, was_truncated). Prefer whole words; never exceed max_tokens if tokenizer works."""
    text = " ".join((text or "").split()).strip()
    if not text:
        return "", False
    if token_len(text) <= max_tokens:
        return text, False

    # Binary-search character cut, then snap to word boundary
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
        # last resort: first N words
        words = text.split()
        best = " ".join(words[: max(8, max_tokens // 2)])
        while best and token_len(best) > max_tokens:
            words = best.split()[:-1]
            best = " ".join(words)

    return best, True
