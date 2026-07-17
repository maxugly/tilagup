from tilagup.clip_fit import fit_clip_prompt, token_len


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
