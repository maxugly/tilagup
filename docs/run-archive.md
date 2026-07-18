# Run archive format

**Last updated:** 2026-07-17

Every invocation creates (or resumes) a directory under `runs/`. This is the source of truth for slow jobs.

## Directory layout (current + target)

```text
runs/
  <image_key>/                         # stem + short path hash
    <run_id>/                          # 20260717_045012_ab12
      run.json                         # authoritative machine state
      events.log                       # append-only NDJSON trail
      source.<ext>
      base_prompt.txt
      tiles/
        r00_c00.png
        r00_c00.prompt.txt
        r00_c00.meta.json
        …
      upscale_job.json                 # written at upscale handoff
      output.png                       # after SD

      # --- when zones ship ---
      zone_map.json                    # tile_id → zone_id
      zones/
        z_fire.json
        z_fire.prompt.txt
        z_fire.png                     # optional bbox crop
```

`image_key` = sanitized stem + short hash of absolute path.  
`run_id` = timestamp + short random.

## Stages

| `stage` | Meaning |
|---------|---------|
| `init` | Directory created, source copied |
| `zones` | *(planned)* Zone discovery done |
| `base_prompt` | Base prompt written |
| `split` | Tiles exported |
| `assign` | *(planned)* Tiles assigned to zones |
| `zone_prompts` | *(planned)* Per-zone prompts written |
| `tile_prompts` | Tile prompts in progress / done |
| `dry_run_complete` | Prompts done; SD skipped |
| `done` | Upscale finished |
| `upscale_failed` | SD stage errored; safe to resume after fix |

## `run.json` (core fields today)

```json
{
  "run_id": "20260717_045012_ab12",
  "image_key": "HIsharp__a1b2c3",
  "created_at": "…",
  "updated_at": "…",
  "stage": "dry_run_complete",
  "source": {
    "original_path": "/abs/path/in.png",
    "path": "source.png",
    "sha256": "…",
    "width": 1024,
    "height": 1024,
    "mode": "RGB"
  },
  "config": {
    "agent": "both",
    "variation": 0.35,
    "strength": 0.28,
    "scale": 2.0,
    "tile_size": 256,
    "overlap": 32,
    "negative_prompt": "…",
    "dry_run": true
  },
  "base_prompt": {
    "text": "…",
    "token_len": 42,
    "attribution": {
      "agent": "agy",
      "cli": "agy",
      "model": null,
      "duration_ms": 12345,
      "created_at": "…"
    }
  },
  "negative_prompt": "…",
  "tiles": [
    {
      "id": "r00_c00",
      "row": 0,
      "col": 0,
      "x": 0,
      "y": 0,
      "w": 288,
      "h": 288,
      "crop_path": "tiles/r00_c00.png",
      "prompt_path": "tiles/r00_c00.prompt.txt",
      "meta_path": "tiles/r00_c00.meta.json",
      "prompt": "…",
      "token_len": 38,
      "zone_id": null,
      "attribution": { "agent": "grok", "cli": "grok", "…": "…" },
      "status": "prompted",
      "error": null
    }
  ],
  "zones": [],
  "agents_used": ["agy", "grok"],
  "output": null,
  "error": null,
  "events": []
}
```

### Planned fields (zones)

- `zones`: array of zone records (`id`, `label`, `bbox`, `prompt`, `attribution`, `tile_ids`)  
- `tiles[].zone_id`: primary zone  
- `tiles[].zone_ids_secondary`: boundary overlaps  
- top-level or file `zone_map.json` for quick inspection  

See [design/zones.md](../design/zones.md).

## Coordinates

`x, y, w, h` are **source image pixels**, FastSD-compatible. Overlap is baked into non-edge crop sizes.

Zone `bbox` values (planned) are **normalized** `[0,1]` on the full image.

## Who did what

- Base: `base_prompt.attribution`  
- Zone *(planned)*: `zones[i].attribution`  
- Tile: `tiles[i].attribution` + `tiles/<id>.meta.json`  
- Set: `agents_used[]`  
- Timeline: `events.log`

## Progress

Loud CLI prints stage banners, tile N/M, agent streams, heartbeats. `events.log` mirrors machine events; you should not need a second terminal to know the job is alive.
