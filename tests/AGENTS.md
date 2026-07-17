# AGENTS.md — tests/

## Rules

1. No live `agy` / `grok` calls — use `--agent stub` / `StubAgent` for pipeline tests.
2. No FastSD / OpenVINO model loads.
3. Use `tmp_path` for filesystem side effects.
4. Cover: tile math, archive create/resume fields, prompt cleaning, **full dry-run pipeline with stub**.
