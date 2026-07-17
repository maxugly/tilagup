"""Loud-by-default CLI logging. Quiet is opt-in.

Progress goes to **stderr** so it still shows when stdout is redirected/piped,
and everything is flush=True. Dry-run is supposed to be watchable in the same
terminal — if you can't see it, that's a bug.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any


_quiet = False


def set_quiet(quiet: bool) -> None:
    global _quiet
    _quiet = bool(quiet)


def is_quiet() -> bool:
    return _quiet


def configure_stdio() -> None:
    """Best-effort line buffering so progress isn't stuck in a pipe buffer."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
        except Exception:
            pass


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def say(msg: str = "", *, err: bool = True) -> None:
    """Progress line (stderr by default). Always flush. Suppressed only by --quiet."""
    if _quiet:
        return
    stream = sys.stderr if err else sys.stdout
    print(f"[{_ts()}] {msg}", file=stream, flush=True)


def banner(title: str) -> None:
    if _quiet:
        return
    line = "═" * max(12, min(72, len(title) + 8))
    print(f"\n{line}\n  {title}\n{line}", file=sys.stderr, flush=True)


def kv(key: str, value: Any) -> None:
    say(f"  {key}: {value}")


def progress(current: int, total: int, label: str = "") -> None:
    """One-line progress: [████░░░░] 3/10 label"""
    if _quiet:
        return
    total = max(total, 1)
    width = 20
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = 100.0 * current / total
    extra = f"  {label}" if label else ""
    say(f"[{bar}] {current}/{total} ({pct:.0f}%){extra}")


def always(msg: str = "", *, err: bool = False) -> None:
    """Print even when quiet (final summary / hard errors)."""
    stream = sys.stderr if err else sys.stdout
    print(msg, file=stream, flush=True)
