Focus exclusively on the Overseer project in this current workspace.

Implement autonomy increment 8 (Target SPEC.md pointer):
1. Update the factory execution pipeline so that at the start of an attempt, the factory reads `<workspace>/SPEC.md` (bounded to 64 KiB via `overseer/readback.py`).
2. Record its path and cryptographic digest (or absence reason) in the context manifest.
3. Hand the attempt `OVERSEER_SPEC_PATH` and `OVERSEER_SPEC_SHA256` in its environment beside the skills variables.
4. Enforce safety checks: refuse a symlinked SPEC pointing outside the workspace; handle a missing SPEC gracefully as absent rather than an error (adding no spec fields if missing).
5. Add unit tests covering SPEC detection, path validation, boundary limits, and manifest integration.
6. Remap factory citations by content, run `python3 scripts/check` and `python3 scripts/check-doc-references` to ensure 100% test pass rates and valid documentation citations, update WORK_LOG.md, and commit clean.
