"""Deterministic offline vision agent for CI / dry pipeline tests.

Never shells out. Optionally peeks at image pixels for mild content-aware text.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from tilagup.agents.base import AgentResult

_PATH_RE = re.compile(
    r"(?:Image path|Crop image path)[^:]*:\s*(\S+)",
    re.IGNORECASE,
)
_TILE_ID_RE = re.compile(r"tile id=([a-zA-Z0-9_]+)", re.IGNORECASE)
_ROW_COL_RE = re.compile(r"row=(\d+)\s+col=(\d+)", re.IGNORECASE)


def _image_hint(path: Path | None) -> str:
    if path is None or not path.is_file():
        return "unknown palette"
    try:
        from PIL import Image

        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((32, 32))
            w, h = im.size
            if w < 1 or h < 1:
                return "empty image"
            # sample grid (avoids deprecated Image.getdata)
            step_x = max(1, w // 8)
            step_y = max(1, h // 8)
            pixels = [
                im.getpixel((x, y))
                for y in range(0, h, step_y)
                for x in range(0, w, step_x)
            ]
        if not pixels:
            return "empty image"
        n = len(pixels)
        r = sum(p[0] for p in pixels) // n
        g = sum(p[1] for p in pixels) // n
        b = sum(p[2] for p in pixels) // n
        # crude brightness / warm-cool tag
        brightness = (r + g + b) / 3
        warmth = "warm" if r > b + 15 else ("cool" if b > r + 15 else "neutral")
        tone = "dark" if brightness < 85 else ("bright" if brightness > 170 else "midtone")
        return f"{tone} {warmth} palette rgb({r},{g},{b})"
    except Exception:
        return "unreadable image"


class StubAgent:
    """Fake vision agent — always available, prompt-only output."""

    name = "stub"
    cli = "stub"

    def __init__(self, *, label: str | None = None):
        # Optional distinct name for multi-stub experiments
        if label:
            self.name = label

    def available(self) -> bool:
        return True

    def complete(self, user_prompt: str, *, timeout_s: float = 300.0) -> AgentResult:
        from tilagup import log

        t0 = time.perf_counter()
        log.say("stub agent thinking (offline, no network)…")
        path_m = _PATH_RE.search(user_prompt)
        image_path = Path(path_m.group(1)) if path_m else None
        hint = _image_hint(image_path)

        tile_m = _TILE_ID_RE.search(user_prompt)
        rowcol = _ROW_COL_RE.search(user_prompt)
        is_tile = tile_m is not None or "This tile id=" in user_prompt

        if is_tile:
            tid = tile_m.group(1) if tile_m else "tile"
            row = rowcol.group(1) if rowcol else "?"
            col = rowcol.group(2) if rowcol else "?"
            # Pull a short slice of locked base if present
            base_snip = ""
            if "LOCKED" in user_prompt:
                # after LOCKED line until blank / This tile
                after = user_prompt.split("LOCKED", 1)[-1]
                lines = [ln.strip() for ln in after.splitlines() if ln.strip()]
                # first non-meta line after LOCKED header
                for ln in lines[1:]:
                    if ln.lower().startswith("this tile") or ln.lower().startswith("crop"):
                        break
                    if len(ln) > 20:
                        base_snip = ln[:160]
                        break
            text = (
                f"stub detail for {tid} (row {row} col {col}): "
                f"local microtexture and material continuity, {hint}"
            )
            if base_snip:
                text = f"{base_snip} — {text}"
        else:
            text = (
                f"stub base prompt: complex detailed scene, {hint}, "
                "preserve overall composition, rich surface structure for tiled upscale"
            )

        duration_ms = max(1, int((time.perf_counter() - t0) * 1000))
        return AgentResult(
            text=text,
            agent=self.name,
            cli=self.cli,
            model="stub-v1",
            duration_ms=duration_ms,
            raw=text,
            command=["stub", "-p", "<inline>"],
        )
