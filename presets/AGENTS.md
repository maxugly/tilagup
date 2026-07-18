# AGENTS.md — presets/

Shell presets for humans who will not remember CLI flags.

## Rules

1. Every variation is a **pair**: `NAME_dry.sh` + `NAME_upscale.sh`.
2. Shared logic only in `_lib.sh`.
3. Default behavior of the product remains **default_*** (texture none, strength 0.28).
4. New experiments = new files; do not change existing preset meanings without renaming.
5. Keep scripts `chmod +x`.
6. Do not put secrets here.

## Adding a preset

Copy an existing pair, edit the flag block, document in `README.md` table.
