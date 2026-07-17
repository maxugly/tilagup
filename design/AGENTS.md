# AGENTS.md — design/

> *For autonomous agents writing design docs. Humans: why we chose what we chose.*

## What Lives Here

Design decisions and rationale. **Not** user tutorials (those are `docs/`). **Not** normative runtime behavior (code + `docs/run-archive.md` win for formats).

## Conventions

1. One decision (or tightly related cluster) per file, `lowercase-hyphenated.md`.
2. Every doc: context → options → decision → consequences.
3. Link to code paths when a decision is implemented.
4. Rejected ideas go in `rejected.md` (or a section), not deleted silently.
5. Do not put implementation code here.

## Files

| File | Content |
|------|---------|
| `rationale.md` | Core architecture: archive-first, base-locked tiles, agent attribution |
