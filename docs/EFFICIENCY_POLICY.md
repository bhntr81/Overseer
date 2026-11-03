# Overseer efficiency policy (P0-B)

Applied 2026-10-30 from the central audit
(`~/Programming/dev-management/DEVELOPMENT_ENVIRONMENT_AUDIT.md`, P0-B).
These are **config-only** settings in `config.json`; no code changed. The run
loop re-reads `config.json` every tick (~30 s), so edits apply live without a
restart, and an invalid edit fails safe (the tick logs a warning and keeps the
previous good config).

## Model selection
- **Sonnet is the default implementation model.** `model_providers.claude.models`
  lists `sonnet` first, then `opus`.
- **Opus is reserved, not removed.** It stays in the list and is selectable for a
  specific pane via `python3 -m overseer model-select <pane>` — use it for hard
  architecture, complex debugging, mathematical reasoning, and independent review.
- Routine continuations ride whatever model the watched pane already runs; with
  Claude Code's default now `sonnet` (P0-A), routine work is Sonnet by default.
- Credit exhaustion still falls back to the free tier (`fallback_policy.zero_credit`
  → `opencode`). Overseer never silently downgrades a model on its own; on a
  provider failure it pauses the pane and waits for an operator `model-select`.

## Unattended limits
- `max_per_day: 4` — a guardrail, not a target. Measured history at apply time:
  16 continuations total since 2026-10-18, never more than 5 in a day, 1 in the
  last 7 days. Raise it only if real throughput proves it too tight.
- `cooldown_seconds: 900`, `idle_seconds: 180`, `serial_queue: true` — one worker
  per project at a time; no runaway observed, so left as-is.
- Explicit stop signals are always honored (see `stopgate.py`); the stop-gate
  stays enabled.

## Continuation prompt (`reply`)
Handoff-first, to stop paying to re-read large docs every continuation:
1. Read the project's `SESSION_HANDOFF.md` if present (objective, last verified
   result, single next step); else fall back to `AGENTS.md`.
2. Open `BLUEPRINT.md` / `ROADMAP.md` only for the section the next step needs —
   not in full.
3. Do the next authorized step only; preserve scope, pauses, consent, draft-only
   limits; a prompt's stopping condition ends that prompt, not the objective.
4. Update `SESSION_HANDOFF.md` before stopping.
5. Print the `OVERSEER_REPORT {...}` status line and end with the matching
   `OVERSEER_STEP_DONE` / `OVERSEER_DONE` / `OVERSEER_NEEDS_INPUT` marker
   (contract unchanged — parsers in `policy.py`/`statusblock.py` depend on it).

The `reply` must stay one line ≤1000 characters (validated by `settings()`).

## Regression guard
`tests/test_config_policy.py` locks this policy in: Sonnet default + Opus present,
`max_per_day ≤ 4`, credit fallback reaches the free tier, and a handoff-first
prompt that keeps the status contract.

## Rollback
```
cp config.json.bak-20261030-061132 config.json   # live service re-reads within ~30 s
```

## Known limitation / next step
The service was OOM-killed once on 2026-10-30 (host has 0 B swap, 15 GiB RAM).
Next highest-value optimization is unrelated to Overseer config: **add swap**
(audit P1-D) so long builds/VMs don't kill the monitor mid-run.
