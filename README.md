# Overseer

Overseer keeps long LLM coding sessions moving without someone sitting at the keyboard,
and keeps a record of what was done.

A coding agent such as Claude Code, Codex, or OpenCode stops at the end of every turn and
waits. Much of the time the right answer is "continue with the next step". Overseer watches
the sessions you opt in, recognises a finished turn, and types the next bounded instruction,
built from a one-line report the agent itself printed. It stops and says why when the agent
asks for a person, reports that it is done, or hits a limit. It never clicks a permission
dialog, answers a substantive question, or runs terminal text as code.

It is local Python, standard library only: no `pip install`, no API key, no network calls of
its own. Version 1.0.0.

## What is in it

| Part | What it does | Command | Runs on |
|---|---|---|---|
| **Monitor** | Watches opted-in tmux panes that run a coding agent and sends the next prompt when a turn ends | `python3 -m overseer run` | Linux, WSL2 (needs tmux) |
| **Single-program mode** | The same policy for one agent in your own terminal, without tmux | `python3 -m overseer here claude` | Linux, WSL2 (needs a pty) |
| **Factory** | Runs one task at a time as explicit commands in a workspace and records the evidence in a SQLite ledger: logs, exit codes, a patch receipt, a handoff record | `python3 -m overseer.factory ...` | Linux, native Windows |
| **Loop** | Feeds the factory unattended: each job's worker report supplies the next instruction | `python3 -m overseer.orchestrate ...` | Linux, native Windows |

How the pieces fit:

```text
 monitor (python3 -m overseer run)                 factory (python3 -m overseer.factory)
 ---------------------------------                 -------------------------------------
 tmux pane running claude / codex / opencode       task spec (JSON): workspace, implementation
   | every 30 s: read the visible screen             command, check commands, contract
   v                                                  | submit -> ledger (SQLite, one writer)
 policy: is the turn finished? is there an            v
   OVERSEER_REPORT line? a stop marker?            run-one: start the command in its own
   | yes, and the limits allow                       process group, capture bounded output,
   v                                                 run the checks, record evidence
 type one bounded prompt into that pane               |
   (or hold the pane and log the reason)              v
                                                   loop (python3 -m overseer.orchestrate):
                                                     build the next job from the worker's
                                                     report, until done or a person is needed
```

The monitor and the factory are separate programs that share this repository. The monitor's
state is a JSON file; the factory's is its ledger. Neither reads the other's.

## Requirements

- Python 3.9 or newer. Nothing else to install for Overseer itself.
- For the monitor: Linux (or WSL2) with `tmux`.
- For the factory's diff receipts and the test suite: `git`.
- A coding-agent client that you have installed and signed in to yourself: `claude`
  (Claude Code), `codex` (OpenAI Codex CLI), or `opencode`. Overseer does not install
  clients or manage accounts.

## Install

There is no package or installer. Clone the repository and run it from there:

```sh
git clone https://github.com/bhntr81/Overseer.git
cd Overseer
cp config.example.json config.json      # PowerShell: Copy-Item config.example.json config.json
python3 scripts/check                   # optional: the test suite; PowerShell: .\scripts\check.ps1
```

Run every command below from the repository directory (or set `PYTHONPATH` to it).
On Windows use `py -3` or `python` in place of `python3`.

## Configure

`config.json` is your local file; it is git-ignored and Overseer never writes over it. To keep
it somewhere else, set `OVERSEER_CONFIG` to its path. The example starts safe: `dry_run` is
`true` (eligible replies are logged, nothing is typed), no pane is targeted, and the stop
agent is off. The settings you will most likely touch:

| Setting | Meaning | Example value |
|---|---|---|
| `dry_run` | `true` logs what would be sent and sends nothing | `true` |
| `poll_seconds` | How often panes are read | `30` |
| `idle_seconds` | How long a finished screen must stay unchanged before a reply | `180` |
| `cooldown_seconds`, `max_per_day` | Per-pane limits on automatic replies | `900`, `4` |
| `reply` | The one-line instruction sent when a finished screen has no report yet | see the file |
| `targets`, `target_paths` | Panes managed without enrolling them: by session or title pattern, or by the directory the client runs in | `[]` |
| `exclude` | Panes never managed | `[]` |
| `serial_queue` | Let only one Overseer-sent turn run at a time | `true` |
| `stop_agent` | Ask a separate model whether a worker's stop is legitimate before holding the pane (runs `claude -p`, which spends that account's credits) | off |
| `model_providers`, `allowed_providers`, `fallback_policy` | Which clients and model names may be chosen when a client reports its model or credits unusable. The names in the example are one machine's snapshot: replace them with what your clients list | see the file |

