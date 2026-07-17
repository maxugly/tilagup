"""Assign agents to base prompt + tiles."""

from __future__ import annotations

from tilagup.agents.agy_agent import AgyAgent
from tilagup.agents.base import VisionAgent
from tilagup.agents.grok_agent import GrokAgent


def build_agents(
    mode: str,
    *,
    agy_model: str | None = None,
    grok_model: str | None = None,
) -> list[VisionAgent]:
    mode = (mode or "both").lower()
    agents: list[VisionAgent] = []
    if mode in ("agy", "both"):
        agents.append(AgyAgent(model=agy_model))
    if mode in ("grok", "both"):
        agents.append(GrokAgent(model=grok_model))
    if mode not in ("agy", "grok", "both"):
        raise ValueError(f"unknown agent mode: {mode}")
    missing = [a.name for a in agents if not a.available()]
    if missing:
        raise RuntimeError(
            f"agent CLI not on PATH: {', '.join(missing)}. "
            "Install/link `agy` and/or `grok`, or pass --agent for whichever exists."
        )
    if not agents:
        raise RuntimeError("no agents configured")
    return agents


def pick_for_index(agents: list[VisionAgent], index: int) -> VisionAgent:
    return agents[index % len(agents)]
