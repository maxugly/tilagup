"""Assign agents to base prompt + tiles."""

from __future__ import annotations

from tilagup.agents.agy_agent import AgyAgent
from tilagup.agents.base import VisionAgent
from tilagup.agents.grok_agent import GrokAgent
from tilagup.agents.stub_agent import StubAgent

VALID_MODES = frozenset({"agy", "grok", "both", "stub"})


def build_agents(
    mode: str,
    *,
    agy_model: str | None = None,
    grok_model: str | None = None,
) -> list[VisionAgent]:
    mode = (mode or "both").lower()
    if mode not in VALID_MODES:
        raise ValueError(f"unknown agent mode: {mode} (expected {sorted(VALID_MODES)})")

    agents: list[VisionAgent] = []
    if mode == "stub":
        agents.append(StubAgent())
        return agents

    if mode in ("agy", "both"):
        agents.append(AgyAgent(model=agy_model))
    if mode in ("grok", "both"):
        agents.append(GrokAgent(model=grok_model))

    missing = [a.name for a in agents if not a.available()]
    if missing:
        raise RuntimeError(
            f"agent CLI not on PATH: {', '.join(missing)}. "
            "Install/link `agy` and/or `grok`, pass --agent for whichever exists, "
            "or use --agent stub for offline CI."
        )
    if not agents:
        raise RuntimeError("no agents configured")
    return agents


def pick_for_index(agents: list[VisionAgent], index: int) -> VisionAgent:
    return agents[index % len(agents)]