Changes to `config.json` apply at the next poll. Every field is described in
[docs/REFERENCE.md](docs/REFERENCE.md) and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Use the monitor (Linux or WSL2)

Start a client in a new tmux session that Overseer watches, and attach to it:

```sh
python3 -m overseer start my-project claude     # or codex, opencode; extra client arguments follow
tmux attach-session -t my-project               # detach again with Ctrl-b d
```

Or enrol a pane you already have, and see what Overseer manages:

```sh
tmux list-panes -a
python3 -m overseer watch %0
python3 -m overseer status
python3 -m overseer unwatch %0
```

Run the monitor in a terminal and watch what it decides:

```sh
python3 -m overseer run            # Ctrl-C stops it; add --once for a single poll
```

Leave `dry_run` on until the log shows it recognising your client's finished turns
correctly, then set `dry_run` to `false`. To run it in the background as a systemd user
service, edit `WorkingDirectory` in `overseer.service` to your clone's path, then:

```sh
mkdir -p ~/.config/systemd/user && cp overseer.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now overseer.service
journalctl --user -u overseer.service -f
```

Restart the service after updating the code. To run one client without tmux:
`python3 -m overseer here claude`.

### How a session cooperates

The agent ends a turn by printing one line that starts with `OVERSEER_REPORT` followed by a
JSON object with `status`, `objective`, `remaining`, `done`, and `evidence`. `status` is
`continue`, `step_done`, `done`, or `needs_input`. Overseer copies those fields into the next
prompt; it does not ask another model to invent one. `done` and `needs_input`, and the
markers `OVERSEER_DONE` and `OVERSEER_NEEDS_INPUT`, stop automatic replies for that screen.
After a `step_done` report the prompt tells the agent to hand the results to a separate
prompt-writing agent that follows [promptwriting/GUIDE.md](promptwriting/GUIDE.md).
The `reply` in the example configuration asks the agent to print such a report, so a session
needs no setup of its own. Do not type in a watched pane while Overseer is replying; unwatch
it first.

Other operator commands: `exclude` / `include` (patterns), `unfreeze PANE` (release a pane
held after an escalation), `model-select PANE` (answer a pending model decision),
`assess "objective"` (size a task). Each has `--help`.

## Use the factory (Linux or native Windows)

A task is a JSON file naming an absolute workspace directory, an implementation command, and
check commands, each an argument list (no shell). `factory/tasks/overseer-checks.json` is an
example; change its `workspace` to the absolute path of your clone before submitting it.
Its two checks run the document-reference check and two small test modules; it finishes in
seconds.

```sh
python3 -m overseer.factory submit factory/tasks/overseer-checks.json
python3 -m overseer.factory run-one
python3 -m overseer.factory status
python3 -m overseer.factory inspect overseer-foundation-checks-003
```

`passed` means every command exited 0; it is not a product review. The ledger and the run
evidence live under `~/.local/state/overseer/factory` unless `--db` names another file. A task
that declares it needs approval waits until you record a decision with `decide`. The commands
run with your own permissions: the factory is a recorder with a gate, not a sandbox.

The loop drives the factory with a real client, taking each next instruction from the
worker's own report: `python3 -m overseer.orchestrate --db DB --loop LOOP.json --target DIR`.
It uses the free OpenCode gateway unless the loop file names a runner; `claude` and `codex`
runners spend that account's credits. See [docs/FACTORY_EXECUTION.md](docs/FACTORY_EXECUTION.md).

## Clients

| Client | Monitor (tmux) | Factory / loop worker |
|---|---|---|
| Claude Code (`claude`) | Supported | Command line built, **not verified against a real run in this repository's tests** |
| OpenAI Codex CLI (`codex`) | Supported | Same: built, not verified |
| OpenCode (`opencode`) | Supported | The default runner (`opencode run`); tests use a stand-in, not the real client |
| Grok Build | Not driven: its composer is not recognised, so the pane is reported, not answered | No |

The ChatGPT Codex app and the Claude desktop app can work *on* this repository (they read
`AGENTS.md` and `CLAUDE.md`), on Linux or Windows. They are not sessions the monitor can
watch: the monitor reads tmux panes.

## Windows

### The Overseer app

Download `Overseer.exe` from the latest GitHub release and run it: it offers to install
itself for your user (no admin rights) with Desktop and Start Menu shortcuts. From a clone,
double-click `install.cmd` instead; it builds the same `.exe` with PyInstaller, or makes a
Desktop shortcut to `Overseer.pyw` if it cannot. `python -m overseer gui` opens the window
on any system with Python and Tk.

