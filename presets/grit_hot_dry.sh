#!/usr/bin/env bash
# PRESET: grit_hot — dry-run (same prompts as grit; hotter denoise on upscale)
# usage: ./presets/grit_hot_dry.sh /path/to/image.png
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"
require_image "$@"

echo_banner "preset: grit_hot  |  DRY-RUN"
echo "image: $1"
echo "flags: --agent both --variation 0.40 --dry-run"
echo "(hot strength is applied in grit_hot_upscale.sh)"
echo ""

tilagup_run "$1" \
  --agent both \
  --variation 0.40 \
  --dry-run

echo ""
echo "Next: ./presets/grit_hot_upscale.sh"
