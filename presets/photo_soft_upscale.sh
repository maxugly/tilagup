#!/usr/bin/env bash
# PRESET: photo_soft — low denoise, no grit; maximize photo fidelity on this stack
#
# strength 0.18 = refine more than rewrite (sd-turbo still has limits).
# texture none  = do not push film-grain packs that fight photoreal crowds.
#
# usage: ./presets/photo_soft_upscale.sh [run_dir]
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"

RUN="$(resolve_run_dir "${1:-}")"
echo_banner "preset: photo_soft  |  UPSCALE"
echo "run: $RUN"
echo "intent: preserve photo — low denoise, no texture pack"
echo "flags: --continue-upscale --strength 0.18 --texture none"
echo ""

tilagup_run --resume "$RUN" \
  --continue-upscale \
  --strength 0.18 \
  --texture none
