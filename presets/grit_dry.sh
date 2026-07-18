#!/usr/bin/env bash
# PRESET: grit — dry-run (agents); grit applied only on upscale partner script
# usage: ./presets/grit_dry.sh /path/to/image.png
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"
require_image "$@"

echo_banner "preset: grit  |  DRY-RUN"
echo "image: $1"
echo "flags: --agent both --variation 0.35 --dry-run"
echo "(texture grit is applied in grit_upscale.sh)"
echo ""

tilagup_run "$1" \
  --agent both \
  --variation 0.35 \
  --dry-run

echo ""
echo "Next: ./presets/grit_upscale.sh"
