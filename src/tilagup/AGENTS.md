# AGENTS.md — src/tilagup/

> *For autonomous agents editing library code.*

## Package map

| Module | Responsibility |
|--------|----------------|
| `cli.py` | argparse entry, orchestrates stages |
| `archive.py` | run dir creation, `run.json`, events.log, resume |
| `tiles.py` | grid math, crop export, overlap |
| `pipeline.py` | stage machine: init → base → split → tile prompts → upscale → done |
| `upscale_fastsd.py` | FastSD CPU tiled upscale integration |
| `prompts_lib.py` | system/user prompt templates for vision agents |
| `agents/` | CLI adapters (`agy`, `grok`) |

## Rules

1. **Atomic writes** to `run.json` (write temp + rename) so a crash mid-write does not corrupt.
2. **Never require GPU** to import the package or run unit tests for split/archive.
3. **Stages are idempotent:** if `run.json` already has base prompt text, skip re-prompt unless `--force`.
4. FastSD is optional at import time; fail only when upscale stage runs without `FASTSDCPU_ROOT`.
5. Tile prompts always receive `base_prompt` + variation + crop path in the agent call.

## Tests

Unit tests live in `tests/` and must not call live agents or load SD models.
