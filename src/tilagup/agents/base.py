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
    """Run an agent CLI. Streams output + heartbeat so the TTY never looks dead."""
    from tilagup import log

    t0 = time.perf_counter()
    log.say(f">>> calling {cli} (agent={agent}) — live output below, heartbeat every 10s")
    log.say(f"    argv head: {' '.join(argv[:3])} …")
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as e:
        raise RuntimeError(f"{cli} not found on PATH") from e

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    assert proc.stdout is not None and proc.stderr is not None
    import select

    streams = [proc.stdout, proc.stderr]
    deadline = time.monotonic() + timeout_s
    last_beat = time.monotonic()
    last_activity = time.monotonic()
    try:
        while True:
            if proc.poll() is not None and not streams:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                proc.kill()
                raise TimeoutError(f"{cli} timed out after {timeout_s}s")

            now = time.monotonic()
            # Heartbeat: prove we are alive even when the agent is silent
            if now - last_beat >= 10.0:
                waited = int(now - t0)
                silent = int(now - last_activity)
                log.say(
                    f"… still waiting on {cli}  "
                    f"elapsed={waited}s  silent={silent}s  "
                    f"timeout_in={int(remaining)}s"
                )
                last_beat = now

            if not streams:
                # process may still be finishing
                if proc.poll() is not None:
                    break
                time.sleep(0.2)
                continue

            ready, _, _ = select.select(streams, [], [], min(1.0, remaining))
            if not ready:
                continue
            for s in ready:
                line = s.readline()
                if line == "":
                    streams = [x for x in streams if x is not s]
                    continue
                last_activity = time.monotonic()
                if s is proc.stdout:
                    stdout_chunks.append(line)
                    log.say(f"  [{cli}:out] {line.rstrip()}")
                else:
                    stderr_chunks.append(line)
                    log.say(f"  [{cli}:err] {line.rstrip()}")

        # drain leftovers
        for s, bucket, tag in (
            (proc.stdout, stdout_chunks, "out"),
            (proc.stderr, stderr_chunks, "err"),
        ):
            rest = s.read()
            if rest:
                bucket.append(rest)
                for line in rest.splitlines():
                    log.say(f"  [{cli}:{tag}] {line}")
        rc = proc.wait(timeout=max(1.0, deadline - time.monotonic()))
    except TimeoutError:
        proc.kill()
        raise

    duration_ms = int((time.perf_counter() - t0) * 1000)
    stdout = "".join(stdout_chunks)
    stderr = "".join(stderr_chunks)
    log.say(f"<<< {cli} finished exit={rc} in {duration_ms}ms")
    if rc != 0:
        raise RuntimeError(
            f"{cli} exit {rc}: {stderr[-2000:] or stdout[-2000:]}"
        )
    raw = stdout.strip() or stderr.strip()
    text = clean_prompt_text(raw)
    if not text:
        raise RuntimeError(f"{cli} returned empty prompt text")
    log.say(f"got prompt: {len(text)} chars from {agent}")
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
