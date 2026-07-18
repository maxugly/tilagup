# tilagup presets

Named **dry-run** + **upscale** script pairs so you don’t have to remember flags.

## Usage

```fish
cd /home/m/snc/cod/tilagup   # or any dir; scripts find the repo

# 1) agents write prompts (no SD)
./presets/grit_dry.sh /path/to/image.png

# 2) when you like the prompts — same preset’s upscale
./presets/grit_upscale.sh
# or pin a run:
./presets/grit_upscale.sh runs/SomeImage__abc/20260718_...
```

`*_upscale.sh` with no args uses the **newest** `runs/*/*/run.json`.

## Layout

| Script | Role |
|--------|------|
| `_lib.sh` | Shared helpers (repo root, `uv run`, latest run) |
| `*_dry.sh` | Image path required → dry-run with that preset’s flags |
| `*_upscale.sh` | Optional run dir → continue-upscale with matching flags |

## Bundled presets

| Name | Dry-run | Upscale extras |
|------|---------|----------------|
| `default` | agent both, variation 0.35 | strength 0.28, texture **none** (stock look) |
| **`photo_soft`** | both, variation **0.20** | strength **0.18**, texture **none** — **best photo preserve on this stack** |
| **`cartoon_ink`** | both, variation **0.40** | strength **0.32**, texture **none**, negatives ban **photo/3d** (not cartoon) — Waldo / comic / flat ink |
| `grit` | same | strength 0.28, texture **grit** |
| `grit_hot` | same | strength **0.40**, texture grit |
| `smooth` | same | strength 0.28, texture **smooth** |
| `stub_smoke` | agent **stub** (no live LLMs) | strength 0.28, texture none (CI / wiring check) |

**Photo tip:** For real photos (crowds, landscapes), use `photo_soft_*`. Higher strength / grit tends to invent generic people and smooth “poster” water on sd-turbo.

**Cartoon tip:** Default negatives ban `cartoon` / `drawing` / `illustration` — bad for Waldo-style art. Use `cartoon_ink_*` so upscale negatives push away photoreal instead.

## Add your own

Copy a pair, rename, edit the flag blocks at the top of each script. Keep dry and upscale **paired** (same name prefix) so texture/strength stay consistent.

```bash
cp presets/grit_dry.sh presets/mylook_dry.sh
cp presets/grit_upscale.sh presets/mylook_upscale.sh
# edit MYLOOK flags in both files
chmod +x presets/mylook_*.sh
```

Or drop a small `presets/local/` directory (gitignored if you want) for private experiments.

## Notes

- Presets call `uv run up.py` from the tilagup repo root.
- Upscale needs `FASTSDCPU_ROOT` set (your fish universal is fine).
- Dry-run does **not** apply texture packs; grit/smooth apply only on upscale (by design).
