# Pending model decision for pane %3

Status: **resolved**. The operator answered through the question recorded
below, and the applied decision is recorded in the "Resolved" section at the
end of this file. The implementation prompt was written by the dedicated
prompt-writing agent and executed by the primary agent.

Recorded 2026-10-19. Prompt authorship: the dedicated prompt-writing agent
authored the implementation prompt; the primary agent implemented it. This
file records the operator question that the implementation was built to ask.

## The question

Pane `%3` is paused with a pending model decision
(`unsupported_model`, detail `gpt-6-astra`). `gpt-6-luna` is excluded by the
operator. Which provider and model should it use?

| Choice | Provider | Model | How it applies |
| --- | --- | --- | --- |
| A | `openai` | `gpt-5.6-terra` (`GPT-5.6-Terra`) | in place through the Codex picker |
| B | `openai` | `gpt-5.6-luna` (`GPT-5.6-Luna`) | in place through the Codex picker |
| C | `claude` | `opus` | new Claude Code session for the same project |
| D | `opencode` | any of the 44 configured ids | needs the monitor's client allowlist extended first |
| E | `grok` | `grok-4.7`, `grok-4.7-build-fast`, `grok-4.6`, `grok-4.5` | needs the monitor's client allowlist extended first |

The operator's previous answer, before asking for the question to be recorded
instead of answered, was A.

## State at the time of writing

- Pane `%3`, session `overseer-crypto-cooking-1236021`, reptyr target
  `1236021:6100232` (alive), `pane_in_mode=0`, `pane_dead=0`.
- Visible error, verbatim:
  `■ {"type":"error","status":400,"error":{"type":"invalid_request_error","message":"The 'gpt-6-astra' model is not supported when using Codex with a ChatGPT account."}}`
- Current model in the composer footer: `GPT-6-Astra ultra`.
- `%3` is watched. `%2` and `%4` are watched and unchanged. `%0` is OFF and
  dead. `%1` and `%5` are excluded.
- Monitor service active, PID 3309774, started 2026-10-19 23:37:48.
  `Active reservation: none`; the paused pane holds no FIFO slot.
- Journal line proving the pause:
  `Oct 19 23:38:18 ... WARNING %3 model decision pending: unsupported_model (gpt-6-astra); choose with: python3 -m overseer model-select %3`
- The composer was probed once with a literal `/model` and cleared again; the
  pane is back to `» Ask Codex to do anything`. No picker was opened, no
  model was changed, and no resolution was recorded.
- In this Codex build, typing `/model` shows the inline hint
  "choose what model and reasoning effort to use". The picker opens on Enter
  and also sets the reasoning effort variant; the current session is on
  `ultra`.

## Applying the choice

For A or B, in place, no further approval is needed:

```sh
cd /home/kali/Projects/Overseer
python3 -m overseer model-select %3 --provider openai --model gpt-5.6-terra
```

The interactive form asks the same question and applies the answer:

```sh
python3 -m overseer model-select %3
```

The command drives the client's own picker, confirms the change from the
composer footer, and records the resolution where the monitor reads it. The
monitor then stops pausing `%3` for that exact failure and the pane returns
to the normal queue, where the 180 second idle threshold applies before a
continuation is dispatched.

For C, the client differs, so the command reports it and prints the commands
to move the work:

```sh
python3 -m overseer start crypto-cooking claude --cwd /home/kali/Projects/Crypto-Cooking
python3 -m overseer watch <new pane>
```

The old `%3` pane stays paused until it is replaced or unwatched.

For D and E, the monitor cannot watch those clients yet, so the command
refuses and says so. Extending the client allowlist is a separate increment
and was not started.

## What has and has not been built

Implemented and committed as `fa9c9f0` "Pause a pane on a model failure and
add an operator model choice":

- `overseer/modelchoice.py` — failure detection, the provider allowlist read
  from `config.json`, and the pure picker-matching helpers.
- `overseer/scheduler.py` — the `model_blocked` phase. A paused pane is never
  dispatched, is never retried, is never given a substituted model, and
  releases its FIFO reservation so it cannot starve the other watched panes.
- `overseer/__main__.py` — the `model-select` command and the pending-decision
  section in `status`.
- `overseer/tmux.py` — the client model picker driver and a read-only pane
  inspection that does not require the opt-in.
- `config.json` — `model_providers` and `allowed_providers`, with model ids
  verified locally from `codex debug models`, `claude --help`,
  `opencode models`, and `~/.grok/models_cache.json`.
- `tests/test_model_choice.py` — 12 tests; the suite grew from 93 to 105 and
  passes.

The feature does not substitute a model automatically, does not retry a blocked
pane, and does not drive a client the account or provider cannot serve.

## Still open

- This decision, and the follow-through of applying it.
- The monitor cannot watch `opencode` or `grok` sessions.
- `%0`'s bridged client (PID 1174383) is dead and unwatched.
- `%2` and `%4` carry `OVERSEER_DONE` and `OVERSEER_NEEDS_INPUT` stop markers
  and both still show `GPT-6-Astra medium`, which is not in the current Codex
  catalog either.
- The factory still has no real provider adapter.
