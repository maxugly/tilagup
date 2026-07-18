# Spec: semantic zones

> **Status:** Designed / not yet implemented in code. Normative for the next feature work.  
> **Last updated:** 2026-07-17

## Problem

A uniform tile grid does not match image meaning. A coherent strip (track, flame, cable bundle) or a mass that spans several cells (pickle pile, face) should share identity. Independent per-tile prompts without a middle layer produce quilts or generic CLIP-truncated mush.

## Principles

1. **Zones are meaning; tiles are execution.**  
2. FastSD still consumes an overlapping **tile grid** with soft masks — we do not replace the blender.  
3. Prompt hierarchy: **base → zone → tile (unique-local only)**.  
4. CLIP budget (~75 tokens) applies at every layer; unique/local content is ordered first.  
5. Everything is archived: zone map, who wrote each zone/tile prompt.

## Data model

### Zone record

```json
{
  "id": "z_fire",
  "label": "organic digital flame column, right face",
  "bbox": [0.55, 0.05, 0.98, 0.75],
  "priority": 1,
  "notes": "vertical strip; plasma + embers",
  "prompt": "… short CLIP-safe zone prompt …",
  "attribution": { "agent": "agy", "cli": "agy", "…": "…" },
  "tile_ids": ["r01_c06", "r02_c06", "r03_c06"]
}
```

- **`bbox`:** normalized `[x0, y0, x1, y1]` in `[0,1]` relative to full image (resolution-independent).  
- **`priority`:** break ties when a tile overlaps multiple zones (higher wins), or use max overlap area.  
- Optional later: `mask_path` for non-rect regions (SAM).

### Tile record extensions

```json
{
  "id": "r02_c06",
  "zone_id": "z_fire",
  "zone_ids_secondary": [],
  "prompt": "local embers, silicon wafer glints…",
  "…": "existing geometry + attribution"
}
```

### `zone_map.json` (run root)

```json
{
  "version": 1,
  "assignment": "max_overlap",
  "tiles": {
    "r00_c00": "z_mycelium",
    "r02_c06": "z_fire"
  }
}
```

## Discovery (stage `zones`)

### v1 — vision agent JSON

Input: full-image path (+ optional downscaled preview).  
Output: **JSON only** (no prose wrapper), schema:

```json
{
  "zones": [
    {
      "id": "z_slug",
      "label": "short human label",
      "bbox": [0.0, 0.0, 1.0, 1.0],
      "priority": 1,
      "notes": "optional"
    }
  ]
}
```

Constraints for the agent:

- Prefer **4–12** zones (not one-per-tile, not one blob).  
- Cover the interesting structure; background may be a single `z_bg` zone.  
- Bboxes may overlap slightly at boundaries; assignment resolves ownership.  
- IDs: `z_[a-z0-9_]+`.

### v2 — optional CV assist (later)

SAM / superpixels propose candidates; agent only **names and merges**. Not required for v1.

## Assignment (stage `assign`)

After `split` produces tiles with pixel `x,y,w,h`:

1. Convert each tile rect to normalized coords.  
2. Compute intersection area with each zone bbox.  
3. `zone_id` = zone with max intersection (tie → higher `priority`, then stable id sort).  
4. If max intersection is ~0, assign `z_bg` or create residual zone covering unclaimed area.  
5. If second-best ≥ 30% of tile area, record in `zone_ids_secondary` (boundary tile).

## Prompting

### Zone prompt

Agent sees: full image (or zone crop from bbox) + base prompt + zone label/notes.  
Output: ≤50 words, CLIP-safe, describes **this region’s identity** only.

### Tile prompt

Agent sees: crop + base + **locked zone prompt** + variation.  
Output: ≤50 words, **unique-first** (what this crop adds inside the zone).  
Must **not** restate the full base or full zone essay.

### Effective SD string (conceptual)

```text
{zone_prompt}, {tile_local_prompt}
```

Then CLIP-fit unique-first if still over budget (prefer keeping `tile_local`).

## Archive layout (target)

```text
runs/<image_key>/<run_id>/
  run.json
  events.log
  source.*
  base_prompt.txt
  zone_map.json
  zones/
    z_fire.json
    z_fire.prompt.txt
    z_fire.png            # optional bbox crop
  tiles/
    r02_c06.png
    r02_c06.prompt.txt
    r02_c06.meta.json     # includes zone_id
  output.png
```

## Pipeline order

See root `AGENTS.md`. Zones stage runs **before** tile prompts; assignment after split.

## CLI (planned)

| Flag | Behavior |
|------|----------|
| (default) | Run with zones once implemented |
| `--no-zones` | Flat base→tile path (current behavior) |
| `--zones-json PATH` | Skip discovery; load human/edited zone map |
| `--reprompt-zones` | Redo zone prompts only |
| `--reprompt-tiles` | Already exists; will respect zone lock |

## Acceptance criteria

1. Dry-run writes `zones/` + `zone_map.json` with stable ids.  
2. Every tile has a `zone_id`.  
3. Tiles in the same zone share zone prompt text in their effective prompt.  
4. Tile prompts remain ≤75 CLIP tokens after fit.  
5. Upscale path unchanged except prompt content.  
6. `--no-zones` still produces a valid flat dry-run for regression.

## Non-goals (v1)

- Interactive zone painting UI  
- Perfect instance segmentation  
- Replacing FastSD tile blend  
- Multi-pass fractal “growth” stages (orthogonal experiment)
