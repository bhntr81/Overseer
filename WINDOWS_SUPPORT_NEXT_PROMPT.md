# TASK: Overseer imports, runs its factory and passes its suite on native Windows, carries the prompt-writing method, and is pushed to GitHub

Working directory: `/home/kali/Programming/Projects/Overseer`. Read first: `AGENTS.md`, `docs/DEVELOPMENT.md`, `.github/workflows/check.yml`.
Starting commit: `26a5be8` on `main`, clean, in sync with `origin` (https://github.com/bhntr81/Overseer.git, public).
Baseline check: `python3 scripts/check` (measured 2026-11-11 on Kali: 637 tests, OK, about 4 minutes). CI run 42863206789 for this commit is green on ubuntu-latest.

## Why this task exists
The owner asked: make Overseer usable by the ChatGPT Codex app on Windows and the Claude desktop app on Windows, add the prompt-writing project to it, and update GitHub. Today an agent in either app can clone the repository and read `AGENTS.md`, but `import overseer.factory` fails on Windows, so it cannot run the factory or the tests.

Settled, not to be reopened:
- "Usable" means: on native Windows the package imports, the factory runs, and the suite passes, with evidence from a `windows-latest` GitHub Actions job. No Windows machine is used directly.
- The tmux monitor and single-program pty mode (`overseer/local.py`) stay POSIX-only. On Windows they exit with one clear line that names WSL2, not an `ImportError`.
- The single-writer lock stays a real exclusive non-blocking lock on Windows (`msvcrt.locking`). This replaces the paragraph in `docs/DEVELOPMENT.md` that says the swap is "deliberately not attempted"; the owner's request supersedes it, on the condition that the guarantee is kept, not stubbed.
- The prompt-writing project's canonical copy stays at `/home/kali/Programming/Projects/PROMPTWRITING`; Overseer gets a snapshot.

## The work
Two increments, each landing on `main` as one commit. Work on a branch with a pull request, because CI on the pull request is the only way to see Windows results; squash-merge to get one commit without force-pushing.

### Increment 1. Native Windows support
What blocks Windows now (measured by grep at `26a5be8`):
- Top-level `import fcntl` in `overseer/__main__.py:2` (flock at 301), `overseer/factory.py:4` (flock 737-745), `overseer/orchestrate.py:24` (131), `overseer/local.py:17` (which also needs `pty`, `termios`, `tty`, `SIGWINCH`, `SIGHUP`).
- Process groups: `os.killpg` at `overseer/factory.py:781` (liveness probe, signal 0) and `:1650` (`SIGKILL`), `overseer/stopgate.py:312` (`SIGTERM`), `overseer/isolation.py:63`; children are started with `start_new_session=True`.
- `/proc` reads in `overseer/tmux.py:37`, `overseer/route.py:33`, `overseer/scheduler.py:87`; the bubblewrap probe in `overseer/isolation.py` is Linux-only by nature and `factory.py:10` imports it at top level.

A correct result:
1. A new compatibility module under 300 lines owns every platform branch: the exclusive non-blocking lock (same "another owner" failure as today, released on close and on process death), starting a child in its own group, probing whether the group is alive, and killing the whole group including grandchildren. Callers lose their `fcntl` imports and call the module. `factory.py` grows by at most 40 lines.
2. Tests come first and are frozen (SHA-256 recorded) before implementing. They must include: a second process cannot take a held lock and can after release; a killed group leaves no surviving grandchild; importing `overseer.factory`, `overseer.__main__` and `overseer.orchestrate` works without `fcntl`; the monitor and pty entry points on Windows give the one-line WSL2 message with a nonzero exit. Lock and group tests run on both systems, not only where they are easy.
3. Tests that inherently need tmux, a pty, `/proc` or bubblewrap are skipped on Windows with a stated reason. On Linux the count does not drop below the baseline and no test changes behaviour.
4. `.gitattributes` forces LF for text files and marks binaries, because skills provenance and the doc checks hash file bytes and a CRLF checkout would change them. All 117 tracked text files are LF today, so `git add --renormalize .` should change nothing; if it does, say what.
5. `.github/workflows/check.yml` gains a `windows-latest` job beside the existing one. It runs the suite through `.\scripts\check.ps1` and the doc check through `.\scripts\check-doc-references.ps1`, so the PowerShell path agents are told to use is the one with evidence. The comment in `scripts/check.ps1` about `fcntl` is corrected.
6. `docs/DEVELOPMENT.md`: platform table, the "why not supported" paragraph, the Windows, Codex and Claude workflows, and known limitations are rewritten to say exactly what ran where. Native Windows suite and factory: executed on CI `windows-latest`, with the run URL and the passed and skipped counts. Monitor and pty mode on Windows: not supported, use WSL2. The Codex Windows app and the Claude desktop app themselves: not executed; instruction files checked by inspection. `AGENTS.md` "Getting started" names both apps. File the increment against one pillar row in `docs/HARNESS_FRAMEWORK.md` (STATE holds the single-writer lock) and add a `WORK_LOG.md` entry.

The hard parts:
- The project forbids editing `tests/` while implementing, yet the first Windows CI runs will show failures nobody can predict from Linux (open-file deletion in temporary directories, `/tmp` and `/bin/sh` assumptions, path separators, missing signals). When a failure is the test's own POSIX assumption, stop implementing, return to the test phase, change the test, re-freeze and record the new hash and the reason. When the failure is product behaviour, fix the product. Do not skip a test on Windows to hide a product failure: a skip is only for the four inherent needs in item 3.
- `msvcrt.locking` locks a byte range of an open file, not the file, and the lock file is opened in append mode today; lock a fixed byte at offset 0. It is also not reentrant, like `flock`; keep the existing depth counter in `factory.py:725-745`.
- Killing only the child's PID on Windows orphans grandchildren. Use a mechanism that takes the tree (a job object, or `taskkill /T /F`), and prove it with the grandchild test.

### Increment 2. The prompt-writing method as `promptwriting/`
1. A small script (`scripts/sync-promptwriting`, stdlib, read-only on the source) copies `README.md`, `AGENTS.md`, `GUIDE.md`, `TEMPLATE.md` and `LESSONS.md` from the canonical project into `promptwriting/`. `LESSONS.md` is copied up to and including the table header and separator, with no data rows. `prompts/` is never copied: the repository is public and the archived prompts hold private details of other projects. With `--check` the script exits nonzero when the snapshot differs from what it would write, and exits 0 with a note when the canonical path is absent (CI and other machines).
2. `DESIGN.md` is not published as it stands. Its Appendix A and closing section (lines 353-394) quote findings from another private project by name. Default: leave it out, and have the snapshot's `README.md` gain one generated line saying the design record and the prompt archive are kept in the canonical project. `GUIDE.md` cites findings F1 to F11 in `DESIGN.md`; that line explains why the file is absent. Do not edit the canonical files.
3. Before committing, read the five snapshot files for anything private beyond the owner's first name and machine-local paths (both already appear in this public repository). Report what you find rather than rewriting the method.
4. Overseer's `AGENTS.md` says: the method is at the machine-local path named in the shared workflow; when that is absent, use `promptwriting/GUIDE.md` in this repository. `docs/DEVELOPMENT.md` known limitations is updated to match. A test covers the script's row stripping and `--check`.

## If Windows CI cannot be made green
After five pushed CI rounds on one failure with no new evidence, stop. Keep the Linux job required and green, leave the Windows work on the branch unmerged, and report the failing test, the trace and what was tried. Do not mark the Windows job `continue-on-error` and call it supported.

## Limits
- Never touch local `config.json` or its backups; never force-push; never grant an approval or edit a ledger by hand. These are the project's standing rules.
- Do not change lock semantics, the ledger or the approval gate on Linux; Linux behaviour is the reference the Windows path must match.
- Do not edit anything under `/home/kali/Programming/Projects/PROMPTWRITING`.
- Pushing to `main` on `origin` is authorized by the owner for these two increments only. Check `git status` shows only intended files before each commit; the repository is public.
- Stop when both increments are on `main` and CI is green. Do not start further portability work (macOS, WSL2 testing, sandboxing the runner).

## Done means
- `python3 scripts/check` and `python3 scripts/check-doc-references` pass locally; the Linux test count is 637 or more.
- `python3 scripts/sync-promptwriting --check` exits 0; `git ls-files promptwriting` lists five files and nothing from `prompts/`.
- `gh run list --branch main --limit 1` shows the run for the final `main` commit completed successfully, with both the ubuntu and the windows job green; `gh run view <id> --log` shows the Windows job's passed and skipped counts.
- `git log --oneline 26a5be8..origin/main` shows two commits; `git status -sb` is clean and level with `origin/main`.

## Report back
In the reply and in `WORK_LOG.md`, conclusion first. Give the two commit hashes, the CI run URL, and for each OS the tests run, passed and skipped (measured from the logs). List every test skipped on Windows with its reason, every test re-freeze with its reason, and anything in the snapshot you judged private. State separately what was executed and what was only inspected. Open decisions as yes/no questions, including: should `DESIGN.md` be published after its Appendix A is edited in the canonical project? End with the handoff block `AGENTS.md` requires.
