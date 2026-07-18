from tilagup.timing_stats import (
    clean_unit_samples,
    estimate_seconds,
    fmt_duration,
    recompute_aggregates,
    reject_outliers,
    sample_is_complete,
)


def test_fmt_duration():
    assert fmt_duration(5) == "5s"
    assert "m" in fmt_duration(65)


def test_estimate_uses_run_samples():
    hist = {"aggregates": {}, "samples": []}
    est = estimate_seconds(
        hist,
        "tile_prompts",
        n_units=10,
        run_unit_samples=[2.0, 2.0, 2.0],
    )
    assert 19.0 <= est <= 21.0


def test_reject_outliers():
    vals = [8.0, 9.0, 8.5, 9.2, 1000.0]
    cleaned = reject_outliers(vals)
    assert 1000.0 not in cleaned
    assert len(cleaned) >= 3


def test_clean_upscale_drops_compile_blip():
    # first ~7s compile, then real ~80s tiles
    samples = [7.0, 80.0, 78.0, 82.0, 79.0]
    cleaned = clean_unit_samples(samples, stage="upscale")
    assert 7.0 not in cleaned
    assert min(cleaned) > 50


def test_incomplete_upscale_not_complete():
    s = {
        "dry_run": False,
        "agent": "both",
        "stages": {
            "upscale": {
                "status": "done",
                "n_units": 4,
                "units_done": 2,
                "seconds": 85,
                "per_unit_s": 40,
            }
        },
    }
    assert sample_is_complete(s) is False


def test_complete_dry_run():
    s = {
        "dry_run": True,
        "agent": "both",
        "stages": {
            "tile_prompts": {
                "status": "done",
                "n_units": 4,
                "units_done": 4,
                "seconds": 30,
                "per_unit_s": 7.5,
            }
        },
    }
    assert sample_is_complete(s) is True


def test_stub_excluded_from_aggregates():
    samples = [
        {
            "dry_run": True,
            "agent": "stub",
            "complete": True,
            "stages": {
                "base_prompt": {"status": "done", "seconds": 0.01},
                "tile_prompts": {
                    "status": "done",
                    "n_units": 4,
                    "units_done": 4,
                    "seconds": 0.1,
                    "per_unit_s": 0.025,
                    "unit_samples": [0.02, 0.03],
                },
            },
        },
        {
            "dry_run": True,
            "agent": "both",
            "complete": True,
            "stages": {
                "base_prompt": {"status": "done", "seconds": 7.5},
                "tile_prompts": {
                    "status": "done",
                    "n_units": 4,
                    "units_done": 4,
                    "seconds": 32,
                    "per_unit_s": 8.0,
                    "unit_samples": [7.0, 8.0, 9.0, 8.5],
                },
            },
        },
    ]
    agg = recompute_aggregates(samples)
    assert "tile_prompts_per_tile" in agg
    # only the live run
    assert agg["tile_prompts_per_tile"]["count"] == 1
    assert 7.0 <= agg["tile_prompts_per_tile"]["median_s"] <= 9.0
    assert agg["base_prompt"]["median_s"] >= 7.0


def test_recompute_aggregates():
    samples = [
        {
            "agent": "both",
            "dry_run": True,
            "stages": {
                "base_prompt": {"status": "done", "seconds": 10.0},
                "tile_prompts": {
                    "status": "done",
                    "seconds": 100.0,
                    "n_units": 10,
                    "units_done": 10,
                    "per_unit_s": 10.0,
                    "unit_samples": [10.0] * 10,
                },
            },
        },
        {
            "agent": "both",
            "dry_run": True,
            "stages": {
                "base_prompt": {"status": "done", "seconds": 20.0},
                "tile_prompts": {
                    "status": "done",
                    "seconds": 80.0,
                    "n_units": 10,
                    "units_done": 10,
                    "per_unit_s": 8.0,
                    "unit_samples": [8.0] * 10,
                },
            },
        },
    ]
    agg = recompute_aggregates(samples)
    assert agg["base_prompt"]["count"] == 2
    assert agg["tile_prompts_per_tile"]["count"] == 2
