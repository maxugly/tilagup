# tilagup — tiled agent upscale

Agent-driven **tiled Stable Diffusion upscale**: one base prompt for the whole image, then a unique agent-written prompt per tile, with full run archives so you can always see **who wrote what** and **where a slow job died**.

```bash
uv run up.py path/to/image.tiff --variation 0.35 --dry-run
uv run up.py path/to/image.tiff --agent both --strength 0.28
uv run up.py --resume runs/20260717_045012_ab12
```

## Why

SD tiled upscale already accepts a prompt **per tile**. Humans writing those by hand is tedious. Vision CLIs (`agy`, `grok`) can look at each crop and invent local micro-detail **on top of a shared base prompt**, with a variation knob so you get richness without a quilt.

## Status

**0.1.0-prealpha** — scaffold + core pipeline. FastSD CPU required for the actual upscale pass.

## Layout

```
tilagup/
├── AGENTS.md           — how agents work in this repo
├── README.md           — this file
├── up.py               — CLI entry
├── design/             — rationale
├── docs/               — user guides
├── src/tilagup/        — library
├── tests/
└── runs/               — local archives (gitignored)
```

## Quickstart

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Optional for prompting: `agy` and/or `grok` on `PATH`
- Optional for upscale: [FastSD CPU](https://github.com/rupeshs/fastsdcpu) checkout + `FASTSDCPU_ROOT`

### Install

```bash
cd tilagup
uv sync
```

### Dry-run (prompts + tiles, no SD)

```bash
uv run up.py /path/to/weird.png \
  --variation 0.35 \
  --agent both \
  --dry-run
```

Creates `runs/<image_key>/<run_id>/` with:

| Path | Purpose |
|------|---------|
| `run.json` | Full state: config, base prompt + agent, every tile + prompt + who wrote it |
| `events.log` | Append-only human trail |
| `source.*` | Copy of input |
| `base_prompt.txt` | Soul of the image |
| `tiles/r00_c00.png` | Crop for vision |
| `tiles/r00_c00.prompt.txt` | Tile prompt text |
| `tiles/r00_c00.meta.json` | Per-tile agent attribution |

CLI is **loud by default** (stage banners, tile progress, agent output). Pass `--quiet` only if you want it muted.

### Real upscale

```bash
export FASTSDCPU_ROOT=/path/to/fastsdcpu
uv run up.py /path/to/weird.png --strength 0.28 --scale 2
```

### Resume

```bash
uv run up.py --resume runs/<image_key>/20260717_045012_ab12
```

Skips stages already marked complete in `run.json` (base prompt, tile prompts, etc.).

## Agents

| CLI | Binary | Role |
|-----|--------|------|
| Antigravity stack | `agy` | Headless vision via `agy -p` |
| Grok | `grok` | Headless vision via `grok -p` |
| Stub (offline) | *(in-process)* | CI / plumbing; `--agent stub` |

`--agent agy|grok|both|stub` — `both` alternates live agents; `stub` never shells out.

## Variation vs strength

| Flag | Meaning |
|------|---------|
| `--variation` | How far tile **prompts** may drift from the base (agent instruction) |
| `--strength` | How hard **SD** may reinvent each crop (img2img strength) |

Keep both moderate unless you want a quilt (or you want a quilt).

## Docs

- [Getting started](docs/getting-started.md)
- [Run archive format](docs/run-archive.md)
- [Agent prompting](docs/agents.md)
- [Design rationale](design/rationale.md)

## License

MIT (see `LICENSE`).
