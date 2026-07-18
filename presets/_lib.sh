#!/usr/bin/env bash
# Shared helpers for tilagup preset scripts.
set -euo pipefail

# Repo root = parent of presets/
_PRESET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TILAGUP_ROOT="$(cd "${_PRESET_DIR}/.." && pwd)"

tilagup_run() {
  cd "$TILAGUP_ROOT"
  if command -v uv >/dev/null 2>&1; then
    uv run up.py "$@"
  else
    # fallback if uv missing but venv exists
    if [[ -x "$TILAGUP_ROOT/.venv/bin/python" ]]; then
      "$TILAGUP_ROOT/.venv/bin/python" "$TILAGUP_ROOT/up.py" "$@"
    else
      echo "error: need uv or $TILAGUP_ROOT/.venv" >&2
      exit 1
    fi
  fi
}

# Newest runs/<image_key>/<run_id> that contains run.json
latest_run_dir() {
  local newest=""
  local newest_m=0
  local d m
  shopt -s nullglob
  for d in "$TILAGUP_ROOT"/runs/*/*; do
    [[ -f "$d/run.json" ]] || continue
    m=$(stat -c %Y "$d" 2>/dev/null || stat -f %m "$d" 2>/dev/null || echo 0)
    if (( m >= newest_m )); then
      newest_m=$m
      newest=$d
    fi
  done
  shopt -u nullglob
  if [[ -z "$newest" ]]; then
    echo "error: no runs found under $TILAGUP_ROOT/runs" >&2
    exit 1
  fi
  echo "$newest"
}

resolve_run_dir() {
  # arg optional: explicit path or empty → latest
  local arg="${1:-}"
  if [[ -z "$arg" ]]; then
    latest_run_dir
    return
  fi
  if [[ -f "$arg/run.json" ]]; then
    echo "$(cd "$arg" && pwd)"
    return
  fi
  if [[ -f "$arg" && "$(basename "$arg")" == "run.json" ]]; then
    echo "$(cd "$(dirname "$arg")" && pwd)"
    return
  fi
  # relative to repo
  if [[ -f "$TILAGUP_ROOT/$arg/run.json" ]]; then
    echo "$(cd "$TILAGUP_ROOT/$arg" && pwd)"
    return
  fi
  echo "error: not a run dir: $arg" >&2
  exit 1
}

require_image() {
  if [[ $# -lt 1 ]]; then
    echo "usage: $0 /path/to/image.png" >&2
    exit 2
  fi
  if [[ ! -f "$1" ]]; then
    echo "error: image not found: $1" >&2
    exit 2
  fi
}

echo_banner() {
  echo ""
  echo "════════════════════════════════════════"
  echo "  $*"
  echo "════════════════════════════════════════"
}
