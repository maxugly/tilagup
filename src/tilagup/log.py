"""Loud-by-default CLI logging. Quiet is opt-in, not the default lifestyle."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any, TextIO


_quiet = False
_stream: TextIO = sys.stderr  # progress on stderr so stdout can stay clean for scripting if needed
# Actually user wants to SEE things — use stdout for progress. Scripts can --quiet.


def set_quiet(quiet: bool) -> None:
    global _quiet
    _quiet = bool(quiet)


def is_quiet() -> bool:
    return _quiet


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def say(msg: str = "", *, err: bool = False) -> None:
    """Print a progress line unless --quiet."""
    if _quiet:
        return
    stream = sys.stderr if err else sys.stdout
    print(f"[{_ts()}] {msg}", file=stream, flush=True)


def banner(title: str) -> None:
    if _quiet:
        return
    line = "─" * max(8, len(title) + 4)
    print(f"\n{line}\n  {title}\n{line}", flush=True)


def kv(key: str, value: Any) -> None:
    say(f"  {key}: {value}")


def always(msg: str, *, err: bool = False) -> None:
    """Print even when quiet (errors / final path summary)."""
    stream = sys.stderr if err else sys.stdout
    print(msg, file=stream, flush=True)
