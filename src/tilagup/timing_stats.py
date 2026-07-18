"""Persistent timing samples + robust ETA priors.

Rules:
- Only **complete** runs feed aggregates (full dry-run or full upscale).
- **Stub** agent runs never poison live-agent ETAs.
- **Skipped** stages ignored.
- **Outliers** rejected (IQR); first-tile compile blips dropped for upscale.
- Aggregates prefer **median** over mean.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path
from typing import Any


# Seeded from real both-agent runs (2026-07-18); refined as history grows.
# Stub/pytest noise is excluded from aggregates.
DEFAULT_PRIORS: dict[str, float] = {
    "init": 0.05,
    "base_prompt": 7.5,  # ~7–8s live agent
    "split": 0.1,
    "tile_prompts_per_tile": 8.0,  # ~7–10s per tile live
    "upscale_per_tile": 95.0,  # ~75–120s per tile after model warm; first tile often compile+run
    "zone_discovery": 20.0,
    "zone_prompts_per_zone": 12.0,
}

STAGE_ORDER = (
    "init",
    "base_prompt",
    "split",
    "tile_prompts",
    "upscale",
)

# Live agents that produce real timing; stub/tests excluded from history aggregates
LIVE_AGENTS = frozenset({"agy", "grok", "both"})


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
        return {"version": 2, "samples": [], "aggregates": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 2, "samples": [], "aggregates": {}}
    # Recompute aggregates on load so rule changes apply to old files
    samples = data.get("samples") or []
    data["aggregates"] = recompute_aggregates(samples)
    data["version"] = 2
    return data


def save_history(data: dict[str, Any]) -> None:
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def reject_outliers(vals: list[float]) -> list[float]:
    """Drop statistical outliers. Small-n: median fence; n>=6: IQR 1.5."""
    clean = sorted(float(v) for v in vals if v is not None and v > 0)
    if len(clean) < 3:
        return clean
    med = statistics.median(clean)
    if med <= 0:
        return clean

    # Always apply a hard median fence first (catches 1000 vs ~8 with n=5)
    hard = [v for v in clean if med / 4 <= v <= med * 4]
    if len(hard) >= 2:
        clean = hard
    else:
        return clean

    if len(clean) < 6:
        return clean

    q1 = statistics.quantiles(clean, n=4)[0]
    q3 = statistics.quantiles(clean, n=4)[2]
    iqr = q3 - q1
    if iqr <= 0:
        return [v for v in clean if abs(v - med) <= max(med * 0.5, 0.01)] or clean
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    filtered = [v for v in clean if lo <= v <= hi]
    return filtered if filtered else clean


def clean_unit_samples(samples: list[float], *, stage: str) -> list[float]:
    """Drop compile blips / insane unit times before per_unit aggregation."""
    vals = [float(s) for s in samples if s is not None and s > 0.05]
    if not vals:
        return []
    # Upscale: first sample is often pipeline compile (~5–10s) then real tiles (~70–150s)
    if stage == "upscale" and len(vals) >= 2:
        med = statistics.median(vals[1:])  # median of rest
        if med > 20 and vals[0] < med * 0.25:
            vals = vals[1:]
    return reject_outliers(vals)


def sample_is_complete(sample: dict[str, Any]) -> bool:
    """True only if the intended work fully finished."""
    if sample.get("complete") is False:
        return False
    if sample.get("complete") is True:
        return True

    stages = sample.get("stages") or {}
    if sample.get("dry_run", True):
        tp = stages.get("tile_prompts") or {}
        if tp.get("status") != "done":
            return False
        n = int(tp.get("n_units") or 0)
        done = int(tp.get("units_done") or 0)
        if n > 0 and done < n:
            return False
        # must have actually run prompts (not zero-time skip of empty)
        sec = tp.get("seconds")
        if sec is not None and float(sec) < 0.001 and n > 0 and done == 0:
            return False
        return True

    # full upscale run
    up = stages.get("upscale") or {}
    if up.get("status") != "done":
        return False
    n = int(up.get("n_units") or 0)
    done = int(up.get("units_done") or 0)
    if n > 0 and done < n:
        return False
    return True


def sample_is_live_agent(sample: dict[str, Any]) -> bool:
    agent = (sample.get("agent") or "").lower()
    return agent in LIVE_AGENTS


def _robust_center(vals: list[float]) -> float | None:
    vals = reject_outliers(vals)
    if not vals:
        return None
    return float(statistics.median(vals))


def recompute_aggregates(samples: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[float]] = {}

    for s in samples:
        if not sample_is_complete(s):
            continue
        if not sample_is_live_agent(s):
            continue

        stages = s.get("stages") or {}
        for name, info in stages.items():
            if not isinstance(info, dict):
                continue
            status = info.get("status")
            if status in ("skipped", "pending", "failed"):
                continue
            if status != "done":
                continue

            if name in ("tile_prompts", "upscale"):
                n = int(info.get("n_units") or 0)
                done = int(info.get("units_done") or 0)
                if n > 0 and done < n:
                    continue  # incomplete stage
                unit_samples = info.get("unit_samples") or []
                cleaned = clean_unit_samples(unit_samples, stage=name)
                if cleaned:
                    per = statistics.median(cleaned)
                elif info.get("per_unit_s") and n > 0 and done >= n:
                    # fall back to recorded per_unit only if fully done
                    per = float(info["per_unit_s"])
                    # reject obvious compile-skewed averages (first tile blip baked in)
                    if name == "upscale" and per < 20:
                        continue
                elif info.get("seconds") and n > 0 and done >= n:
                    per = float(info["seconds"]) / n
                else:
                    continue
                key = (
                    "tile_prompts_per_tile"
                    if name == "tile_prompts"
                    else "upscale_per_tile"
                )
                if per > 0.05:
                    buckets.setdefault(key, []).append(per)
                continue

            if name in ("init", "base_prompt", "split"):
                sec = info.get("seconds")
                if sec is None:
                    continue
                sec = float(sec)
                # ignore near-zero skips that were mis-marked done
                if sec < 0.001:
                    continue
                # base_prompt under 0.5s is almost certainly stub/skip noise
                if name == "base_prompt" and sec < 0.5:
                    continue
                buckets.setdefault(name, []).append(sec)

    out: dict[str, Any] = {}
    for key, vals in buckets.items():
        cleaned = reject_outliers(vals)
        if not cleaned:
            continue
        out[key] = {
            "mean_s": statistics.fmean(cleaned),
            "median_s": statistics.median(cleaned),
            "count": len(cleaned),
            "raw_count": len(vals),
            "min_s": min(cleaned),
            "max_s": max(cleaned),
            "outliers_dropped": len(vals) - len(cleaned),
        }
    return out


def _agg_center(history: dict[str, Any], key: str) -> float | None:
    a = (history.get("aggregates") or {}).get(key) or {}
    if a.get("count", 0) <= 0:
        return None
    # prefer median
    if a.get("median_s") is not None:
        return float(a["median_s"])
    if a.get("mean_s") is not None:
        return float(a["mean_s"])
    return None


def estimate_seconds(
    history: dict[str, Any],
    key: str,
    *,
    n_units: int = 1,
    run_unit_samples: list[float] | None = None,
) -> float:
    """Best estimate: this-run robust units → history median → prior."""
    stage_hint = "upscale" if "upscale" in key else "tile_prompts" if "tile" in key else key

    if run_unit_samples:
        cleaned = clean_unit_samples(run_unit_samples, stage=stage_hint)
        if cleaned:
            per = statistics.median(cleaned)
            return max(0.1, per * max(n_units, 1))

    # normalize stage keys to aggregate keys
    agg_key = key
    if key == "tile_prompts":
        agg_key = "tile_prompts_per_tile"
    elif key == "upscale":
        agg_key = "upscale_per_tile"

    center = _agg_center(history, agg_key)
    if center is not None:
        if agg_key.endswith("_per_tile") or agg_key.endswith("_per_zone"):
            return max(0.1, center * max(n_units, 1))
        return max(0.1, center)

    # also try raw key
    center = _agg_center(history, key)
    if center is not None:
        return max(0.1, center * (n_units if "per_" in key else 1))

    prior_key = key
    if key == "tile_prompts":
        prior_key = "tile_prompts_per_tile"
        return max(0.1, DEFAULT_PRIORS[prior_key] * max(n_units, 1))
    if key == "upscale":
        prior_key = "upscale_per_tile"
        return max(0.1, DEFAULT_PRIORS[prior_key] * max(n_units, 1))

    return max(
        0.1,
        DEFAULT_PRIORS.get(prior_key, 10.0) * (n_units if "per_" in prior_key else 1),
    )


def mark_sample_complete(sample: dict[str, Any]) -> dict[str, Any]:
    """Annotate complete flag from stage statuses."""
    sample = dict(sample)
    sample["complete"] = sample_is_complete(sample)
    return sample


def record_sample(sample: dict[str, Any]) -> None:
    """Append a run sample; only complete live-agent runs affect aggregates."""
    sample = mark_sample_complete(sample)
    hist = load_history()
    samples = hist.setdefault("samples", [])
    samples.append(sample)
    if len(samples) > 200:
        hist["samples"] = samples[-200:]
    hist["aggregates"] = recompute_aggregates(hist["samples"])
    hist["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    hist["version"] = 2
    # also store which samples were used (debug aid)
    hist["aggregate_rules"] = {
        "complete_only": True,
        "live_agents_only": sorted(LIVE_AGENTS),
        "outlier_method": "IQR_1.5",
        "upscale_drop_first_if_compile_blip": True,
        "stat": "median",
    }
    save_history(hist)


def rebuild_history_file() -> dict[str, Any]:
    """Re-filter existing history in place (e.g. after rule changes)."""
    hist = load_history()
    hist["aggregates"] = recompute_aggregates(hist.get("samples") or [])
    hist["version"] = 2
    hist["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_history(hist)
    return hist


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
