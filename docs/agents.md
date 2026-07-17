# Vision agents

How tilagup talks to **`agy`** and **`grok`**, and how credit is stored.

## Binaries (literally)

| Agent id | CLI binary | Headless flags |
|----------|------------|----------------|
| `agy` | `agy` | `agy -p "…" --dangerously-skip-permissions` |
| `grok` | `grok` | `grok -p "…" --yolo` |
| `stub` | *(in-process)* | No CLI; deterministic offline prompts for CI |

There is no `antigravity` wrapper in this project. Use **`agy`**.

## Modes (`--agent`)

| Value | Behavior |
|-------|----------|
| `agy` | All prompts via `agy` |
| `grok` | All prompts via `grok` |
| `both` | Base prompt uses first available (agy preferred in list order); tiles **alternate** `agy`, `grok`, … |
| `stub` | Offline stub agent — full pipeline dry-run without live vision CLIs |

Assignment is recorded per tile so you can see who wrote each prompt in `run.json`.

### Stub agent

```bash
uv run up.py sample.png --agent stub --dry-run
```

Writes real `run.json` / tile files with `attribution.agent = "stub"` and `model = "stub-v1"`. Used by automated tests; not for production upscales.

## What the agent receives

### Base prompt

- System-style instructions: SD prompt only, no markdown
- Absolute path to the full source image copy under the run dir

### Tile prompt

- Locked **base prompt** text
- Tile id / row / col
- Absolute path to that tile’s crop PNG
- Variation language (derived from `--variation`)

## Output contract

Agents must return **prompt text only**. Adapters strip markdown fences and common preambles. Empty output → retry once → fail tile (status `failed`, error string stored).

## Attribution object

```json
{
  "agent": "agy",
  "cli": "agy",
  "model": null,
  "duration_ms": 12000,
  "created_at": "2026-07-17T04:50:12+00:00"
}
```

Stored on `base_prompt` and each `tiles[]` entry, plus `tiles/<id>.meta.json`.

## Timeouts

`--timeout` (default 300s) applies per agent call. Upscale is separate and can run much longer.

## Offline / CI

Unit tests never call live agents. For dry-run without agents you would need a future stub agent — not in v0.1.

Last updated: 2026-07-17