The window has two modes. **Build a new program**: describe what you want once, pick an
empty folder and press Build. **Continue an existing project**: pick a folder and,
optionally, what to focus on; the agent finds the unfinished work from the project's notes,
TODOs, failing tests and history. Either way Overseer runs the factory loop
(`overseer/build.py`): one fresh worker session per step, each given the objective and the
report format, until the worker reports done and `overseer_check.py`, a script the worker
writes and the factory runs itself after every step, passes. It stops early when the
worker needs you, after repeated failures, or at the step limit. While it runs you can
steer it (your message goes at the top of the next step) or ask Claude about the project in
read-only plan mode. The agent is Claude Code by default; letting it run commands, which
installing packages and running tests need, is a checkbox. Each step spends the chosen
agent's account credits.

### The rest on Windows

On native Windows the factory, the loop, and the test suite run; this is exercised by CI on
`windows-latest`. The monitor, `overseer here`, and the isolation probe need tmux or a POSIX
terminal and exit with one line that points to WSL2. A worker client installed as a native
`.exe` receives its instruction exactly as written. A client that exists only as a `.cmd` or
`.bat` shim is refused, before anything starts, whenever the instruction contains something
`cmd.exe` would interpret (a quote, `%`, `&`, a line break); use WSL2 or a native build for
those. Details: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Troubleshooting

| Symptom | What to check |
|---|---|
| `config.json` is missing, exit 1 | Copy `config.example.json` to `config.json`, or set `OVERSEER_CONFIG` |
| The log says a reply was eligible but nothing was typed | `dry_run` is `true` |
| A pane is never answered | `python3 -m overseer status`: is it `WATCHED` or `TARGETED`, not `EXCLUDED` or `OUT OF SCOPE`? Is the foreground program `claude`, `codex`, or `opencode` with an empty composer? Has the screen been idle for `idle_seconds`? Is the cooldown or daily limit reached? |
| `HALTED / PAUSED SESSIONS` in `status` | The listed reason and "Resume" line say what ends the hold; a held pane after an escalation needs `unfreeze` |
| `another monitor is already using this state file` | A monitor is already running (often the service); stop it first |
| `... is not supported on native Windows ... WSL2` | That command needs tmux; run it under WSL2 |
| A factory job failed with `refused to start ...cmd` | See Windows above |
| `needs_reconciliation` in the factory | A worker was interrupted; inspect the workspace, then `reconcile` / `resolve` |
| The client ignores a continuation | Look at the pane. The journal line `sent ...` means the line was typed, not that the client acted on it |

Screen recognition is heuristic and tied to the clients' current interfaces: a client update,
a wrapper, or another language can make Overseer miss a finished turn. It is built to miss
rather than to send wrongly. Validate against your own clients in dry-run mode first.

## Limits

- The monitor needs tmux; there is no native Windows or macOS monitor (macOS is untested).
- It cannot verify that an agent did what it reported, that a prompt-writing agent ran, or
  that work is correct. It reads the visible screen only.
- The factory runs trusted commands with your permissions. Its bubblewrap profile is a probe,
  not a sandbox around tasks. Contract fields such as risk tier and budget are recorded; most
  are not enforced.
- No real client is run by the test suite or CI, so the worker command lines for `claude` and
  `codex` are unverified, and model names in the example configuration can be out of date.
- WSL2, the ChatGPT Codex app, and the Claude desktop app were not executed for this release.
- The design documents under `docs/` describe more than is built. What is built is listed in
  [docs/HARNESS_FRAMEWORK.md](docs/HARNESS_FRAMEWORK.md).
- No licence file is included. Until the author adds one, normal copyright applies.

## Documentation

| For | Read |
|---|---|
| Every monitor and factory behaviour in detail | [docs/REFERENCE.md](docs/REFERENCE.md) |
| Setup on each platform, running tests, platform status, contributing rules | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), [AGENTS.md](AGENTS.md) |
| Factory commands and what is implemented | [docs/FACTORY_EXECUTION.md](docs/FACTORY_EXECUTION.md) |
| What exists against the design | [docs/HARNESS_FRAMEWORK.md](docs/HARNESS_FRAMEWORK.md) |
| The prompt-writing method | [promptwriting/README.md](promptwriting/README.md) |
| Development history and internal records (not user documentation; they name the author's machine) | [WORK_LOG.md](WORK_LOG.md), [docs/internal/](docs/internal/README.md) |
