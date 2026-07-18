#!/usr/bin/env bash
# PRESET: cartoon_ink — preserve flat color / ink illustration while adding micro-chaos
#
# - strength 0.32: room for tiny characters/props without full photoreal rewrite
# - texture none: grit pack fights clean ink/flat color
# - negative: ban PHOTO looks, NOT cartoon/drawing/illustration
#
# usage: ./presets/cartoon_ink_upscale.sh [run_dir]
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"

RUN="$(resolve_run_dir "${1:-}")"

# Important: default tilagup negative includes "cartoon, drawing, illustration"
# which actively hurts Waldo / comic sources. Override for this preset.
CARTOON_NEG='photorealistic, photograph, realistic photo, 3d render, cgi, plastic, glossy skin, airbrushed, blurry, lowres, watermark, logo, text, deformed, mutation, ugly, muddy colors'

echo_banner "preset: cartoon_ink  |  UPSCALE"
echo "run: $RUN"
echo "intent: illustration-friendly denoise + negatives"
echo "flags: --continue-upscale --strength 0.32 --texture none"
echo "neg:   (photo/3d banned; cartoon/drawing allowed)"
echo ""

tilagup_run --resume "$RUN" \
  --continue-upscale \
  --strength 0.32 \
  --texture none \
  --negative-prompt "$CARTOON_NEG"
