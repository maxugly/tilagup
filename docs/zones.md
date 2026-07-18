# Zones (operator guide)

**Last updated:** 2026-07-17  
**Code status:** Designed — not shipped yet. Flat grid dry-run/upscale works today.

## What a zone is

A **zone** is a coherent region of meaning in the image: a flame column, neon mycelium mass, drip base, cable forest, background slab, a strip that reads as one object across the width, a pile large enough to span several tiles.

Zones are **not** the same as tiles:

| | Zone | Tile |
|--|------|------|
| Meaning | Semantic region | Crop of the SD grid |
| Count | Usually 4–12 | Often dozens (e.g. 8×8) |
| Span | May cover many tiles | Fixed cell (+ overlap) |
| Prompt role | Shared identity for that region | Local detail inside the zone |

## Why you care

Without zones, every tile is a freestanding monologue. You pay for agents and still risk a quilt — or CLIP throws away the unique ending of a long prompt.

With zones:

1. **Base** — whole-image style  
2. **Zone** — “this is the fire column”  
3. **Tile** — only what *this* crop adds inside that column  

A racecar-track strip stays one track across a row of tiles. A pickle pile stays one pile across a few cells.

## What you will see on disk (when zones ship)

```text
runs/<image_key>/<run_id>/
  base_prompt.txt
  zone_map.json          # tile_id → zone_id
  zones/
    z_fire.json
    z_fire.prompt.txt
    z_fire.png           # optional crop
  tiles/
    r02_c06.prompt.txt
    r02_c06.meta.json    # includes zone_id
```

Inspect zone map before upscale the same way you inspect tile prompts today.

## Workflow (target)

```bash
# dry-run: base + zones + tile prompts (no SD)
uv run up.py image.png --agent both --dry-run

# inspect zone_map.json + zones/*.prompt.txt + tiles/*.prompt.txt

uv run up.py --resume runs/... --continue-upscale
```

Planned escapes:

- `--no-zones` — flat base→tile only (current behavior)  
- `--zones-json path` — inject a hand-edited zone map  

## Until zones ship

Use the flat path. Prefer short unique-first tile prompts (`--reprompt-tiles` if an old run has essay-length prompts). Upscale still CLIP-fits unique-first so local detail is not blindly chopped off the end.

## Spec

Normative detail: [design/zones.md](../design/zones.md).
