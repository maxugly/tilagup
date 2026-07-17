#!/usr/bin/env python3
"""Thin entry: `uv run up.py path/to/image.tiff …`"""

import sys

# Unbuffered-ish progress even under weird terminals / uv wrapping
try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except Exception:
    pass

from tilagup.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
