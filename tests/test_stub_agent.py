from pathlib import Path

from PIL import Image

from tilagup.agents.stub_agent import StubAgent


def test_stub_base_prompt(tmp_path: Path):
    img = tmp_path / "full.png"
    Image.new("RGB", (64, 64), color=(200, 40, 40)).save(img)
    agent = StubAgent()
    r = agent.complete(f"Image path (open and inspect): {img}\n\nWrite base prompt.")
    assert r.agent == "stub"
    assert r.model == "stub-v1"
    assert "stub base prompt" in r.text
    assert "warm" in r.text or "rgb" in r.text


def test_stub_tile_prompt_includes_id(tmp_path: Path):
    crop = tmp_path / "r00_c01.png"
    Image.new("RGB", (32, 32), color=(20, 30, 180)).save(crop)
    agent = StubAgent()
    prompt = (
        "LOCKED — preserve style/subject):\n"
        "a peat skull with neon channels\n\n"
        f"This tile id=r00_c01 row=0 col=1.\n"
        f"Crop image path (open and inspect): {crop}\n"
    )
    r = agent.complete(prompt)
    assert "r00_c01" in r.text
    assert "stub detail" in r.text
