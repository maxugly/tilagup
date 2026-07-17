"""Adapter for the `grok` CLI."""

from __future__ import annotations

from tilagup.agents.base import AgentResult, run_argv, which


class GrokAgent:
    name = "grok"
    cli = "grok"

    def __init__(self, *, extra_args: list[str] | None = None, model: str | None = None):
        self.extra_args = list(extra_args or [])
        self.model = model

    def available(self) -> bool:
        return which(self.cli) is not None

    def complete(self, user_prompt: str, *, timeout_s: float = 300.0) -> AgentResult:
        # --yolo auto-approves tools so vision/read can open the image path
        argv = [self.cli, "-p", user_prompt, "--yolo"]
        if self.model:
            argv.extend(["-m", self.model])
        argv.extend(self.extra_args)
        try:
            return run_argv(
                argv,
                agent=self.name,
                cli=self.cli,
                model=self.model,
                timeout_s=timeout_s,
            )
        except Exception as first:
            try:
                return run_argv(
                    argv,
                    agent=self.name,
                    cli=self.cli,
                    model=self.model,
                    timeout_s=timeout_s,
                )
            except Exception as second:
                raise RuntimeError(
                    f"grok failed after retry. first={first!s}; second={second!s}"
                ) from second
