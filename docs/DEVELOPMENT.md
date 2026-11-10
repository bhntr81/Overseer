# Developing Overseer: Linux, Windows PowerShell, Codex desktop, Claude Code

One guide for every environment. The rules every agent must follow are in
[AGENTS.md](../AGENTS.md); this file says how to set up, run, and verify.
Nothing here was verified on a platform not named in its status line.

## Requirements and honest platform status

Python 3.9 or newer, standard library only (no `pip install`). Tests: no network, no API keys,
no LLM calls. The monitor additionally needs tmux.

| Environment | Status | Evidence |
|---|---|---|
| Linux (tmux installed) | Supported: the full suite and the monitor | Suite run on Kali; CI runs `python scripts/check` on ubuntu-latest |
| Windows PowerShell, native | **Not supported for the suite or the monitor** | Inferred from inspection, **not executed on Windows** (see below) |
| Windows via WSL2 | Expected to work as Linux; **not tested** | Not executed |
| Codex desktop | Works through `AGENTS.md` plus the commands below | Instruction files only; **not executed in Codex desktop** |
| Claude Code | Works through `CLAUDE.md` (points at `AGENTS.md`) | Used to develop this repository |

Why native Windows is not supported: `overseer/__main__.py`, `factory.py`, `local.py`, and
`orchestrate.py` import `fcntl`, which exists only on POSIX, so those modules cannot be imported on
Windows. They use `fcntl.flock` for the single-writer lock, `os.killpg` and `signal.SIGHUP`/`SIGWINCH`
for process control, `termios` for terminals, `/proc` for working directories, and tmux for
sessions. Swapping those out would weaken or change the single-writer lock and the monitor itself,
so it is deliberately not attempted here. The PowerShell scripts below are provided so the
workflow is the same on a PowerShell host that can import the package (pwsh on Linux or macOS, or
a Windows shell running inside WSL); the scripts themselves are plain PowerShell and
Python-interpreter discovery. They were run under `pwsh` on Linux only.

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

**Windows PowerShell.** Prefer WSL2 and follow the Linux workflow. In a PowerShell session that can
import the package, use the `.ps1` equivalents in the table. Native Windows cannot import the package
today (see above); `check.ps1` will run and the suite will fail at import, which is the honest result.

**Codex desktop.** Open the repository root: Codex reads `AGENTS.md` there, which links to this
file. Inspect with `git status` and `git log --oneline -5`; run one module with the one-test command
above, then the full sequence; review with `git diff`. Codex's Windows environment has the same
native-Windows limits as above; use its WSL or a Linux workspace for runs. Use argument lists, not
shell strings, for subprocesses. Commit only when the task says so.

**Claude Code.** `CLAUDE.md` imports `AGENTS.md`; the workflow is the same.

## Known limitations

- Native Windows: not supported (above). Not executed on any Windows host.
- Codex desktop: not executed; the instruction files and commands were checked by inspection.
- The factory's argument-vector runner is not itself sandboxed; the bubblewrap profile only probes.
- `AGENTS.md` refers to the author's private playbook path outside this repository; on another
  machine that file is absent, and the instructions say to report that rather than invent it.
