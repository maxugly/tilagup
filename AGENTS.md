# AGENTS.md — tilagup Repository

> *For autonomous agents working in this repo. Humans: this is how the robots understand the project. Read it anyway.*

## Project Identity

- **Name:** tilagup (tiled agent upscale)
- **Type:** CLI + library for agent-driven tiled SD upscaling
- **Language:** Python 3.11+
- **Version:** 0.1.0-prealpha
- **Entry:** `uv run up.py <image>` or `uv run tilagup <image>`

## Architecture (authoritative mental model)

```text
image
  ├─ base          soul / style / whole composition
  ├─ zones[]       semantic regions (coherent meaning; may span many tiles)
  └─ tiles[]       overlapping FastSD execution grid
                     each tile → primary zone_id + short unique-local prompt
```

| Layer | Purpose | CLIP |
|-------|---------|------|
| **Base** | Global style lock | Short (≤~50 words / ≤75 tokens) |
| **Zone** | Object/scene strip identity (track, flame, mycelium, drip…) | Short zone prompt |
| **Tile** | Local micro-detail **inside** its zone only | Unique-first, ≤75 tokens |

**Zones are meaning. Tiles are execution.** Do not invent a second stitcher — FastSD tiled upscale + soft masks remain the blend path.

Normative zone design: **`design/zones.md`**. User-facing: **`docs/zones.md`**.

## What works today vs next

| Capability | Status |
|------------|--------|
| Run archive `runs/<image_key>/<run_id>/` | Shipped |
| Base + flat grid tile prompts | Shipped |
| Loud CLI / dry-run / resume / `--reprompt-tiles` | Shipped |
| CLIP fit (unique-first at upscale; short agent templates) | Shipped |
| FastSD worker in FastSD venv (`FASTSDCPU_ROOT`) | Shipped |
| Zone discovery, zone prompts, tile→zone assignment | **Next** (spec ready) |

When implementing zones, update `run.json` schema + archive layout in the same PR as code. Do not leave docs lying.

## Repository Layout

```text
tilagup/
├── AGENTS.md
├── README.md
├── up.py
├── design/                 # architecture (zones.md is normative)
├── docs/                   # operators
├── src/tilagup/            # library
│   ├── agents/             # agy / grok / stub
│   ├── archive.py
│   ├── pipeline.py
│   ├── tiles.py            # grid math (execution)
│   ├── clip_fit.py
│   ├── upscale_fastsd.py
│   └── upscale_worker.py
├── tests/
└── runs/                   # gitignored archives
```

## Conventions

1. **AGENTS.md in every directory.** Read it before editing files there.
2. **Run archives are sacred.** Never delete `runs/…` without explicit human OK.
3. **Loud by default.** Same terminal; `--quiet` only if asked. No “tail the log in another pane” as the primary UX.
4. **Hierarchy:** base → zone → tile. Tile prompts must not invent a new global scene.
5. **Unique-first.** Local/zone-specific detail comes before shared fluff so CLIP truncation cannot kill uniqueness.
6. **Reuse FastSD blend.** Feed `tiles[]` into FastSD’s tiled upscaler.
7. **Agent output is boring.** Prompt text only (or JSON for zone maps). Parse fail → retry → log + fail.
8. **Machine state = JSON; humans = markdown.**

### Naming

| Kind | Style |
|------|--------|
| Modules | `snake_case.py` |
| Docs | `lowercase-hyphenated.md` |
| Run IDs | `YYYYMMDD_HHMMSS_<short>` |
| Tile IDs | `r{row:02d}_c{col:02d}` |
| Zone IDs | `z_<slug>` (e.g. `z_fire`, `z_mycelium`) |
| JSON fields | `snake_case` |

### Commit prefixes

`feat:` `fix:` `docs:` `design:` `chore:` `test:`

### Agent attribution

```json
{
  "agent": "agy",
  "cli": "agy",
  "model": null,
  "duration_ms": 12000,
  "created_at": "ISO-8601"
}
```

Allowed `agent`: `agy`, `grok`, `stub`, `human`, `unknown`.

## Pipeline stages (target order)

1. `init` — copy source, meta  
2. `zones` — discover zones (agent JSON / future SAM)  
3. `base_prompt` — global soul (may use zone list)  
4. `split` — overlapping tile grid  
5. `assign` — tile → primary zone (overlap)  
6. `zone_prompts` — one short prompt per zone  
7. `tile_prompts` — unique-local under zone lock  
8. `dry_run_complete` or `upscale` → `done`

**Shipped today:** 1, 3, 4, 7 (flat: no zone lock), 8.  
**Next:** 2, 5, 6, and zone lock on 7.

## Next implementation focus

Build zone discovery + assignment + zone prompts per `design/zones.md`. Keep flat path as `--no-zones` fallback until zones are default.
