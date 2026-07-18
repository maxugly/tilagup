# AGENTS.md — src/tilagup/agents/

> *Vision CLI adapters. Who writes prompts (and soon zone maps).*

## Adapters

| Module | Binary | Role |
|--------|--------|------|
| `agy_agent.py` | `agy` | Live vision |
| `grok_agent.py` | `grok` | Live vision |
| `stub_agent.py` | stub | Offline CI |
| `base.py` | — | Protocol, stream, clean text |
| `roster.py` | — | `agy` / `grok` / `both` / `stub` |

## Rules

1. **`agy` means the `agy` binary.**  
2. Absolute image paths in prompts.  
3. subprocess argv lists only (`shell=False`).  
4. Stream + heartbeat; never silent multi-minute waits without ALIVE lines.  
5. Attribution: `agent`, `cli`, `model`, `duration_ms`, `created_at`.  
6. **Prompt modes:** free text for base/tile/zone prompts; **JSON only** for zone discovery (when implemented) — parse strictly, retry once on invalid JSON.  
7. Stub must remain available without network for full dry-run tests (extend stub for fake zones when zone stages land).
