from tilagup.texture import apply_positive, merge_negative, normalize_mode, pack_for


def test_none_is_noop():
    p = pack_for("none", 1.0)
    assert p["positive"] == ""
    assert p["negative"] == ""


def test_grit_full():
    p = pack_for("grit", 1.0)
    assert "film grain" in p["positive"]
    assert "smooth" in p["negative"]


def test_grit_scaled():
    full = pack_for("grit", 1.0)["positive"].split(",")
    half = pack_for("grit", 0.5)["positive"].split(",")
    assert len(half) < len(full)
    assert len(half) >= 1


def test_merge_and_apply():
    assert apply_positive("mud face", "film grain") == "mud face, film grain"
    n = merge_negative("blurry, lowres", "smooth, plastic")
    assert "blurry" in n and "smooth" in n


def test_normalize():
    assert normalize_mode("off") == "none"
    assert normalize_mode("GRIT") == "grit"
