# Run archive format

Every invocation creates (or resumes) a directory under `runs/`. This is the source of truth for slow jobs.

## Directory layout

```text
runs/<run_id>/
  run.json              # authoritative machine state
  events.log            # append-only NDJSON trail
  source.<ext>          # copy of input
  base_prompt.txt       # convenience copy of base prompt text
  tiles/
    r00_c00.png         # crop for vision
    r00_c00.prompt.txt  # tile prompt text
    r00_c00.meta.json   # tile prompt + attribution + geometry
    …
  output.png            # final upscale (after SD stage)
```

`run_id` looks like `20260717_045012_ab12`.

## `run.json` (core fields)

```json
{
  "run_id": "20260717_045012_ab12",
  "created_at": "2026-07-17T04:50:12+00:00",
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
      "attribution": {
        "agent": "grok",
        "cli": "grok",
        "model": null,
        "duration_ms": 8000,
        "created_at": "…"
      },
      "status": "prompted",
      "error": null
    }
  ],
  "agents_used": ["agy", "grok"],
  "output": null,
  "error": null,
  "events": []
}
```

## Stages

| `stage` | Meaning |
|---------|---------|
| `init` | Directory created, source copied |
| `base_prompt` | Base prompt written |
| `split` | Tiles exported |
| `tile_prompts` | At least some tile prompts written (final when all done) |
| `dry_run_complete` | Prompts done; SD skipped |
| `done` | Upscale finished |
| `upscale_failed` | SD stage errored; safe to `--resume` after fix |

## Who did what

- **Base:** `run.json` → `base_prompt.attribution.agent`
- **Per tile:** `tiles[i].attribution.agent` and `tiles/<id>.meta.json`
- **Set of agents:** `agents_used[]`
- **Timeline:** `events.log` (NDJSON) and truncated `events` array in `run.json`

## Coordinates

`x, y, w, h` are **source image pixels**, FastSD-compatible. Overlap is baked into non-edge crop sizes the same way FastSD’s tiled upscaler expects.

Last updated: 2026-07-17
