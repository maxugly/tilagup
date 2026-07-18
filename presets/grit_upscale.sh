#!/usr/bin/env bash
# PRESET: grit — upscale with film-grain / raw-texture pack
# usage: ./presets/grit_upscale.sh [run_dir]
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"

RUN="$(resolve_run_dir "${1:-}")"
echo_banner "preset: grit  |  UPSCALE"
echo "run: $RUN"
echo "flags: --continue-upscale --strength 0.28 --texture grit --texture-strength 1.0"
echo ""

tilagup_run --resume "$RUN" \
  --continue-upscale \
  --strength 0.28 \
  --texture grit \
  --texture-strength 1.0
