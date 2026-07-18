#!/usr/bin/env bash
# PRESET: stub_smoke — offline dry-run (no agy/grok); plumbing check
# usage: ./presets/stub_smoke_dry.sh /path/to/image.png
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"
require_image "$@"

echo_banner "preset: stub_smoke  |  DRY-RUN"
echo "image: $1"
echo "flags: --agent stub --variation 0.35 --dry-run"
echo ""

tilagup_run "$1" \
  --agent stub \
  --variation 0.35 \
  --dry-run

echo ""
echo "Next: ./presets/stub_smoke_upscale.sh  (needs FASTSDCPU_ROOT for real SD)"
