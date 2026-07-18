#!/usr/bin/env bash
# PRESET: default — stock tilagup dry-run (no texture pack)
# usage: ./presets/default_dry.sh /path/to/image.png
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"
require_image "$@"

echo_banner "preset: default  |  DRY-RUN"
echo "image: $1"
echo "flags: --agent both --variation 0.35 --dry-run"
echo ""

tilagup_run "$1" \
  --agent both \
  --variation 0.35 \
  --dry-run

echo ""
echo "Next: ./presets/default_upscale.sh"
echo "  (or: ./presets/default_upscale.sh runs/<image_key>/<run_id>)"
