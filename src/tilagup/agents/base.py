"""Shared agent protocol and response cleaning."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class AgentResult:
    text: str
    agent: str
    cli: str
    model: str | None
    duration_ms: int
    raw: str
    command: list[str]


class VisionAgent(Protocol):
    name: str
    cli: str

    def available(self) -> bool: ...

    def complete(self, user_prompt: str, *, timeout_s: float = 300.0) -> AgentResult: ...


_FENCE_RE = re.compile(r"^```(?:\w+)?\s*\n(.*?)\n```\s*$", re.DOTALL | re.MULTILINE)


def clean_prompt_text(raw: str) -> str:
    text = raw.strip()
    # drop common preambles
    for prefix in (
        "sure,",
        "sure!",
        "here is",
        "here's",
        "the prompt:",
        "prompt:",
        "final prompt:",
    ):
        low = text.lower()
        if low.startswith(prefix):
            text = text[len(prefix) :].lstrip(" \n:")
    m = _FENCE_RE.match(text)
    if m:
        text = m.group(1).strip()
    # if model wrapped mid-response fences, take largest line-block
    if "```" in text:
        parts = re.findall(r"```(?:\w+)?\s*\n(.*?)```", text, flags=re.DOTALL)
        if parts:
            text = max(parts, key=len).strip()
    # collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # strip wrapping quotes
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        text = text[1:-1].strip()
    return text


def run_argv(
    argv: list[str],
    *,
    agent: str,
    cli: str,
    model: str | None = None,
    timeout_s: float = 300.0,
) -> AgentResult:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"{cli} timed out after {timeout_s}s: {argv[:3]}…") from e
    duration_ms = int((time.perf_counter() - t0) * 1000)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if proc.returncode != 0:
        raise RuntimeError(
            f"{cli} exit {proc.returncode}: {stderr[-2000:] or stdout[-2000:]}"
        )
    raw = stdout.strip() or stderr.strip()
    text = clean_prompt_text(raw)
    if not text:
        raise RuntimeError(f"{cli} returned empty prompt text")
    return AgentResult(
        text=text,
        agent=agent,
        cli=cli,
        model=model,
        duration_ms=duration_ms,
        raw=raw,
        command=argv,
    )


def which(binary: str) -> str | None:
    return shutil.which(binary)


def image_hint_block(image_path: Path) -> str:
    """Absolute path block for agents that open files by path."""
    return str(image_path.resolve())
