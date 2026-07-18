#!/usr/bin/env bash
# PRESET: smooth — dry-run; polished texture pack on upscale partner
# usage: ./presets/smooth_dry.sh /path/to/image.png
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"
require_image "$@"

echo_banner "preset: smooth  |  DRY-RUN"
echo "image: $1"
echo "flags: --agent both --variation 0.35 --dry-run"
echo ""

tilagup_run "$1" \
  --agent both \
  --variation 0.35 \
  --dry-run

echo ""
echo "Next: ./presets/smooth_upscale.sh"
