"""Loud by default. --quiet exists if you actually want silence."""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any


_quiet = False


def set_quiet(quiet: bool) -> None:
    global _quiet
    _quiet = bool(quiet)


def is_quiet() -> bool:
    return _quiet


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True, write_through=True)  # type: ignore[attr-defined]
        except Exception:
            pass


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _emit(msg: str) -> None:
    if _quiet:
        return
    line = f"[{_ts()}] {msg}"
    for stream in (sys.stdout, sys.stderr):
        try:
            print(line, file=stream, flush=True)
        except Exception:
            pass


def say(msg: str = "", **_ignored: Any) -> None:
    _emit(msg)


def banner(title: str) -> None:
    if _quiet:
        return
    line = "═" * max(12, min(72, len(title) + 8))
    block = f"\n{line}\n  {title}\n{line}"
    for stream in (sys.stdout, sys.stderr):
        try:
            print(block, file=stream, flush=True)
        except Exception:
            pass


def kv(key: str, value: Any) -> None:
    _emit(f"  {key}: {value}")


def progress(current: int, total: int, label: str = "") -> None:
    if _quiet:
        return
    total = max(total, 1)
    width = 24
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = 100.0 * current / total
    extra = f"  {label}" if label else ""
    _emit(f"[{bar}] {current}/{total} ({pct:.0f}%){extra}")


def dump(title: str, text: str) -> None:
    """Print a multi-line blob with a header (full prompts). Suppressed when quiet."""
    if _quiet:
        return
    _emit(f"──── {title} ────")
    for stream in (sys.stdout, sys.stderr):
        try:
            print(text if text.endswith("\n") else text + "\n", file=stream, flush=True)
        except Exception:
            pass
    _emit(f"──── end {title} ({len(text)} chars) ────")


def always(msg: str = "", **_ignored: Any) -> None:
    """Final summary / hard errors — still prints when --quiet."""
    line = msg
    # keep errors visible on stderr; summaries on both
    for stream in (sys.stdout, sys.stderr):
        try:
            print(line, file=stream, flush=True)
        except Exception:
            pass
