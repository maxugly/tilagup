# Getting started

**Last updated:** 2026-07-17

End-to-end dry-run and upscale with the **current flat-grid** pipeline.  
Zones (semantic regions) are designed next — see [zones.md](zones.md) and [design/zones.md](../design/zones.md).

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- For real prompts: `agy` and/or `grok` on `PATH`
- For offline plumbing tests: `--agent stub`
- For upscale: FastSD CPU checkout + `FASTSDCPU_ROOT`  
  - fish (persistent): `set -Ux FASTSDCPU_ROOT /path/to/fastsdcpu`  
  - No FastSD web server required

## Install

```bash
cd tilagup
uv sync
```

## Dry-run (recommended first)

Real agent prompts, **no** diffusion. Watch the **same terminal** (loud by default).

```bash
uv run up.py /path/to/image.png \
  --variation 0.35 \
  --agent both \
  --dry-run
```

Offline smoke:

```bash
uv run up.py /path/to/image.png --agent stub --dry-run
```

Expected artifacts under `runs/<image_key>/<run_id>/`:

- `run.json`, `events.log`, `source.*`
- `base_prompt.txt`
- `tiles/rXX_cYY.png` + `.prompt.txt` + `.meta.json`

CLI prints `path:` / `json:` when finished. Stage: `dry_run_complete`.

On a real TTY you also get a **sticky status strip at the bottom**: elapsed / ETA,
step x/x, tile x/x, done-step timings, and upcoming estimates. Verbose log still
scrolls above. Timing samples are written to `runs/.../timing.json` and aggregated
in `~/.local/share/tilagup/timing_history.json` for smarter ETAs over time.

### Inspect prompts

```bash
set run runs/<image_key>/<run_id>
cat $run/base_prompt.txt
# word / token-ish length
wc -w $run/tiles/*.prompt.txt | sort -n | tail
```

Prompts should stay short (≤~50 words). Unique local detail should lead. If a run still has long essays from an older build:

```bash
uv run up.py --resume $run --reprompt-tiles
```

## Upscale

Only after you like the prompts:

```bash
# FASTSDCPU_ROOT already set in your shell
uv run up.py --resume runs/<image_key>/<run_id> --continue-upscale
```

Uses FastSD’s own venv Python. Per-tile prompts go through unique-first CLIP fit (~75 tokens) so local detail is preferred over restated base fluff.

Output: `runs/.../output.png`, stage `done`.

## Resume

```bash
uv run up.py --resume runs/<image_key>/<run_id>
```

Without `--dry-run`, a completed dry-run continues to upscale.  
With `--dry-run` on an already complete dry-run: no-op unless `--reprompt-tiles` / `--force`.

## Flags

| Flag | Default | Notes |
|------|---------|--------|
| `--agent` | `both` | `agy` / `grok` / `both` / `stub` |
| `--variation` | `0.35` | Prompt drift guidance |
| `--strength` | `0.28` | SD img2img strength |
| `--texture` | `none` | Upscale-only pack: `none` (default, unchanged), `grit`, `smooth` |
| `--texture-strength` | `1.0` | 0..1 how hard the pack applies |
| `--tile-size` | `256` | Grid stride |
| `--overlap` | `32` | Soft blend region |
| `--dry-run` | off | Prompts only |
| `--continue-upscale` | off | After dry-run → SD |
| `--reprompt-tiles` | off | Wipe + regenerate tile prompts |
| `--quiet` | off | Mute progress |
| `--force` | off | Redo stages |

## Architecture reminder

```text
target:  base → zones → tiles → FastSD
today:   base → tiles (flat) → FastSD
```

When zones land, dry-run will also write `zones/` + `zone_map.json`. Until then, flat is the testable path.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `agent CLI not on PATH` | Install `agy`/`grok`, or `--agent stub` |
| `FastSD CPU not found` | `set -Ux FASTSDCPU_ROOT …` |
| `No module named 'yaml'` / missing torch | Fixed by worker using FastSD venv — update code; do not install torch into tilagup |
| CLIP truncate / long prompts | `--reprompt-tiles`; agents must stay short |
| Quilt / seams | Lower `--variation` / `--strength`; zones will help when shipped |
| Blank terminal | Old build; current code is loud in-process |

## Related

- [Run archive](run-archive.md)
- [Agents](agents.md)
- [Zones](zones.md)
