# Getting started

Prerequisites, dry-run, and first real upscale.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- For real prompts: at least one vision CLI on `PATH`:
  - **`agy`** — headless (`agy -p "…"`)
  - **`grok`** — headless (`grok -p "…"`)
- For offline CI / plumbing checks: `--agent stub` (no external CLI)
- For actual SD upscale (not dry-run): a [FastSD CPU](https://github.com/rupeshs/fastsdcpu) checkout and `FASTSDCPU_ROOT` pointing at it

## Install

```bash
cd tilagup
uv sync
```

## Dry-run (recommended first)

Creates a full run archive: base prompt, tile crops, per-tile prompts, attribution JSON. **No** diffusion.

Offline smoke (no `agy`/`grok` required):

```bash
uv run up.py /path/to/image.png --agent stub --dry-run
```

Live agents:

```bash
uv run up.py /path/to/image.png \
  --variation 0.35 \
  --agent both \
  --dry-run
```

Expected:

```text
run_id:  20260717_…
path:    runs/20260717_…
stage:   dry_run_complete
tiles:   N
agents:  agy, grok
json:    runs/…/run.json
```

Inspect:

```bash
less runs/<id>/base_prompt.txt
ls runs/<id>/tiles/
jq '.tiles[] | {id, agent: .attribution.agent, status}' runs/<id>/run.json
```

## Real upscale

```bash
export FASTSDCPU_ROOT=/path/to/fastsdcpu
uv run up.py /path/to/image.png \
  --agent both \
  --variation 0.35 \
  --strength 0.28 \
  --scale 2
```

Output lands at `runs/<id>/output.png`. Progress is appended to `events.log` and mirrored in `run.json`.

## Resume

If a run dies mid-prompting or mid-upscale:

```bash
uv run up.py --resume runs/<id>
```

Completed base/tile prompts are skipped unless you pass `--force`.

## Flags cheat sheet

| Flag | Default | Notes |
|------|---------|--------|
| `--agent` | `both` | `agy` / `grok` / `both` (alternate tiles) |
| `--variation` | `0.35` | Prompt drift from base (0..1) |
| `--strength` | `0.28` | SD img2img strength |
| `--tile-size` | `256` | Grid stride |
| `--overlap` | `32` | Soft blend region |
| `--dry-run` | off | Prompts only |
| `--force` | off | Redo stages |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `agent CLI not on PATH: agy` | Install/link `agy`; or `--agent grok` |
| `FastSD CPU not found` | `export FASTSDCPU_ROOT=…` or use `--dry-run` |
| Quilt / seams | Lower `--variation` and/or `--strength`; ensure overlap ≥ 16 |
| Agent returns essays | Templates already demand prompt-only; check `tiles/*.meta.json` raw via events |

Last updated: 2026-07-17
