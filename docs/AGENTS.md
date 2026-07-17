# AGENTS.md — docs/

> *For autonomous agents writing user-facing documentation.*

## What Lives Here

Guides and reference for humans (and agents) **using** tilagup. Not design rationale (`design/`), not package internals (`src/tilagup/AGENTS.md`).

## Conventions

1. **Audience:** someone who has an image and wants a tiled agent upscale.
2. **Start with prerequisites.**
3. **Copy-pasteable commands** with expected artifacts.
4. **Date** “Last updated” at the bottom when you change a doc.
5. Link to `run.json` field names exactly as implemented.
6. Do not invent CLI flags — match `tilagup.cli` / `up.py --help`.

## Files

| File | Content |
|------|---------|
| `getting-started.md` | Install, dry-run, first real upscale |
| `run-archive.md` | Directory layout + `run.json` schema |
| `agents.md` | How agy/grok are invoked and attributed |
