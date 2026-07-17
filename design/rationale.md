# Rationale — tilagup core design

## Context

FastSD CPU’s tiled SD upscale already supports a **per-tile prompt** and soft masks. Humans cannot cheaply write N good tile prompts for weird images. Vision CLIs (`agy`, `grok`) can, if we keep a shared base and log everything (upscale is slow).

## Decisions

### 1. Archive-first runs

**Decision:** Every job is a directory under `runs/` with `run.json` + `events.log` before any expensive work.

**Why:** CPU/OpenVINO upscales take a long time. Crash recovery and “who wrote this prompt?” both need durable state.

### 2. Base-locked tile prompts

**Decision:** Base prompt first; every tile prompt is instructed to stay inside that style/subject. `--variation` only scales how much local invention is allowed.

**Why:** Independent free-form tile prompts produce quilts. Temperature alone is not enough.

### 3. Crops on disk, blend in FastSD

**Decision:** Export overlapping crops for agents and attribution; feed the same geometry into FastSD’s `tiles[]` rather than paste ourselves.

**Why:** Soft masks and overlap already exist. Reimplementing stitching is wasted risk.

### 4. Dual agents with attribution

**Decision:** Support `agy` and `grok`, optional `both` alternating, always record `attribution.agent` per prompt.

**Why:** User asked to maximize variation without inventing seams, and to know who did what.

### 5. Dry-run before SD

**Decision:** `--dry-run` completes base + split + tile prompts and stops.

**Why:** Inspect prompts before burning an hour of upscale.

### 6. `agy` means `agy`

**Decision:** Adapter invokes the `agy` binary only.

**Why:** Explicit user correction — not `antigravity`, not aliases that hang.

## Non-goals (v0.1)

- Interactive prompt editing UI
- Multi-pass hierarchical “growth” (gem.md-style stages)
- Named semantic zones (brain/flame) without a grid
- Parallel agent fan-out

## Consequences

- CLI surface stays small: `up.py` + resume + dry-run.
- JSON schema in `docs/run-archive.md` is part of the product.
- FastSD remains an external runtime dependency via `FASTSDCPU_ROOT`.
