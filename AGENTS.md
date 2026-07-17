# AGENTS.md — tilagup Repository

> *For autonomous agents working in this repo. Humans: this is how the robots understand the project. Read it anyway.*

## Project Identity

- **Name:** tilagup (tiled agent upscale)
- **Type:** CLI tool + library for agent-driven tiled SD upscaling
- **Language:** Python 3.11+
- **Version:** 0.1.0-prealpha
- **Entry:** `uv run up.py <image>` or `uv run tilagup <image>`

## What This Is

Given an image, tilagup:

1. Creates a **run archive** (log everything; upscale is slow).
2. Asks a vision agent for a **base prompt** (the soul of the image).
3. **Splits** the image into overlapping tiles (crops on disk for agents + coords for SD).
4. Asks agents for a **unique tile prompt** per crop, anchored to the base (variation controlled).
5. Runs **FastSD CPU tiled SD upscale** with per-tile prompts + soft masks.
6. Records **who wrote which prompt** (agy / grok / human) in JSON.

## Repository Layout

```
tilagup/
├── AGENTS.md              — this file
├── README.md              — project overview
├── pyproject.toml         — package + deps
├── up.py                  — thin CLI entry (uv run up.py …)
├── design/                — rationale, decisions
├── docs/                  — user-facing guides
├── src/tilagup/           — library code
│   ├── agents/            — agy / grok adapters
│   └── …
├── scripts/               — one-off helpers
├── tests/                 — unit tests (no GPU required)
└── runs/                  — local run archives (gitignored)
```

## Conventions

### For all agents working here

1. **AGENTS.md in every directory.** Read it before editing files there.
2. **Run archives are sacred.** Never delete a `runs/<id>/` without explicit human OK. Prefer append-only `events.log` + update `run.json`.
3. **Base-locked tile prompts.** Every tile prompt must stay inside the base style/subject. Variation is local detail, not new global subjects.
4. **Reuse FastSD blend.** Do not invent a new paste path. Feed `tiles[]` into FastSD’s tiled upscaler (overlap + soft mask).
5. **Agent output is boring.** Vision agents must return prompt text only (or write a file). Parse failures → one retry → log + fail tile.
6. **YAML/JSON for machine state; markdown for humans.** `run.json` is authoritative for a run; docs explain how to read it.
7. **YAGNI for v0.1.** Interactive edit UI, multi-pass gem.md stages, fancy named zones — later.

### Naming

| Kind | Style |
|------|--------|
| Python modules | `snake_case.py` |
| Docs | `lowercase-hyphenated.md` |
| Run IDs | `YYYYMMDD_HHMMSS_<short>` |
| Tile IDs | `r{row:02d}_c{col:02d}` |
| JSON fields | `snake_case` |

### Commit prefixes

- `feat:` — user-facing capability
- `fix:` — bug fix
- `docs:` — documentation only
- `design:` — design/ rationale
- `chore:` — packaging, lint, repo hygiene
- `test:` — tests

### Agent attribution

When an agent writes a prompt, record at minimum:

```json
{
  "agent": "agy",
  "cli": "agy",
  "model": null,
  "created_at": "ISO-8601",
  "raw_path": "optional path to raw response"
}
```

Allowed `agent` values: `agy`, `grok`, `human`, `unknown`.

## Current State

**Phase:** 0.1.0-prealpha scaffold

**Done / target for this scaffold:**

- Package layout + AGENTS.md tree
- Run archive (`run.json`, tiles, events.log)
- Tile split with overlap
- `agy` + `grok` headless adapters
- `stub` offline agent for CI / full dry-run tests
- Dry-run (prompts only)
- FastSD CPU upscale hook (env `FASTSDCPU_ROOT`)
- Resume + progress

**Not yet:**

- Interactive prompt editing
- Multi-pass hierarchical “growth” (see gem.md experiments elsewhere)
- Parallel agent fan-out

## Next Action

Implement → dry-run on a real image → wire FastSD → document in `docs/getting-started.md`.
