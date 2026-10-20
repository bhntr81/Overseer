# Overseer

A local Python monitor for explicitly opted-in Codex and Claude terminal sessions.
It checks every 30 seconds. When a watched pane shows a structured output
report, Overseer builds the next one-line prompt from that report and submits
it. When no report is visible, it can send the configured continuation
instruction after a recognized question remains unchanged for three minutes.
No API key or Python dependencies are required. Requires Python 3 and tmux
on Linux.

The integration uses tmux panes, accessible from one QTerminal project hub. It
does not switch desktop focus during monitoring. The six original Codex clients
were migrated live using a locally installed `reptyr -T` bridge; they were not
restarted. Original QTerminal windows retain stale output and are hidden from
the desktop/taskbar while their processes stay alive. Use the project hub.
Migration metadata is recorded in
`~/.local/state/overseer/migration.json`. Bridge targets are checked against their
PID, process start time, foreground process group, and bridge executable before
any input is sent.

## One project window

Open **Overseer Terminals** on the desktop. It focuses the existing project
display; if that display was closed, it attaches a new window to the existing
solver session, or another surviving project if the solver session has ended.
Press **F12** for an alphabetically ordered project menu, then
choose a project with its number or the arrow keys and Enter. **Ctrl-b s** opens
tmux's complete session tree, including sessions added later. **Ctrl-b d** detaches
the display without stopping a project. The status bar shows the current project.

This switches between the original sessions; it neither copies nor restarts
them. Selecting an excluded project does not enroll it or change the FIFO queue.
The F12 menu is configured in `terminal-hub.tmux.conf` and loaded from
`~/.tmux.conf`. Its labels/targets describe the six migrated sessions; update
that file if those sessions are renamed or replaced. New sessions remain
accessible through Ctrl-b s. The launcher requires the existing tmux server.

Five redundant tmux displays were detached. Six legacy donor windows are hidden,
not terminated, because they remain ancestors of the migrated clients. To show
them again, run `scripts/terminal-hub --restore-hidden`. Do not close those legacy
windows while their migrated clients are in use. The current Overseer conversation
and unrelated terminals are left alone. Window IDs and restore information are
recorded in `~/.local/state/overseer/terminal-hub.json`.

## Software factory direction

Overseer is the software factory project. The current design is the
[Version 2 blueprint](docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt), moved verbatim from
Downloads. The [original blueprint](docs/SOFTWARE_FACTORY_BLUEPRINT.md) is retained
for history. [Selected third-party skills](docs/FACTORY_SKILLS.md) support prompt
writing, bounded loops, and skill authoring. [Execution record and commands](docs/FACTORY_EXECUTION.md)
distinguish the implemented local task runner from planned provider automation.
The [harness framework](docs/HARNESS_FRAMEWORK.md) maps that design onto the six
harness pillars and the code that implements them.

Run `python3 -m overseer.factory --help` for the separate explicit-job runner.
Each completed run writes a `context.json` manifest into its run evidence
directory, recording what the controller supplied for that attempt and why,
and the ledger stores the four memory record kinds: a verified fact, a
decision, a hypothesis, and a historical attempt. Before a new attempt starts,
the runner recalls the relevant records: those of its own job and those of
earlier runs in the same project. A decision a later decision superseded, and a
verified fact whose bound revision is no longer the workspace's base commit,
are marked as unusable rather than handed over as settled. The recall is
written to `recall.json` in the run evidence and passed to the worker through
`OVERSEER_RECALL_PATH`, `OVERSEER_RECALL_COUNT`, `OVERSEER_RECALL_KINDS`, and
`OVERSEER_RECALL_SUMMARY`. The runner also assembles a codebase context from
the workspace file tree: it selects the files the task commands name or whose
path matches the task terms, extracts their structural symbols, and writes the
map to `codebase.json` in the run evidence, which the worker receives through
`OVERSEER_CODEBASE_PATH`, `OVERSEER_CODEBASE_FILES`,
`OVERSEER_CODEBASE_SELECTED`, `OVERSEER_CODEBASE_SUMMARY`, and
`OVERSEER_CODEBASE_RELATIONS`. The map names
the files and the symbols and carries a bounded excerpt of their code: at
most 8 KiB and 60 lines per file, and 32 KiB for the whole attempt. It also
relates each selected symbol to the code that calls it and to the test files
that cover it. That relation is a static reference and not a proven call:
Python is parsed, every other language is matched textually, and an attribute
reference does not name the object it belongs to. The search is capped at 400
files and 2 MiB, with 20 callers and 10 tests per symbol; the size of a file
is checked before it is opened, so the bytes read never pass the bound. A
symbol nothing references is recorded as such, with the number of files that
were searched, and a corpus the cap truncated is recorded as truncated, with
the reason that says so. A file
whose name marks it as a secret is never read for its content, and a file that
is binary, too large, or not text is left alone. The manifest records the
excerpt's line ranges and byte counts, and the relation counts and the
per-symbol entries.
A command-mode task must carry a `contract` block that states the
role, risk tier, external effects, protected paths, approval requirements,
acceptance identifiers, required capabilities, project constraints, measured
evidence, provider availability, and budget limits. The block is validated and
stored with the task; it records those statements and enforces none of them.
A command-mode task may also carry an optional `envelope` block that names one
of the four capability modes, its declared scope, whether a fresh decision is
required, and the decider it names. The mode, the scope, and the decider
identity are recorded, not authorized. The one enforced part is the gate: a
task that declares it needs a decision waits in `awaiting_approval` and is not
dispatched until a decision is recorded in the ledger, and that record names
who decided. Give the decision with the runner's own command:

