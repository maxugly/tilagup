#!/usr/bin/env bash
# PRESET: cartoon_ink — busy illustration / Waldo-style / flat comic art
# Dry-run: moderate-high variation so tiles can name tiny local characters & props.
# Partner upscale uses illustration-friendly negatives (does NOT ban cartoon/drawing).
#
# usage: ./presets/cartoon_ink_dry.sh /path/to/image.png
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"
require_image "$@"

echo_banner "preset: cartoon_ink  |  DRY-RUN"
echo "image: $1"
echo "intent: busy illustration / ink / flat color crowds"
echo "flags: --agent both --variation 0.40 --dry-run"
echo ""
echo "Next: ./presets/cartoon_ink_upscale.sh"
echo ""

tilagup_run "$1" \
  --agent both \
  --variation 0.40 \
  --dry-run
