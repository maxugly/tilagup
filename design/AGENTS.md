# AGENTS.md — design/

> *Architecture and rationale. Not tutorials (`docs/`). Not runtime code.*

## What lives here

| File | Role |
|------|------|
| `zones.md` | **Normative** zone system: data model, discovery, assignment, prompts, acceptance |
| `rationale.md` | Why we chose archive-first, hierarchy, CLIP unique-first, FastSD venv, loud CLI |

## Rules

1. Spec changes to zones land in `zones.md` in the same PR as code that implements them.  
2. Mark **Status** (Designed / Partial / Shipped) at the top of each design doc.  
3. Do not put install walkthroughs here — that is `docs/`.  
4. Rejected ideas get a short entry in `rationale.md`, not silent deletion.

## Implementing zones

Read `zones.md` fully before writing code. Pipeline stage order and archive layout there are authoritative. Flat path must remain as `--no-zones` until zones are default.
