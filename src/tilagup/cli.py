"""CLI: uv run up.py IMAGE [options] | uv run tilagup …"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tilagup import __version__, log
from tilagup.pipeline import run_pipeline
from tilagup.prompts_lib import DEFAULT_NEGATIVE


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tilagup",
        description=(
            "Tiled agent upscale — base + per-tile vision prompts, FastSD blend, "
            "full archives. Loud by default; use --quiet if you hate joy."
        ),
    )
    p.add_argument(
        "image",
        nargs="?",
        type=Path,
        help="Input image (png/jpg/tiff/…). Omit with --resume.",
    )
    p.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Resume an existing run dir (runs/<image_key>/<run_id>/ or path to run.json).",
    )
    p.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("runs"),
        help="Root for archives: runs/<image_key>/<run_id>/ (default: ./runs).",
    )
    p.add_argument(
        "--agent",
        choices=("agy", "grok", "both", "stub"),
        default="both",
        help="Vision agent(s). 'both' alternates tiles; 'stub' is offline/CI. Default: both.",
    )
    p.add_argument(
        "--variation",
        type=float,
        default=0.35,
        help="0..1 how far tile prompts may drift from base (default 0.35).",
    )
    p.add_argument(
        "--strength",
        type=float,
        default=0.28,
        help="SD img2img strength for tiled upscale (default 0.28).",
    )
    p.add_argument(
        "--scale",
        type=float,
        default=2.0,
        help="Upscale scale factor (default 2.0).",
    )
    p.add_argument("--tile-size", type=int, default=256, help="Tile stride size (default 256).")
    p.add_argument("--overlap", type=int, default=32, help="Tile overlap pixels (default 32).")
    p.add_argument(
        "--negative-prompt",
        type=str,
        default=DEFAULT_NEGATIVE,
        help="Negative prompt for SD upscale.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Split + write all prompts; do not run SD upscale.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-run stages even if outputs exist.",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Per-agent-call timeout seconds (default 300).",
    )
    p.add_argument(
        "--agy-model",
        type=str,
        default=None,
        help="Optional model id passed to `agy --model`.",
    )
    p.add_argument(
        "--grok-model",
        type=str,
        default=None,
        help="Optional model id passed to `grok -m`.",
    )
    p.add_argument(
        "--continue-upscale",
        action="store_true",
        help="On --resume after dry-run, clear dry_run and run FastSD upscale.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Silence progress spam (default is loud — you asked for this).",
    )
    p.add_argument("--version", action="version", version=f"tilagup {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    log.set_quiet(args.quiet)

    if not args.resume and not args.image:
        build_parser().error("image path required unless --resume")
    if args.image and not args.image.is_file():
        log.always(f"error: image not found: {args.image}", err=True)
        return 2
    if not (0.0 <= args.variation <= 1.0):
        log.always("error: --variation must be in [0, 1]", err=True)
        return 2

    config = {
        "agent": args.agent,
        "variation": args.variation,
        "strength": args.strength,
        "scale": args.scale,
        "tile_size": args.tile_size,
        "overlap": args.overlap,
        "negative_prompt": args.negative_prompt,
        "dry_run": args.dry_run,
        "agy_model": args.agy_model,
        "grok_model": args.grok_model,
    }

    dry = args.dry_run
    if args.continue_upscale:
        dry = False
        config["dry_run"] = False

    try:
        arch = run_pipeline(
            image=args.image,
            resume=args.resume,
            runs_dir=args.runs_dir,
            config=config,
            dry_run=dry,
            force=args.force,
            timeout_s=args.timeout,
        )
    except KeyboardInterrupt:
        log.always("\ninterrupted — run dir preserved for --resume", err=True)
        return 130
    except Exception as e:
        log.always(f"error: {e}", err=True)
        return 1

    data = arch.load()
    log.always("")
    log.always(f"run_id:     {data['run_id']}")
    if data.get("image_key"):
        log.always(f"image_key:  {data['image_key']}")
    log.always(f"path:       {arch.root}")
    log.always(f"stage:      {data.get('stage')}")
    bp = (data.get("base_prompt") or {}).get("text")
    if bp:
        who = ((data.get("base_prompt") or {}).get("attribution") or {}).get("agent")
        log.always(f"base:       {len(bp)} chars (agent={who})")
    log.always(f"tiles:      {len(data.get('tiles') or [])}")
    log.always(f"agents:     {', '.join(data.get('agents_used') or [])}")
    if data.get("output"):
        log.always(f"output:     {arch.root / data['output']}")
    log.always(f"json:       {arch.run_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
