# tilagup — tiled agent upscale

Agent-driven **tiled Stable Diffusion upscale** with full run archives: who wrote each prompt, zone identity (design), and where a slow job died.

**Product model (target):** chop the image by **meaning** (zones), execute by **tiles** (FastSD grid).

```text
image
  → base prompt          (soul / style of the whole)
  → zones[]              (coherent regions: fire column, track strip, pickle pile…)
  → tiles[]              (overlapping SD grid; each tile belongs to a zone)
  → FastSD tiled upscale (per-tile prompts + soft masks)
```

```bash
uv run up.py path/to/image.png --agent both --variation 0.35 --dry-run
uv run up.py --resume runs/<image_key>/<run_id> --continue-upscale
```

## Status

| Layer | State |
|-------|--------|
| Run archives, loud CLI, dry-run / resume | **Shipped** |
| Base + flat grid tile prompts (`agy` / `grok` / `stub`) | **Shipped** |
| CLIP-safe short prompts (≤~75 tokens, unique-first) | **Shipped** |
| FastSD upscale via FastSD’s own venv | **Shipped** |
| **Semantic zones** (discover → assign tiles → zone prompts) | **Designed — next build** |

Flat grid works today so you can test end-to-end. Zones are the hierarchy that makes per-tile work *worth* the agent time (see [design/zones.md](design/zones.md)).

## Why zones

A dumb grid does not know a racecar strip is one object across many tiles, or that a pickle pile spans a few cells. Without zones, agents invent 64 almost-independent monologues → quilt risk, or CLIP truncation kills the unique tail.

With zones:

- **Base** — shared materials, lighting, palette  
- **Zone** — coherent identity for a region (may span many tiles)  
- **Tile** — short local delta only, unique-first, CLIP-safe  

Same zone → shared spine. Adjacent tiles stay one track / one pile / one flame column.

## Quickstart (what works now)

### Prerequisites

- Python 3.11+, [uv](https://github.com/astral-sh/uv)
- Vision: `agy` and/or `grok` on `PATH` (or `--agent stub` for offline plumbing)
- Upscale: [FastSD CPU](https://github.com/rupeshs/fastsdcpu) checkout; `FASTSDCPU_ROOT` set (fish: `set -Ux FASTSDCPU_ROOT /path/to/fastsdcpu`)

No FastSD **server** is required — tilagup spawns FastSD’s venv Python in-process for the worker.

### Install

```bash
cd tilagup
uv sync
```

### Dry-run (prompts only, no SD)

```bash
uv run up.py /path/to/image.png --agent both --variation 0.35 --dry-run
```

Creates `runs/<image_key>/<run_id>/` with `run.json`, `base_prompt.txt`, `tiles/*`, attribution. **Loud by default** in the same terminal.

### Upscale after you like the prompts

```bash
uv run up.py --resume runs/<image_key>/<run_id> --continue-upscale
```

### Other flags

| Flag | Role |
|------|------|
| `--agent agy\|grok\|both\|stub` | Who writes prompts |
| `--variation` | How far tile prompts may drift (agent instruction) |
| `--strength` | SD img2img strength |
| `--reprompt-tiles` | Wipe tile prompts, regenerate short unique-first ones |
| `--quiet` | Mute progress (final summary still prints) |

## Layout

```text
tilagup/
├── AGENTS.md
├── README.md
├── up.py
├── design/          # architecture & rationale (zones spec lives here)
├── docs/            # user guides
├── src/tilagup/     # library
├── tests/
└── runs/            # local archives (gitignored)
```

## Docs

| Doc | Content |
|-----|---------|
| [Getting started](docs/getting-started.md) | Install, dry-run, upscale |
| [Run archive](docs/run-archive.md) | On-disk layout + `run.json` |
| [Agents](docs/agents.md) | `agy` / `grok` / `stub`, attribution |
| [Zones (user)](docs/zones.md) | What zones mean for operators |
| [Zones (spec)](design/zones.md) | Normative zone architecture |
| [Rationale](design/rationale.md) | Why we chose this shape |

## License

MIT (see `LICENSE`).
