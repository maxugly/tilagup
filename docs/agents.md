# Vision agents

**Last updated:** 2026-07-17

How tilagup talks to **`agy`**, **`grok`**, and **`stub`**, and how credit is stored.

## Binaries

| Agent id | Binary | Headless |
|----------|--------|----------|
| `agy` | `agy` | `agy -p "…" --dangerously-skip-permissions` |
| `grok` | `grok` | `grok -p "…" --yolo` |
| `stub` | *(in-process)* | Offline CI; no network |

Use **`agy`**, not `antigravity`.

## Modes (`--agent`)

| Value | Behavior |
|-------|----------|
| `agy` | All prompts via `agy` |
| `grok` | All prompts via `grok` |
| `both` | Alternate across tiles (base uses first in list = agy first) |
| `stub` | Deterministic offline prompts |

Assignment is stored per prompt in `run.json`.

## What they write (today)

### Base

Short CLIP-safe overall prompt (≤~50 words): subject, materials, light, palette.

### Tile

Short prompt for **this crop only**, **unique-first** (local detail before shared style). Must not restate the entire global scene. Variation knob controls how much invention is allowed.

If the agent returns an essay, tilagup does **one rewrite pass** demanding ≤50 words / ≤75 CLIP tokens.

### Zones (planned)

1. **Discovery:** JSON zone list with normalized bboxes (structured output).  
2. **Zone prompt:** short identity for that region.  
3. **Tile:** unique-local under locked zone prompt (same rules as today + zone spine).

See [zones.md](zones.md) and [design/zones.md](../design/zones.md).

## CLIP limit

SD1.5 / turbo OpenVINO path: **~77 tokens**. Upscale worker unique-first fits to ~75. Do not rely on head-truncation of long base+local essays — regenerate with `--reprompt-tiles` instead of “repairing” by chopping.

## Attribution

```json
{
  "agent": "agy",
  "cli": "agy",
  "model": null,
  "duration_ms": 12000,
  "created_at": "2026-07-17T04:50:12+00:00"
}
```

On `base_prompt`, each `tiles[]` entry, and (planned) each zone.

## Timeouts

`--timeout` (default 300s) per agent call. Upscale is separate and can run much longer; worker heartbeats while FastSD runs.

## Loud I/O

Agent argv (including prompt body), streamed stdout/stderr, and 5s heartbeats print in the **same terminal** unless `--quiet`.
