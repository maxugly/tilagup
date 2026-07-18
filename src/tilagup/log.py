"""Loud by default. --quiet exists if you actually want silence.

Progress prints once (stderr) so terminals don't double every line.
"""

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
    # Once, to stderr — always visible in an interactive terminal, not doubled
    print(f"[{_ts()}] {msg}", file=sys.stderr, flush=True)
    # keep sticky ETA bar fresh when a tracker is live
    try:
        from tilagup.job_status import get_tracker

        tr = get_tracker()
        if tr is not None:
            tr.tick()
    except Exception:
        pass


def say(msg: str = "", **_ignored: Any) -> None:
    _emit(msg)


def banner(title: str) -> None:
    if _quiet:
        return
    line = "═" * max(12, min(72, len(title) + 8))
    print(f"\n{line}\n  {title}\n{line}", file=sys.stderr, flush=True)


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
    if _quiet:
        return
    _emit(f"──── {title} ────")
    print(text if text.endswith("\n") else text + "\n", file=sys.stderr, flush=True)
    _emit(f"──── end {title} ({len(text)} chars) ────")


def always(msg: str = "", **_ignored: Any) -> None:
    """Final summary / hard errors — still prints when --quiet."""
    print(msg, file=sys.stderr, flush=True)
    # also stdout so capture tools see the summary
    print(msg, file=sys.stdout, flush=True)
