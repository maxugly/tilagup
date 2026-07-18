# Rationale — tilagup

**Last updated:** 2026-07-17

## Context

FastSD CPU’s tiled SD upscale already supports a **per-tile prompt** and soft masks. Humans cannot cheaply write N good tile prompts. Vision CLIs (`agy`, `grok`) can — if hierarchy and CLIP limits are respected, and slow jobs are fully archived.

## Decisions

### 1. Archive-first runs

**Decision:** Every job is `runs/<image_key>/<run_id>/` with `run.json` + `events.log` before expensive work.

**Why:** Upscales take a long time. Crash recovery and “who wrote this?” need durable state. Per-image folders keep attempts for the same source together.

### 2. Hierarchy: base → zones → tiles

**Decision:** Semantic **zones** (meaning) sit between global base and execution tiles. See `design/zones.md`.

**Why:** Flat independent tile prompts under-use agents and quilt easily. A racecar strip or pickle pile is one zone spanning many tiles; shared zone identity keeps coherence while tiles add local depth.

**Status:** Designed; flat path shipped first so the pipeline could be tested end-to-end.

### 3. Tiles remain the execution grid

**Decision:** Keep FastSD’s overlapping grid + soft masks. Assign tiles to zones by overlap; do not invent a new paste path.

**Why:** Blend quality already exists. Zones change *prompts*, not geometry of stitching.

### 4. CLIP-safe unique-first prompts

**Decision:** Agent templates demand ≤~50 words; rewrite if long; upscale worker CLIP-fits with unique-first (strip restated base, keep local, then style tail). Max ~75 tokens for SD1.5/turbo.

**Why:** CLIP drops tokens beyond ~77. Head-truncating long essays kills the unique tail — defeating per-tile work. Unique-first is non-negotiable.

### 5. Loud CLI by default

**Decision:** Progress, full prompts, agent streams, heartbeats in the **same** terminal. `--quiet` exists but is opt-in.

**Why:** Dry-run exists to watch and judge. Silent tools are unusable for this workflow.

### 6. FastSD in FastSD’s venv

**Decision:** Upscale worker runs under `FASTSDCPU_ROOT/env/bin/python`, not tilagup’s slim venv.

**Why:** torch/openvino/diffusers live there. tilagup stays light; no need for a FastSD HTTP server.

### 7. Dual live agents + stub

**Decision:** `agy`, `grok`, `both` (alternate), `stub` for CI.

**Why:** Attribution + variation; stub exercises the full dry-run without network.

### 8. Dry-run before SD

**Decision:** `--dry-run` completes prompts and stops; `--continue-upscale` / resume without dry-run runs SD.

**Why:** Inspect prompts (and later zone maps) before burning hours.

## Rejected / deferred

| Idea | Why not now |
|------|-------------|
| Quiet-by-default CLI | Operator cannot test dry-runs |
| Head-truncate long prompts only | Destroys unique tile content |
| Replace grid with freeform regions only | Loses FastSD soft-mask path |
| Interactive prompt UI | After zones land |
| Parallel agent fan-out | Nice; sequential is fine for v0.1 |

## Consequences

- Docs and `run.json` must grow zone fields without breaking flat runs (`--no-zones`).  
- Zone discovery quality is the main product bet after the flat path is proven.  
- Archive layout under `zones/` is part of the product, not an afterthought.
