from tilagup.timing_stats import estimate_seconds, fmt_duration, recompute_aggregates


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


def test_recompute_aggregates():
    samples = [
        {
            "stages": {
                "base_prompt": {"seconds": 10.0},
                "tile_prompts": {"seconds": 100.0, "n_units": 10, "per_unit_s": 10.0},
            }
        },
        {
            "stages": {
                "base_prompt": {"seconds": 20.0},
                "tile_prompts": {"seconds": 80.0, "n_units": 10, "per_unit_s": 8.0},
            }
        },
    ]
    agg = recompute_aggregates(samples)
    assert agg["base_prompt"]["count"] == 2
    assert agg["tile_prompts_per_tile"]["mean_s"] == 9.0
