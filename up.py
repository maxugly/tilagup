#!/usr/bin/env python3
"""Thin entry: `uv run up.py path/to/image.tiff …`"""

import os
import sys

# Force unbuffered stdio before anything else (uv/python wrappers love to buffer)
os.environ.setdefault("PYTHONUNBUFFERED", "1")
try:
    sys.stdout.reconfigure(line_buffering=True, write_through=True)  # type: ignore[attr-defined]
    sys.stderr.reconfigure(line_buffering=True, write_through=True)  # type: ignore[attr-defined]
except Exception:
    pass

from tilagup.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
