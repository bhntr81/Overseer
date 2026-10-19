# Overseer

A local Python monitor for explicitly opted-in Codex and Claude terminal sessions.
It checks every 30 seconds and can send a configured continuation message after
a recognized question remains unchanged for three minutes. No API key or Python
dependencies are required. Requires Python 3 and tmux on Linux.

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

The [software factory blueprint](docs/SOFTWARE_FACTORY_BLUEPRINT.md) describes the
CEO, director, provider supervisors, Model Router, worker agents, quality gates,
and phased delivery plan. [Execution record and commands](docs/FACTORY_EXECUTION.md)
distinguish the implemented local task runner from planned provider automation.

Run `python3 -m overseer.factory --help` for the separate explicit-job runner.
Run `python3 scripts/check` for isolated local verification. The terminal monitor
continues to operate independently.

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

## Try it

```sh
cd /home/kali/Projects/Overseer
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
cd /home/kali/Projects/Overseer
systemctl --user stop overseer.service
python3 -m overseer run
```

To enable sending, set `dry_run` to `false` in `config.json`.
Change `reply` to the desired single-line continuation instruction.
The included reply requires the shared `/home/kali/Projects/AGENTS.md` workflow:
use `coder_optimization` guidance and a dedicated prompt-writing agent. The writer
reads the last execution output and verification results, writes a bounded next
prompt, and the primary agent executes and verifies that prompt before returning
results to the writer. Project-specific agent/model requirements still apply.
All ten current project roots link to this shared guidance; new projects beneath
that directory inherit it. Inactive projects do not have live agents, and existing
terminal sessions must load the updated instructions before following them.
It distinguishes a completed prompt-writing step from a completed authorized
project workflow: when execution was already authorized, the client should
execute the next step and verify its results. Draft-only requests do not grant
execution authority. Completion and blocker responses must explain the reason
before ending with the appropriate stop marker.

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
operator can explicitly unwatch it to release its reservation. Exclusions and
unwatching remove panes from queue control. The scheduler serializes Overseer's
automatic terminal dispatches only: manual input, excluded sessions, and agents
delegated inside a session can still overlap. Terminal-state detection remains
heuristic, so this is not a provider-wide concurrency lock.

The monitor recognizes explicit routine questions such as “Would you like me to
continue?” and “Shall I proceed?”. With `continue_on_completion: true` (enabled),
it also recognizes Codex's completed-turn footer, `Worked for … • …`, when the
composer is empty. It asks the client to continue only unfinished authorized work,
using the designated prompt agent if applicable. A standalone `OVERSEER_DONE` or
`OVERSEER_NEEDS_INPUT` response stops further automatic continuation of that
screen. It does not use another LLM to interpret arbitrary questions. Idle alone
without a recognized question/completion marker does not trigger a reply.

If a client appears to ignore a continuation, inspect its response in the pane.
`sent routine continuation` in the journal means tmux accepted the input commands;
it does not prove submission, execution, or completion. A visible client response
of `OVERSEER_DONE` means the client received the instruction and declared its work
complete; it can still have interpreted the task too narrowly. Correct that task
scope in the conversation when necessary. Changing `reply` applies to future
eligible sends; it does not clear existing stop markers or resend old messages.

The foreground command must be `codex` or `claude`, with an empty composer line
(`>`, `›`, or `❯`, including the verified empty Codex placeholder). A shell,
typed draft, copy mode, exited pane, unrecognized
question, visible generation marker, or sensitive/permission wording causes a
skip. UI versions, wrappers, placeholders, and different languages can cause
missed prompts. These checks are heuristics, not proof of an agent's state;
validate against your clients in dry-run mode first.

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
