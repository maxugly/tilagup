#!/usr/bin/env bash
# PRESET: grit_hot — grit pack + higher denoise (more invention)
# usage: ./presets/grit_hot_upscale.sh [run_dir]
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"

RUN="$(resolve_run_dir "${1:-}")"
echo_banner "preset: grit_hot  |  UPSCALE"
echo "run: $RUN"
echo "flags: --continue-upscale --strength 0.40 --texture grit --texture-strength 1.0"
echo ""

tilagup_run --resume "$RUN" \
  --continue-upscale \
  --strength 0.40 \
  --texture grit \
  --texture-strength 1.0
