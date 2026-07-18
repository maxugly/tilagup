# AGENTS.md — tests/

## Rules

1. No live `agy` / `grok` calls — use `stub` / pure functions.  
2. No FastSD / OpenVINO model loads.  
3. Use `tmp_path` for filesystem side effects.  

## Coverage (current)

- Tile grid math  
- Archive create / image_key layout  
- Prompt cleaning  
- CLIP fit / unique-first  
- Full dry-run pipeline with stub  

## Coverage (when zones land)

- Bbox / tile overlap assignment  
- Tie-break priority  
- Residual / background zone  
- `zone_map.json` round-trip  
- Stub zone discovery JSON  
