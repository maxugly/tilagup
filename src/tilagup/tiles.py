"""Tile grid math and crop export (overlap-aware, FastSD-compatible coords)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class TileSpec:
    id: str
    row: int
    col: int
    x: int
    y: int
    w: int
    h: int
    # soft-mask offset inside tile (0 on first row/col)
    x_offset: int
    y_offset: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "row": self.row,
            "col": self.col,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "x_offset": self.x_offset,
            "y_offset": self.y_offset,
        }


def compute_tiles(
    width: int,
    height: int,
    *,
    tile_size: int = 256,
    overlap: int = 32,
) -> list[TileSpec]:
    """Match FastSD-style grid: stride = tile_size, edge tiles may include overlap padding.

    Source crop size is tile_size + overlap on non-final edges (same idea as
    fastsdcpu tiled_upscale.py).
    """
    if tile_size < 64:
        raise ValueError("tile_size must be >= 64")
    if overlap < 0 or overlap >= tile_size:
        raise ValueError("overlap must be in [0, tile_size)")

    total_cols = max(1, math.ceil(width / tile_size))
    total_rows = max(1, math.ceil(height / tile_size))
    tiles: list[TileSpec] = []

    for row in range(total_rows):
        y_offset = overlap if row > 0 else 0
        for col in range(total_cols):
            x_offset = overlap if col > 0 else 0
            x1 = col * tile_size
            y1 = row * tile_size
            # width/height of source crop
            w = tile_size + (overlap if col < total_cols - 1 else 0)
            h = tile_size + (overlap if row < total_rows - 1 else 0)
            # clamp to image bounds
            if x1 >= width or y1 >= height:
                continue
            w = min(w, width - x1)
            h = min(h, height - y1)
            # Expand tiny edge slivers left/up so margins are never dropped
            if w < 8 and x1 > 0:
                grow = min(8 - w, x1)
                x1 -= grow
                w += grow
            if h < 8 and y1 > 0:
                grow = min(8 - h, y1)
                y1 -= grow
                h += grow
            if w < 1 or h < 1:
                continue
            tid = f"r{row:02d}_c{col:02d}"
            tiles.append(
                TileSpec(
                    id=tid,
                    row=row,
                    col=col,
                    x=x1,
                    y=y1,
                    w=w,
                    h=h,
                    x_offset=x_offset if col > 0 else 0,
                    y_offset=y_offset if row > 0 else 0,
                )
            )
    return tiles


def export_crops(
    source: Path,
    tiles_dir: Path,
    tiles: list[TileSpec],
    *,
    format: str = "PNG",
) -> list[dict[str, Any]]:
    """Write tile crops; return tile dicts ready for run.json (status=pending)."""
    tiles_dir.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    with Image.open(source) as im:
        im = im.convert("RGB")
        for t in tiles:
            crop = im.crop((t.x, t.y, t.x + t.w, t.y + t.h))
            rel_png = f"tiles/{t.id}.png"
            path = tiles_dir / f"{t.id}.png"
            crop.save(path, format=format)
            crop.close()
            rec = t.as_dict()
            rec.update(
                {
                    "crop_path": rel_png,
                    "prompt_path": f"tiles/{t.id}.prompt.txt",
                    "meta_path": f"tiles/{t.id}.meta.json",
                    "prompt": None,
                    "attribution": None,
                    "status": "pending",
                    "error": None,
                }
            )
            out.append(rec)
    return out


def load_image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size
