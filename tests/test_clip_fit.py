from tilagup.clip_fit import fit_clip_prompt, fit_tile_prompt, strip_restated_base, token_len


def test_short_prompt_unchanged():
    s = "cracked mud face, neon blue contour lines, fire, dark background"
    out, cut = fit_clip_prompt(s, max_tokens=75)
    assert out == s
    assert cut is False


def test_long_prompt_truncated():
    s = " ".join(["detailed organic cybernetic peat skull texture"] * 40)
    out, cut = fit_clip_prompt(s, max_tokens=75)
    assert cut is True
    assert token_len(out) <= 75
    assert len(out) < len(s)


def test_strip_restated_base_keeps_tail():
    base = "surreal mud face neon blue fire dark cybernetic portrait"
    tile = (
        base
        + " "
        + "and in this crop frayed copper root-cables with opal crustacean shells"
    )
    unique = strip_restated_base(tile, base)
    assert "opal" in unique
    assert "frayed" in unique


def test_fit_tile_unique_first():
    base = " ".join(["global scene description mud face neon fire wires"] * 5)
    unique = "frayed copper root-cables, opal crustacean shells, micro Mandelbrot mycelium"
    tile = base + " " + unique
    out, changed = fit_tile_prompt(tile, base, max_tokens=75)
    assert token_len(out) <= 75
    # unique detail must survive
    assert "opal" in out or "frayed" in out or "mycelium" in out
