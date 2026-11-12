# Developing Overseer: Linux, Windows, the Codex app, Claude Code and the Claude desktop app

One guide for every environment. The rules every agent must follow are in
[AGENTS.md](../AGENTS.md); this file says how to set up, run, and verify.
Nothing here was verified on a platform not named in its status line.

## Requirements and honest platform status

Python 3.9 or newer, standard library only (no `pip install`). Tests: no network, no API keys,
no LLM calls. The monitor additionally needs tmux.

| Environment | Status | Evidence |
|---|---|---|
| Linux (tmux installed) | Supported: the full suite, the factory, and the monitor | Suite run on Kali; CI job `tests` on ubuntu-latest |
| Windows, native (PowerShell) | Supported: the package, the factory, the loop, and the suite. **Not supported: the tmux monitor and `overseer here`** | CI job `windows` on windows-latest runs `.\scripts\check.ps1` and `.\scripts\check-doc-references.ps1`: 647 tests run, 629 passed, 18 skipped, and 271 document references checked, in [run 43168733243](https://github.com/bhntr81/Overseer/actions/runs/43168733243) (2026-11-12, Python 3.15); the ubuntu job of the same run: 655 run, 654 passed, 1 skipped |
| Windows via WSL2 | Expected to work as Linux, monitor included; **not tested** | Not executed |
| ChatGPT Codex app on Windows | Works through `AGENTS.md` plus the PowerShell commands below | Instruction files checked by inspection; the commands it is told to run are the ones the `windows` CI job runs. **Not executed inside the app** |
| Claude desktop app on Windows (Code tab) | Works through `CLAUDE.md` (imports `AGENTS.md`) plus the same commands | Same as above. **Not executed inside the app** |
| Claude Code on Linux | Works through `CLAUDE.md` | Used to develop this repository |

What native Windows runs, and how. `overseer/hostos.py` is the one module that branches on the
operating system (its Windows job-object calls are in `overseer/winjob.py`); no other module
names `fcntl` or `killpg`.

| Need | POSIX | Native Windows |
|---|---|---|
| Single-writer lock (factory database, loop ledger) | `fcntl.flock`, exclusive, non-blocking | `msvcrt.locking` on byte 0 of the lock file, exclusive, non-blocking. The same refusal for a second owner; released on close and on the owner's death |
| A task's processes as one group | a new session; `killpg` | a job object named after the child's pid; every descendant joins it and one call ends them all |
| Is an interrupted task's group still alive | `killpg(pid, 0)` | the job is opened by name and its live-process count is read |
| Bounded read of a task's output | `select` on the pipe | a reader thread behind the same calls |
| Gated launcher | `exec` of the command | the launcher stays as the parent and passes the exit status through |

What native Windows does not run: `overseer run`, `status`, `watch`, `unwatch`, `start`, `here`, and
`model-select`. They drive tmux panes or a pty (`termios`, `/proc`, `SIGWINCH`), which Windows does
not have. Each exits 1 with one line that names WSL2; none raises an `ImportError`. The bubblewrap
isolation probe is Linux-only. Use WSL2 for all of these.

Tests skipped on Windows, each with its reason in the test: the monitor command line (`run`,
`status`; 5 tests), the pty mode (`tests/test_local.py`, the whole module), `/proc` and POSIX pane
scope (3), the bubblewrap probe (4), the live tmux transport (1), a file name that is not Unicode
(1), and the loop's multi-line step brief through a `.cmd` fake worker (1 test in 3 classes).

Limits of the Windows path, stated plainly:

- A job object keeps its name only while a handle to it is open. The controller holds one and the
  gated launcher holds another, so a task whose controller crashed is still found by `resolve`. A
  launcher that starts after its controller has already died cannot open the job and exits 125
  without running the task. If the controller dies **and** the task's own command has exited while
  a grandchild lingers, that grandchild is no longer found; on Linux it is.
- A task killed on timeout reports the exit status Windows gives a terminated process, not `-9`.
- A task command must be something `CreateProcess` can start: an `.exe`, or a `.cmd`/`.bat` file.
  A script with only a shebang line is not runnable; name the interpreter in the argument list.
  A `.cmd` file cannot receive an argument that contains a line break, so a worker client that is
  installed as a `.cmd` shim does not get the loop's multi-line step brief intact.

## Configuration: public example, local file

| File | Tracked? | Purpose |
|---|---|---|
| `config.example.json` | yes | Safe template: `dry_run: true`, nothing watched, stop agent off |
| `config.json` | **no, git-ignored** | Your local configuration; read by the monitor every poll |
| `config.json.bak*` | **no, git-ignored** | Your local backups |

First-time setup (never overwrites an existing `config.json`):

```sh
# Linux / macOS / WSL
[ -e config.json ] || cp config.example.json config.json
```

```powershell
# PowerShell
if (-not (Test-Path config.json)) { Copy-Item config.example.json config.json }
```

Overseer only reads `config.json`; it never creates or replaces it. To use a file elsewhere (a CI job, a second
checkout, a Codex workspace), set `OVERSEER_CONFIG` to its path (bash: `export OVERSEER_CONFIG=/path/mine.json`;
PowerShell: `$env:OVERSEER_CONFIG = 'C:\path\mine.json'`); unset or empty means `<repo>/config.json`. The override
only chooses the path. With no `config.json`, a command
that needs it exits 1 and the error names `config.example.json`. Required fields: `poll_seconds`,
`idle_seconds`, `cooldown_seconds`, `max_per_day` (positive integers) and `dry_run` (boolean).
Optional, with defaults: `continue_on_completion`, `serial_queue`, `capacity_retry_seconds` (120),
`capacity_max_retries` (3), `exclude`, `targets`, `target_paths` (relative entries resolve against
the directory that holds `config.json`), `reply`, `model_providers`, `allowed_providers`,
`fallback_policy`, `usage_winddown_percent`, `stop_agent`. Field behavior is documented in
[README.md](../README.md). Tests never read your `config.json`; they use `config.example.json`.

`config.json` and an older backup were committed to this repository's history before this
separation; they hold no credentials, but they do show one author's session names and paths.
They are no longer tracked; the history was not rewritten.

## Run the tests

From the repository root. `scripts/check` runs the whole suite with tmux isolated in a temporary
directory, so it never touches your live tmux server. Do not run bare `python -m unittest` while
your own tmux sessions exist.

| Task | Linux / macOS / WSL | PowerShell |
|---|---|---|
| Full suite | `python3 scripts/check` | `.\scripts\check.ps1` |
| Doc references | `python3 scripts/check-doc-references` | `.\scripts\check-doc-references.ps1` |
| One test module | `TMUX_TMPDIR="$(mktemp -d)" python3 -B -m unittest tests.test_config_separation` | `$env:TMUX_TMPDIR = (New-Item -ItemType Directory (Join-Path ([IO.Path]::GetTempPath()) "ov$(Get-Random)")).FullName; python -B -m unittest tests.test_config_separation` |

Choose an interpreter explicitly with `OVERSEER_PYTHON` or `check.ps1 -Python <path>`;
`check.ps1 -ResolveOnly` prints what it would use. Exit codes are preserved: 0 pass, nonzero fail,
2 for no interpreter or a missing document.

## Mandatory sequence for every increment

1. Red-Green separation: write the tests first and freeze them (record their SHA-256); do not edit `tests/` while implementing.
2. Implement. New logic goes in new modules under 300 lines; `factory.py` takes at most +40 lines.
3. `python3 scripts/check`, then `python3 scripts/check-doc-references`: both must pass.
4. One commit for the increment. Commit and push only when the task authorizes it. Never force-push.

## Integrity guarantees an edit must not weaken

- **SQLite ledger**: jobs, immutable submissions, approvals, memory records, sealed digests. Do not
  edit a ledger by hand and do not write around the factory's own methods.
- **Approval gate**: a task that needs a decision stays `awaiting_approval` until
  `python3 -m overseer.factory decide <id> --decision granted --decider NAME` records a grant.
  Never grant on the operator's behalf.
- **Single-writer lock and controller epoch**: one factory worker owns a database; backup and
  restore fence under a fresh epoch so a stale lease cannot publish.
- **Sealed digests, diff receipts, handoff records**: written per attempt; reconcile with
  `python3 -m overseer.factory reconcile-handoff <id>` (read-only: it reports disagreements and
  never resolves them).

## Environment workflows

**Linux terminal.** Clone, `cp config.example.json config.json`, `python3 scripts/check`. To run
the monitor see "Background service" in the README; start with `dry_run: true`.

**Windows PowerShell.** Install Python 3.9+ (the `py` launcher or `python` on `PATH`) and Git for
Windows. Clone, `Copy-Item config.example.json config.json` if you have none, then
`.\scripts\check.ps1` and `.\scripts\check-doc-references.ps1`. The factory runs natively:
`py -3 -m overseer.factory --db <path> ...`. `.gitattributes` keeps every text file LF on checkout;
do not convert line endings, because skills provenance and the document checks hash file bytes. For
the monitor, use WSL2 and follow the Linux workflow.

**ChatGPT Codex app on Windows.** Open the repository root as the workspace: Codex reads
`AGENTS.md` there, which links to this file. With the agent running natively (PowerShell), use the
PowerShell column of the table above; with the agent running in WSL, use the Linux column. Inspect
with `git status` and `git log --oneline -5`; run one module with the one-test command, then the
full sequence; review with `git diff`. Use argument lists, not shell strings, for subprocesses.
Commit only when the task says so.

**Claude desktop app on Windows (Code tab).** Open the repository folder. `CLAUDE.md` imports
`AGENTS.md`, so the instructions are the same ones Codex reads. The app's shell on Windows is Git
Bash or PowerShell: in Git Bash run `python scripts/check` and `python scripts/check-doc-references`
(or `py -3` in place of `python`); in PowerShell run the `.ps1` scripts.

**Claude Code (terminal).** `CLAUDE.md` imports `AGENTS.md`; the workflow is the same on each system.

**The prompt-writing method.** `AGENTS.md` sends project work through a prompt-writing role whose
method lives in this repository, [promptwriting/GUIDE.md](../promptwriting/GUIDE.md). That directory is
the project itself, on every machine. The design record (`DESIGN.md`) and the prompt archive
(`prompts/`) exist only on the author's machine and are git-ignored, because they quote other,
private projects.

## Known limitations

- Native Windows: the monitor, `overseer here`, and the isolation probe are not supported (above).
  The suite and the factory were executed on CI `windows-latest` only, not on a desktop machine.
- The Codex app and the Claude desktop app: not executed; their instruction files and the commands
  they are told to run were checked by inspection and, for the commands, by the `windows` CI job.
- The factory's argument-vector runner is not itself sandboxed; the bubblewrap profile only probes.
- `AGENTS.md` refers to the author's private playbook path outside this repository; on another
  machine that file is absent, and the instructions say to report that rather than invent it. The
  prompt-writing method is the exception: it lives in `promptwriting/`, without the design
  record and the prompt archive, which stay on the author's machine.