```sh
python3 -m overseer.factory decide <task-id> --decision granted --decider operator
```

Run `python3 scripts/check` for isolated local verification. The terminal
monitor continues to operate independently.

## Installed configuration

The user service is enabled and running with automatic replies. User lingering
is enabled, allowing it to run after logout. It checks every 30 seconds, waits
three minutes, and permits at most 12 replies per pane per rolling day, with a
15-minute cooldown. Kali labs and the setup conversation are excluded.

```sh
overseer status
overseer exclude labs
overseer exclude %2
overseer include %2
journalctl --user -u overseer.service -f
systemctl --user stop overseer.service
```

Exclusions match pane IDs exactly, or session names/window titles by
case-insensitive substring. Quoted globs are supported (`overseer exclude '*labs*'`).
`include` removes the exact exclusion rule supplied; other matching rules remain
in force. `watch` and `unwatch` independently control pane enrollment. Config is
reloaded every poll, so exclusions and setting changes apply within 30 seconds.
Do not use `include` as a substitute for checking `status` when several rules match.

## Project targeting

The monitor manages only the panes that are in scope. A pane is in scope when
it was explicitly enrolled with `overseer watch`, or when the configured
target scope names it. Every other tmux window is ignored: it is never
snapshotted, never queued, never sent to, and never typed into.

`config.json` carries the scope:

```json
"targets": ["overseer-projects-1174383"],
"target_paths": ["."]
```

- `targets` are patterns matched against the pane ID, the session name, and the
  window title, with the same rules as `exclude`: an exact pane ID, a
  case-insensitive substring, or a quoted glob. A matching pane is managed
  without being enrolled.
- `target_paths` are directories. A pane whose client runs inside one of them
  is managed. A relative path is resolved against the directory that holds
  `config.json`, so `"."` means this workspace. The directory is the client's
  own, not the bridge's, so a reptyr-bridged session is judged by the project
  its client actually works on.

The rules, in order: an excluded pane is never managed, even when it is
enrolled or targeted. Otherwise an enrolled pane is managed, then a targeted
one. `overseer status` shows the scope of every window: `WATCHED` for an
enrolled pane, `TARGETED` for a pane in scope by configuration, `EXCLUDED` for
an excluded one, and `OUT OF SCOPE` for a window the monitor ignores.

## Try it

```sh
cd /home/kali/Programming/Projects/Overseer
python3 -m unittest discover -s tests -v
python3 -m overseer start my-project codex
tmux attach-session -t my-project
```

Use `claude` in place of `codex` for Claude. Additional client arguments follow
the client name, for example `python3 -m overseer start resumed codex resume`.
Use the client's resume picker to choose an existing conversation. To keep the
client running after leaving a terminal, detach with `Ctrl-b`, then `d`.

To preview instead of sending, set `dry_run` to `true` in `config.json`. Eligible
replies are then logged but never sent. The installed background service already
runs the monitor; to run it manually, stop that service first:

```sh
cd /home/kali/Programming/Projects/Overseer
systemctl --user stop overseer.service
python3 -m overseer run
```

To enable sending, set `dry_run` to `false` in `config.json`.
`reply` is the single-line instruction used when a pane has not yet printed a
report. The included reply tells the client to follow
`/home/kali/Programming/Projects/AGENTS.md` and the coder optimization playbook, do the next
authorized step, and print one visible `OVERSEER_REPORT` line. That line starts
with `OVERSEER_REPORT` and a JSON object. The keys are `status`, `objective`,
`remaining`, `done`, and `evidence`. `status` is `continue`, `done`, or
`needs_input`. `continue` needs a nonempty objective and remaining step.
Overseer reads the latest report on the visible screen, copies those fields
into the next one-line prompt, and submits that prompt. It does not ask another
model to invent the prompt, and it does not execute terminal text. A `done` or
`needs_input` report stops further automatic prompts for that screen. An invalid
report, or a continue report with no objective or remaining step, also stops
that screen instead of falling back to `reply`. Project-specific agent and model
requirements still apply. Draft-only requests do not grant execution authority.

