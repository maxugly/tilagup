from tilagup.agents.base import clean_prompt_text


def test_strips_fence():
    raw = '```\nA glowing peat skull with neon mycelium\n```'
    assert clean_prompt_text(raw) == "A glowing peat skull with neon mycelium"


def test_strips_preamble():
    raw = "Sure! Here's the prompt:\n\nweathered organic machine face"
    assert "weathered organic machine face" in clean_prompt_text(raw)
    assert not clean_prompt_text(raw).lower().startswith("sure")
