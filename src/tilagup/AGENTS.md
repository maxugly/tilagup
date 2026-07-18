# AGENTS.md — src/tilagup/

> *Library code. Read root AGENTS.md + design/zones.md before adding zone stages.*

## Package map

| Module | Responsibility | Zones note |
|--------|----------------|------------|
| `cli.py` | argparse, orchestration entry | Future: `--no-zones`, `--zones-json` |
| `pipeline.py` | Stage machine | Insert `zones` → `assign` → `zone_prompts` before tile prompts |
| `archive.py` | `runs/<image_key>/<run_id>/` | Add `zones/` writers when implementing |
| `tiles.py` | Grid math, crop export | Execution grid only; assignment is separate |
| `prompts_lib.py` | Agent prompt templates | Add zone discovery + zone prompt templates |
| `clip_fit.py` | CLIP unique-first fit | Tile fit should prefer local over zone restatement |
| `log.py` | Loud / quiet logging | Keep progress in-process |
| `upscale_fastsd.py` | Spawn FastSD worker | Pass zone-aware prompts via job JSON as plain tile prompts |
| `upscale_worker.py` | Runs in FastSD venv | Stay free of tilagup package imports if possible |
| `agents/` | agy / grok / stub | Zone discovery may need JSON-mode cleanup |

## Rules

1. **Zones = meaning; tiles = execution.** Do not replace FastSD soft-mask blend.  
2. Flat path (`base → tiles`) must keep working as `--no-zones` until zones are default.  
3. Atomic `run.json` writes.  
4. Unit tests: no live agents, no model load. Zone assignment tests = pure geometry.  
5. CLIP: unique-first; never “fix” quality by only head-truncating long essays.

## Target stage order

`init` → `zones` → `base_prompt` → `split` → `assign` → `zone_prompts` → `tile_prompts` → dry-run or `upscale` → `done`
