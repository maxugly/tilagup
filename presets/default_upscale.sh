#!/usr/bin/env bash
# PRESET: default — stock upscale (strength 0.28, texture none)
# usage: ./presets/default_upscale.sh [run_dir]
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"

RUN="$(resolve_run_dir "${1:-}")"
echo_banner "preset: default  |  UPSCALE"
echo "run: $RUN"
echo "flags: --continue-upscale --strength 0.28 --texture none"
echo ""

tilagup_run --resume "$RUN" \
  --continue-upscale \
  --strength 0.28 \
  --texture none
