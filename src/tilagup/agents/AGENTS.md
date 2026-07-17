# AGENTS.md — src/tilagup/agents/

> *Vision CLI adapters. Who writes prompts.*

## Role

Adapters invoke headless agent CLIs, force **prompt-only** output, and return attribution metadata for `run.json`.

## Adapters

| Module | Binary | Invoke pattern |
|--------|--------|----------------|
| `agy_agent.py` | `agy` | `agy -p "<prompt>" --dangerously-skip-permissions` |
| `grok_agent.py` | `grok` | `grok -p "<prompt>" --yolo` (or equivalent) |
| `stub_agent.py` | `stub` | In-process; no network. For CI / pipeline tests |
| `base.py` | — | Protocol + shared parse/clean |
| `roster.py` | — | Assign which agent does which tile (`both` = alternate) |

## Rules

1. **`agy` means the `agy` binary.** Not `antigravity`, not a synonym invent — the PATH tool is literally `agy`.
2. Image paths in prompts must be **absolute** so headless sessions can open them.
3. Strip markdown fences and leading “Sure!” fluff; keep the prompt body.
4. On timeout/non-zero exit: retry once; then raise with stderr tail logged to events.
5. Record `agent`, `cli`, `model` (if known), `duration_ms` in attribution.
6. Do not shell with unescaped user content beyond careful quoting / argv lists (use `subprocess` argv list, never `shell=True`).
7. **`stub` never calls external CLIs.** Use `--agent stub` for offline dry-runs and unit/integration tests. Stub may open local crop paths with Pillow for a palette hint only.
