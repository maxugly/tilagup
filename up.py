#!/usr/bin/env python3
"""Thin entry: `uv run up.py path/to/image.tiff …`"""

from tilagup.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