Manage existing tmux panes:

```sh
tmux list-panes -a
python3 -m overseer watch %0
python3 -m overseer status
python3 -m overseer unwatch %0
```

Only enroll panes whose LLM sessions you want to continue automatically.
Do not type in a watched pane while the bot is responding; desktop input and
tmux writes cannot be made atomic together. Unwatch the pane first when taking
over manually.

## Model decisions

When a client reports that its model, its account, or its credits cannot be
used, the monitor does not retry and does not substitute a model. The affected
pane is paused, its FIFO reservation is released so the other watched panes
keep running, and the decision is recorded. The journal names the command:

```text
%3 model decision pending: unsupported_model (gpt-6-astra); choose with: python3 -m overseer model-select %3
```

`python3 -m overseer status` lists every pending decision. `python3 -m overseer
model-select %3` asks which permitted provider and model to use; the
non-interactive form is `python3 -m overseer model-select %3 --provider openai
--model gpt-5.6-terra`. A choice is applied through the client's own model picker
and confirmed from the pane's composer footer, so a pane that cannot serve the
chosen model is reported instead of being forced. When the chosen provider uses
a different client, the work is routed: a new session is started for that client
in the same working directory and the pane it came from stays paused.

The Codex picker has two steps. The first lists the models and the second asks
for the reasoning level, where the scope key `s` applies the change to the
session only and leaves the global default alone. The monitor uses the session
scope, so a change made through it does not edit the client's configuration.

### Credit fallback hierarchy

`config.json` carries a `fallback_policy`:

- **Primary, the paid tier.** `primary` names the providers that carry normal
  coding work.
- **Fallback 1, zero paid credits.** When a client reports exhausted credits,
  `zero_credit` names the provider that takes over. The monitor routes the work
  automatically: it starts that client in the pane's working directory, enrolls
  it, and sends the configured continuation so the work resumes. The pane that
  failed stays paused.
- **Fallback 2, every credit maxed out.** When the zero-credit tier reports the
  same failure, the pane is paused with the status `CREDITS_EXHAUSTED_WAITING`.
  Nothing is retried, no lower tier is used, and no model is substituted. The
  pause ends by itself when the client stops showing the error, which is what
  waiting for the credits to reset means here.

```text
%3 CREDITS_EXHAUSTED_WAITING: insufficient credit (credit_exhausted); waiting for the credits to reset
```

`excluded_models` names model ids that are offered nowhere: they are absent
from the provider lists, from the interactive picker, and from every automatic
choice. The current exclusion is `gpt-6-luna`, on the operator's stated
judgment that it is not a coding model. That is the operator's reason, not a
measured result.

The permitted providers and their model identifiers live in `config.json` under
`model_providers` and `allowed_providers`. They were verified locally with
`codex debug models`, `claude --help`, `opencode models`, and
`~/.grok/models_cache.json`, and they can go stale. No model name may be
invented; a model outside the configured list is refused. Codex, Claude, and
OpenCode sessions can be watched and driven; a Grok session cannot, because the
monitor does not recognize its composer, and it is reported instead of being
forced.

This feature does not substitute a model automatically, does not retry a
blocked pane, and does not drive a client that the account or provider cannot
serve. A route creates a new session; it never restarts or replaces an existing
one, and it never sends text to a pane other than the one it just created.

## Background service

```sh
mkdir -p ~/.config/systemd/user
cp overseer.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now overseer.service
journalctl --user -u overseer.service -f
```

Stop: `systemctl --user stop overseer.service`. Disable automatic startup:
`systemctl --user disable --now overseer.service`. Restart after code changes:
`systemctl --user restart overseer.service`.

For service operation after logout and startup without a desktop login, enable
user lingering with `loginctl enable-linger "$USER"` (the system may require
administrator authorization). The computer must remain powered on and awake.
The service restarts the monitor after failure; it does not recreate LLM
sessions after reboot. Reopen/resume and enroll those sessions after reboot.

## Detection and limits

