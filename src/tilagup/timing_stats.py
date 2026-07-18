"""Persistent timing samples + priors for ETA.

Every stage/unit duration is recorded so we can tune estimates later from real data.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path
from typing import Any


# Absolute priors (seconds) when no history exists yet — rough guesses
DEFAULT_PRIORS: dict[str, float] = {
    "init": 0.4,
    "base_prompt": 18.0,  # one vision agent call
    "split": 1.5,
    "tile_prompts_per_tile": 12.0,  # one agent call per tile
    "upscale_per_tile": 50.0,  # SD tile on CPU/iGPU — slow
    "zone_discovery": 20.0,  # future
    "zone_prompts_per_zone": 12.0,  # future
}

# Relative weights among stages (used only to scale priors together)
# tile-heavy stages scale with n_tiles outside this table
STAGE_ORDER = (
    "init",
    "base_prompt",
    "split",
    "tile_prompts",
    "upscale",
)


def history_path() -> Path:
    env = os.environ.get("TILAGUP_TIMING_PATH")
    if env:
        return Path(env).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        base = Path(xdg) / "tilagup"
    else:
        base = Path.home() / ".local" / "share" / "tilagup"
    base.mkdir(parents=True, exist_ok=True)
    return base / "timing_history.json"


def load_history() -> dict[str, Any]:
    path = history_path()
    if not path.is_file():
        return {"version": 1, "samples": [], "aggregates": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "samples": [], "aggregates": {}}


def save_history(data: dict[str, Any]) -> None:
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _agg_mean(history: dict[str, Any], key: str) -> float | None:
    a = (history.get("aggregates") or {}).get(key) or {}
    if a.get("count", 0) > 0 and a.get("mean_s") is not None:
        return float(a["mean_s"])
    return None


def estimate_seconds(
    history: dict[str, Any],
    key: str,
    *,
    n_units: int = 1,
    run_unit_samples: list[float] | None = None,
) -> float:
    """Best estimate for a stage or per-unit × n_units.

    Preference: this-run unit samples → history mean → prior.
    """
    if run_unit_samples:
        # robust: median of this run so far
        try:
            per = statistics.median(run_unit_samples)
            return max(0.1, per * n_units)
        except statistics.StatisticsError:
            pass

    mean = _agg_mean(history, key)
    if mean is not None:
        if key.endswith("_per_tile") or key.endswith("_per_zone"):
            return max(0.1, mean * n_units)
        return max(0.1, mean)

    prior_key = key
    if key == "tile_prompts":
        prior_key = "tile_prompts_per_tile"
        return max(0.1, DEFAULT_PRIORS[prior_key] * n_units)
    if key == "upscale":
        prior_key = "upscale_per_tile"
        return max(0.1, DEFAULT_PRIORS[prior_key] * n_units)

    return max(0.1, DEFAULT_PRIORS.get(prior_key, 10.0) * (n_units if "per_" in prior_key else 1))


def record_sample(sample: dict[str, Any]) -> None:
    """Append one finished run sample and refresh aggregates."""
    hist = load_history()
    samples = hist.setdefault("samples", [])
    samples.append(sample)
    # keep last 200 runs
    if len(samples) > 200:
        hist["samples"] = samples[-200:]
    hist["aggregates"] = recompute_aggregates(hist["samples"])
    hist["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_history(hist)


def recompute_aggregates(samples: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[float]] = {}
    for s in samples:
        stages = s.get("stages") or {}
        for name, info in stages.items():
            if not isinstance(info, dict):
                continue
            if info.get("per_unit_s") is not None and info.get("n_units"):
                key = f"{name}_per_tile" if name in ("tile_prompts", "upscale") else f"{name}_per_unit"
                # store per-unit into named keys we query
                if name == "tile_prompts":
                    key = "tile_prompts_per_tile"
                elif name == "upscale":
                    key = "upscale_per_tile"
                buckets.setdefault(key, []).append(float(info["per_unit_s"]))
            if info.get("seconds") is not None and name in ("init", "base_prompt", "split"):
                buckets.setdefault(name, []).append(float(info["seconds"]))

    out: dict[str, Any] = {}
    for key, vals in buckets.items():
        if not vals:
            continue
        out[key] = {
            "mean_s": statistics.fmean(vals),
            "median_s": statistics.median(vals),
            "count": len(vals),
            "min_s": min(vals),
            "max_s": max(vals),
        }
    return out


def fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"
