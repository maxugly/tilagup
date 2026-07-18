# AGENTS.md — docs/

> *User-facing documentation for operators and implementors using tilagup.*

## What lives here

| File | Audience | Content |
|------|----------|---------|
| `getting-started.md` | Everyone | Install, dry-run, upscale, flags |
| `run-archive.md` | Operators / agents | On-disk layout, stages, `run.json` |
| `agents.md` | Operators | agy/grok/stub, CLIP, attribution |
| `zones.md` | Operators | What zones mean; not yet shipped |

Normative zone **spec** is `design/zones.md`, not here.

## Conventions

1. State **what is shipped vs planned** clearly (zones are planned).  
2. Commands must match `tilagup.cli` / `up.py --help`.  
3. Prefer same-terminal UX language; do not document “tail events.log in another pane” as the primary workflow.  
4. **Last updated** date at top or bottom when you change a file.  
5. Link to `design/` for architecture; do not fork a second zones data model.

## When zones ship

Update `getting-started.md`, `run-archive.md`, and `zones.md` in the same PR as code. Mark zones **shipped** and document `--no-zones` / `--zones-json` when they exist.