With `serial_queue: true`, automatic sends use a persisted FIFO queue. Only one
Overseer-dispatched turn owns the slot. Other eligible panes wait until that turn
visibly finishes, stops, or reports a model-capacity error. Already running watched
panes also prevent new dispatches; they are never interrupted. New follow-ups go
behind existing waiters. Queue order and the active reservation survive restart
and appear in `overseer status`.

An explicit `Selected model is at capacity` terminal error enters the queue with
`capacity_retry_seconds` of waiting (default 120). It retries the same model at
most `capacity_max_retries` times (default 3) per failure episode, still subject
to the rolling daily reply limit. Retry delay replaces the ordinary idle/cooldown
timers for these errors. The FIFO head waits its retry delay; after its budget is
exhausted it is skipped so other work can run. A completed turn resets the retry
budget. Capacity errors do not establish that local concurrency caused them.

An ambiguous delivery or unrecognized completion holds the slot and logs a
warning after two minutes. Inspect that pane rather than blindly resending; an
identical capacity screen without an observed intervening run remains ambiguous
and is held rather than automatically retried. Changed footer tips do not count
as evidence of a new answer. A new routine continuation question can also end a
turn for clients that do not display Codex's completed-turn footer. An
operator can explicitly unwatch it to release its reservation. Exclusions,
unwatching, and leaving the target scope remove panes from queue control. The
scheduler serializes Overseer's
automatic terminal dispatches only: manual input, excluded sessions, and agents
delegated inside a session can still overlap. Terminal-state detection remains
heuristic, so this is not a provider-wide concurrency lock.

The monitor recognizes explicit routine questions such as “Would you like me to
continue?” and “Shall I proceed?”. With `continue_on_completion: true` (enabled),
it also recognizes Codex's completed-turn footer, `Worked for … • …`, when the
composer is empty. Eligible screens that contain an `OVERSEER_REPORT` line
receive a prompt built from that report. Eligible screens without one receive
`reply`. A standalone `OVERSEER_DONE` or `OVERSEER_NEEDS_INPUT` response stops
further automatic continuation of that screen, as does a report whose status is
`done` or `needs_input`. The report has to stay on one visible line because the
monitor captures the current pane, not scrollback. Permission wording, generation
markers, and the other skip rules still apply to the whole visible screen,
including text inside a report. Idle alone without a recognized
question/completion marker does not trigger a reply.

If a client appears to ignore a continuation, inspect its response in the pane.
`sent routine continuation` means the configured instruction was typed.
`sent report-based prompt` means the typed line was built from the visible
report. Neither journal line includes the prompt or the report, and neither
proves that the client submitted, executed, or finished the work. `skipped:
invalid output report`, `skipped: report has no remaining work`, and `skipped:
output report requested no further continuation` mean that screen was withheld
and will not be answered again until its visible text changes. A visible client
response of `OVERSEER_DONE` means the client declared its work complete; it can
still have interpreted the task too narrowly. Changing `reply` applies to future
eligible sends that have no report; it does not clear existing stop markers or
resend old messages. Code changes apply after the user service is restarted.
Config changes apply on the next poll.

The foreground command must be `codex`, `claude`, or `opencode`, with an empty
composer line (`>`, `›`, `❯`, or `»`, including the verified empty Codex
placeholder and the OpenCode composer box). A shell,
typed draft, copy mode, exited pane, unrecognized
question, visible generation marker, or sensitive/permission wording causes a
skip. UI versions, wrappers, placeholders, and different languages can cause
missed prompts. These checks are heuristics, not proof of an agent's state;
validate against your clients in dry-run mode first. A Grok session is not
recognized, so the monitor reports it instead of driving it.

An OpenCode session is understood in both of its turn states. While a turn
runs, the running footer (`esc interrupt`) and the background-work hint mark
the pane as active, and it is never answered. When the turn ends, that marker
is gone and the composer is an empty box, so the pane counts as finished, the
queue reservation is released, and the next continuation is sent. A fresh
session shows an `Ask anything…` placeholder in the same box. OpenCode draws
no user-message boundary, so the tail of its screen is treated as the current
answer.

Replies have a 15-minute cooldown and a limit of 12 per pane per rolling day.
The monitor persists fingerprints in `~/.local/state/overseer/state.json` so
the same screen is not answered again after restart. It saves a send reservation
before delivery; an ambiguous or failed delivery is not automatically retried.
A file lock prevents two monitors sharing that state from sending duplicates.
Logs contain pane IDs and action reasons, not conversation contents. State
contains hashes and timestamps, not captured terminal text.

The monitor does not click permission dialogs, change LLM approval settings,
answer substantive questions, or submit shell commands. The terminal content
is never executed as code. A final recheck narrows—but cannot eliminate—the
race between observing the pane and sending input.
