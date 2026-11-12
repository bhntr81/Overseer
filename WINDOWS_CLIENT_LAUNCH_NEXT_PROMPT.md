# TASK: On native Windows a worker's instruction reaches the client exactly as written, or the job is refused before it starts

Working directory: `/home/kali/Programming/Projects/Overseer`. Read first: `AGENTS.md`,
`docs/DEVELOPMENT.md` ("Limits of the Windows path"), `overseer/hostos.py`, `overseer/provider.py`.
Starting commit: `3c21beb` on `main`, level with `origin` (https://github.com/bhntr81/Overseer.git, public).
Baseline: `python3 scripts/check` on Linux, 665 run, 664 passed, 1 skipped; windows-latest 657 run,
639 passed, 18 skipped (both reported for CI run 43170875858, not rechecked by the prompt writer).

## Why this task exists
John's goal is an Overseer that an agent in the ChatGPT Codex app or the Claude desktop app can use
on Windows. The last increment made the package, the factory, the loop and the suite run there. What
still stands between that and a loop that drives a real client on Windows is the last hop: starting
the client and handing it the instruction. Worker clients on Windows are commonly installed as
`.cmd` shims, for example by a global npm install (assumed; no Windows machine was checked). On
that path three things are wrong, and they share one cause:

1. **Not found.** `provider.py` puts a bare name (`opencode`, `claude`, `codex`; lines 28, 124, 133)
   first in the argument list, and the Windows launcher runs it with
   `subprocess.call(sys.argv[1:])` (`overseer/hostos.py:44`). Windows adds only `.exe` to a bare
   name, so a client that exists on `PATH` only as `opencode.cmd` is not found (assumed, not run).
2. **Line breaks.** A `.cmd` file cannot receive an argument that contains a line break (measured in
   the last increment; the test is skipped at `tests/test_loop.py:143`). With `--size`, the loop
   always sends one: `overseer/orchestrate.py:243` builds `brief + '\n\n' + instruction`.
3. **Interpretation.** Windows starts a `.cmd` file through `cmd.exe`, and Python adds no escaping
   for it (Python `subprocess` documentation, security note on batch files; not run here). The
   instruction is text a model wrote: the previous worker's `NEXT_AGENT_INSTRUCTION`. A `"` in it
   ends the quoting, after which `&`, `|` and `>` are commands, and `%NAME%` is expanded even
   inside quotes. The docstring at `overseer/provider.py:57` says "a shell is never used, so the
   instruction cannot be split or interpreted"; on this path that is not true. The existing test
   passes on Windows only because its instruction has no `"` and no `%` (`tests/test_provider.py:70`).

Settled, not to be reopened: the tmux monitor and `overseer here` stay POSIX-only; platform code
goes in `overseer/hostos.py` (218 lines; 300 is the limit) or a module it owns, as `winjob.py` is;
Linux behaviour is the reference; Windows evidence comes from the `windows` CI job, on a pull request.

## The work
One increment, one commit on `main`. A correct result:

1. On Windows a client named without a path is found the way the user's shell finds it (`PATHEXT`),
   and a client that is not installed fails with one line that names it.
2. For every text `provider._require_instruction` accepts, the instruction reaches the client as one
   argument, byte for byte, or the job is refused before any child process starts, with one line
   that says why and what to install instead. It never arrives altered and is never parsed by
   `cmd.exe`. For a `.cmd` or `.bat` client, delivering or refusing is your choice; give the reason.
   Delivering is allowed only by a route that does not put the text on a `cmd.exe` command line (a
   client that reads its prompt from standard input or a file would be one; check the client's own
   help before relying on it, nothing about that is verified here).
3. The rule sits where the command is started, so it also covers a task's `implementation` and
   `checks` from a spec, which reach the same launcher (`overseer/factory.py:1602`).
4. Tests first, frozen with their SHA-256 before implementing. On Windows they must show: an
   instruction with a line break, one with `" & echo` writing a marker file, and one with `%PATH%`
   each arrive exactly or are refused with no child started; the marker file does not exist
   afterwards; a client present only as `.cmd` is found by its bare name. On Linux the same three
   texts arrive exactly. The skip at `tests/test_loop.py:143` is removed, or its reason is restated
   to say what now happens.
5. `docs/DEVELOPMENT.md` (the limit bullet, the skip list, the counts and run link), the docstring at
   `provider.py:57`, one pillar row in `docs/HARNESS_FRAMEWORK.md` (TOOLS holds safe execution), and
   a `WORK_LOG.md` entry say what is now true.

The hard parts:
- Escaping the text for `cmd.exe` (carets, doubled quotes) looks like the fix and is not. A line
  break cannot be escaped at all, and `cmd.exe` and the program it starts parse the line by
  different rules, which is how this class of fault arose in other runtimes (CVE-2024-24576).
- The Windows fake workers in `tests/test_loop.py:50-55` and `tests/test_provider.py:66-69` are
  `.cmd` starters. If `.cmd` clients are refused, those fakes need another form. That is a test
  change: make it in the test phase and record it with the re-freeze.

## If a premise turns out false
The first CI round, with the new tests red, measures premises 1 and 3. If the bare name is found, or
the injected command does not run and the text arrives intact, keep the test, cite the log line in
the report, and drop that part. If CI cannot tell which holds, stop and report the output.

## Limits
- Do not install or call a real client: the suite has no network and no paid calls. The flags in
  `_claude_argv` and `_codex_argv` stay "unverified here"; report them as not executed.
- `factory.py` takes at most 40 new lines; new logic in a module under 300 lines.
- Pushing a branch, opening a pull request and squash-merging it to `main` is authorized for this
  one increment, because CI on the pull request is the only source of Windows results. Check that
  `git status` shows only intended files before the commit; the repository is public.
- Stop after five pushed CI rounds on one failure with no new evidence: leave the branch unmerged
  and report the test, the trace and what was tried.
- Stop when the commit is on `main` and CI is green. Not part of this task: the lingering
  grandchild limit, WSL2, a new way of passing instructions on Linux, and publishing `DESIGN.md`,
  which waits for John's yes or no.

## Done means
- `python3 scripts/check` and `python3 scripts/check-doc-references` pass locally; Linux runs 665
  tests or more.
- `gh run list --branch main --limit 1` shows the run for the final commit successful on both jobs;
  its Windows log shows the new tests ran (not skipped) and at most 18 skips.
- `git log --oneline 3c21beb..origin/main` shows one commit; `git status -sb` is clean.

## Report back
In the reply and in `WORK_LOG.md`, conclusion first: for a `.cmd` client, delivered or refused, and
why. Then the commit, the CI run link, and tests run, passed and skipped per system from the logs.
Say for each of the three premises whether CI confirmed it. List every test re-freeze with its
reason. Keep executed apart from inspected. Open decisions as yes/no questions. Also save a copy of
this prompt in the canonical `PROMPTWRITING/prompts/`, open its `LESSONS.md` row, and fill the open
row for `WINDOWS_SUPPORT_NEXT_PROMPT.md` from the last report. End with the handoff block
`AGENTS.md` requires.
