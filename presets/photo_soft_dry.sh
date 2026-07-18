#!/usr/bin/env bash
# PRESET: photo_soft — best-effort *preserve the photograph*
# Dry-run: lower variation so tile agents invent less.
# Partner upscale: low strength, no texture pack (stock SD strings only).
#
# Goal: keep layout/identity of a real photo (crowds, water, stage) instead of
# rewriting into generic AI festival people + cartoon surf.
#
# usage: ./presets/photo_soft_dry.sh /path/to/image.png
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_lib.sh"
require_image "$@"

echo_banner "preset: photo_soft  |  DRY-RUN"
echo "image: $1"
echo "intent: preserve photo — low agent invention"
echo "flags: --agent both --variation 0.20 --dry-run"
echo ""
echo "Next: ./presets/photo_soft_upscale.sh"
echo ""

tilagup_run "$1" \
  --agent both \
  --variation 0.20 \
  --dry-run
