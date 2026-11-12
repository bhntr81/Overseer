# Capture the workspace diff of an attempt as a patch receipt

Status: **ready to execute once the skills-provenance increment is
committed**. This prompt was written by the dedicated prompt-writing agent of
the Overseer project. The primary agent executes it; writing it is not
completion.

The user's request, verbatim:

> Focus exclusively on the Overseer project in this current workspace.
> Implement workspace diff and patch receipt capture for the CONTEXT and
> EVIDENCE pillars in the factory: 1. Update the run execution and manifest
> pipeline so that the exact git diff (patch) of any changes made to the
> workspace during an attempt is automatically captured and stored in the run
> evidence directory (e.g., as `diff.patch`). 2. Record diff statistics,
> modified file lists, and path summaries in the context manifest. 3. Add
> comprehensive unit tests in tests/test_factory.py covering diff capture,
> patch generation, and manifest integration. 4. Run python3 scripts/check and
> python3 scripts/check-doc-references to ensure 100% test pass rates and valid
> citations, update WORK_LOG.md, and commit clean.

## Which pillar row this is filed against

`AGENTS.md` requires exactly one row. The user names CONTEXT and EVIDENCE.
This increment is filed against **EVIDENCE**
(`docs/HARNESS_FRAMEWORK.md:36`). A patch of what an attempt changed is a
receipt of the attempt's result, which is the verification record the
blueprint asks for: "Record source tree/commit, … actual command, exit status,
result, and evidence digest" (`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:311`).
CONTEXT is touched only where the manifest must stay honest: the manifest gets
a `workspace_diff` block, and `candidate_revision` leaves the `unmeasured`
list only for an attempt where it was actually observed (section 6). The
CONTEXT row's verdict and its "Next increment" cell are not changed; only its
citations are re-derived where lines move.

## Precondition: start from the skills commit

This prompt was written against the **uncommitted** skills-provenance working
tree (310 tests, 166 references), which is still under review.

1. `git status --short` prints only `?? EVIDENCE_WORKSPACE_DIFF_NEXT_PROMPT.md`,
   and `HEAD` is the skills-provenance commit the coordinator names. Otherwise
   stop and report `needs_input`. Do not fold the skills changes into this
   commit.
2. Re-run both baseline commands and use their counts in place of 310 / 166.
3. **Re-measure every line reference below** against that commit.

Review lessons carried forward, part of the acceptance:

1. **Line citations drift.** Re-derive every citation by hand after the last
   edit, in every row and passage the increment touches.
2. **A test is evidence only if a plausible wrong implementation fails it.**
   Run the mutations of section 9 one at a time; show the suite failing; name
   the failing test; revert.
3. **Counts describe what is shown.** Insertions and deletions count the lines
   in `diff.patch`; files whose content was withheld or omitted are counted
   apart, with the reason, and the stats say they are incomplete.
4. **Evidence is scoped to this attempt.** A change that was in the workspace
   before the attempt started is never attributed to the attempt.
5. **Words claim only what was observed.** The patch is what the commands left
   in the workspace, as seen by the controller; it is not proof that the
   implementation command alone made it, and not a review.

## What "the changes made during an attempt" means

- **Before** = a snapshot taken immediately before the implementation command
  starts, after the map and skills are assembled.
- **After** = a snapshot taken immediately after the implementation command
  returns, whether it passed, failed, or timed out.
- **The attempt's change** = every path whose state differs between before and
  after. `diff.patch` is the patch from the before state to the after state of
  those paths, and nothing else.
- **After the checks**, a third, status-only comparison: any path the
  acceptance commands changed further is listed as `changed_by_checks` (path
  and status only, no second patch), because checks should not change the
  candidate and a reader must be able to see that they did.
- **Pre-existing changes** (dirty tracked files and untracked files present at
  before) are not part of the attempt. A pre-existing path the attempt did not
  touch is listed only in a bounded `pre_existing` summary (count and paths).
  A pre-existing path the attempt changed further is diffed against its
  **before** content, not against `HEAD`, so the user's own edit is not in the
  patch.

## Repository and paths

- Repository: `/home/kali/Programming/Projects/Overseer`, branch `main`.
- Python 3 standard library only. `git` is required for capture but its
  absence is a recorded reason, not a failure. Measured with git 2.53.0.

Measured on the uncommitted skills tree; re-measure (precondition 3):

| Path and line | What it is now |
| --- | --- |
| `overseer/factory.py:309` | `_run_git(workspace, *arguments)`: read-only git with a 10 s timeout, no env control |
| `overseer/factory.py:324` | `repository_identity(workspace)`: root and `base_commit` at attempt start |
| `overseer/factory.py:1263` | the manifest's `'unmeasured'` list (contains `candidate_revision`) |
| `overseer/factory.py:1313` | `execute(job_id, argv, cwd, timeout, log, env)` |
| `overseer/factory.py:1926` | `run_one` |
| `overseer/factory.py:2011` | the mode branches: `isolation_probe`, `fake_provider`, `fixture`, then the command loop at 2030 |
| `overseer/factory.py:2034` | the `execute(...)` call; `index == 0` is the implementation command |
| `overseer/factory.py:2048` | `summary = {...}` |
| `overseer/factory.py:2059` | the `_context_manifest(...)` call; `context.json` next |
| `overseer/codemap.py:166` | `is_secret(path)`: the secret-name rule to reuse |
| `tests/test_factory.py:1274` | `class ContextTests`; the `git(...)` helper at 1335; a git workspace is built at 1401 |
| `docs/HARNESS_FRAMEWORK.md:36` | the EVIDENCE row |
| `docs/HARNESS_FRAMEWORK.md:94` | "Token and cost fields are null and are never estimated." (the does-not-claim list) |
| `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:311` | the verification record sentence |
| `README.md:45` | "Software factory direction"; the evidence-file paragraphs at 56–111 |
| `WORK_LOG.md:2603` | the skills entry; the file ends at 2679 |

## Required behavior

### 1. A read-only module

Add `overseer/workdiff.py`, in the style of `overseer/codemap.py` and
`overseer/skills.py`:

```python
def snapshot(workspace):
    """Record the state of a git workspace without changing it. ..."""

def capture(before, workspace):
    """Return (patch_text, receipt) for what changed since the snapshot. ..."""

def changed_since(after, workspace):
    """Return the paths whose status changed since a snapshot, status only. ..."""
```

It imports `is_secret` from `overseer.codemap` and nothing from
`overseer.factory`. No function raises for a workspace problem: each returns a
dict with `captured: False` and the reason.

### 2. Git is run read-only, with nothing external

One private runner for every git call in the module:

- argv form only, `['git', '-C', workspace, <options>, <command>, ...]`, no
  shell, `timeout=10`, stdout as bytes, output capped at
  `MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024` (a larger output is a recorded
  reason, not a partial read presented as whole);
- environment: a copy of `os.environ` with `GIT_OPTIONAL_LOCKS=0` (so
  `git status` does not refresh and rewrite the index), `GIT_TERMINAL_PROMPT=0`,
  `GIT_PAGER=cat`, `PAGER=cat`, `GIT_CONFIG_NOSYSTEM=1`, `LC_ALL=C`;
- options: `-c core.quotepath=off -c core.fsmonitor=false
  -c core.untrackedCache=false -c color.ui=false` (an fsmonitor hook would run
  a program; the untracked cache could be written).

The only git commands allowed: `rev-parse --show-toplevel`, `rev-parse
--verify -q HEAD`, `status --porcelain=v1 -z --untracked-files=all
--no-renames`, `ls-files -s -z -- <path>` (mode), and `cat-file blob
<commit>:<path>` / `cat-file -s` (size first). **Never** `add`, `add -N`,
`stash`, `checkout`, `reset`, `commit`, `update-index`, `apply`, `diff` with
an external driver, or anything that writes. A test proves `.git/index`,
`.git/HEAD`, and every ref are byte-identical after a run.

### 3. The snapshot

`snapshot(workspace)` records:

- `root` (`rev-parse --show-toplevel`), `head` (`rev-parse --verify -q HEAD`,
  `None` in a repository with no commit, which is recorded, not an error);
- the parsed porcelain status: per path, its two status letters;
- for every path that is dirty or untracked at before, its **before content**
  held in memory only (never written to disk): file type (regular, symlink,
  missing), mode, size, SHA-256, and the bytes when the file is regular, not
  secret-named, at most `MAX_FILE_BYTES = 256 * 1024`, and the running total
  stays within `MAX_BEFORE_BYTES = 8 * 1024 * 1024`; otherwise the bytes are
  not kept and the reason is recorded (`secret_name`, `too_large`,
  `before_budget`);
- `captured: False` with the reason for: no workspace, not a directory, git
  not available, not a git work tree, git timed out, output over the bound.

The workspace subdirectory case: when the workspace is a subdirectory of the
repository, only paths under the workspace are considered (`git -C workspace
status` reports paths relative to the top; filter to the workspace prefix and
record paths relative to the workspace).

### 4. The capture

`capture(before, workspace)` takes a new status at after and decides the
changed paths: a path is changed when its status letters differ, or when it is
dirty or untracked at both times and its type, mode, or SHA-256 differs.
Untracked files are included (they come from `--untracked-files=all`, so the
index is never touched). Ignored files are not seen; the receipt says so.

For each changed path, in path order, up to `MAX_DIFF_FILES = 200`:

- **before side**: a pre-existing dirty or untracked path uses its held before
  bytes (or is `withheld_pre_existing` when they were not held); a path clean
  at before uses `cat-file blob <before head>:<path>` when it exists there
  (size checked first with `cat-file -s`); otherwise it is absent;
- **after side**: the worktree file, size checked with `os.lstat` before
  reading; a symlink is recorded as `symlink` and its target is not read or
  recorded;
- **status**: `added`, `modified`, `deleted`, `type_changed`, or
  `mode_changed`. Renames are recorded as a delete and an add; the receipt says
  rename detection is not done;
- **content**: `in_patch`, or withheld with the reason: `secret_name` (path
  listed, no content, **no hash**), `binary` (NUL byte or not UTF-8; both
  SHA-256 recorded), `too_large`, `symlink`, `withheld_pre_existing`,
  `omitted_by_bound` (section 5).

The patch of a text file is a git-style unified diff generated in Python with
`difflib.unified_diff(n=3)`: `diff --git a/<p> b/<p>`, `new file mode` /
`deleted file mode` / `old mode` + `new mode` lines where they apply,
`--- a/<p>` or `--- /dev/null`, `+++ b/<p>` or `+++ /dev/null`, the hunks, and
`\ No newline at end of file` where a side lacks a final newline. It must
apply: a test runs `git apply --check` and then `git apply` in a **separate
temporary copy** of the before state and compares the bytes with the after
state. This is the "exact" in the user's request: the patch reproduces the
after bytes of every `in_patch` file.

If HEAD moved between before and after (the attempt committed), the before side
of a path clean at before is still the **before** HEAD's blob, so commits made
by the attempt are inside the patch; the receipt records `head_before`,
`head_after`, and `head_moved: True`.

### 5. Bounds, and what the counts mean

Module constants, all recorded in the receipt's `limits`:
`MAX_GIT_OUTPUT_BYTES`, `MAX_FILE_BYTES`, `MAX_BEFORE_BYTES`,
`MAX_DIFF_FILES = 200`, `MAX_PATCH_BYTES = 1024 * 1024`,
`MAX_PATH_CHARS = 1024` (a longer path is listed truncated with
`path_truncated: True` and its content withheld), `MAX_LISTED = 200`
(list lengths in the manifest), `MAX_PRE_EXISTING_LISTED = 50`.

The patch is built file by file; a file's patch that would take the total past
`MAX_PATCH_BYTES` is not started (never cut mid-hunk), and it and every later
file are `omitted_by_bound`. Changed paths beyond `MAX_DIFF_FILES` are counted
in `files_beyond_bound`, not listed.

The receipt's `stats`: `files_changed` (all changed paths seen),
`files_in_patch`, `files_withheld` (by reason), `files_omitted`,
`insertions` and `deletions` (lines of the `in_patch` files only),
`complete` (`True` only when every changed file is `in_patch`),
`patch_bytes`, `patch_sha256`. `files_changed == files_in_patch +
sum(files_withheld.values()) + files_omitted + files_beyond_bound`.

`paths`: the changed paths grouped by their top-level directory under the
workspace (`.` for the top), sorted, each with a count.

### 6. How it reaches the evidence and the manifest

In `run_one`, command mode only:

- `before = snapshot(spec['workspace'])` immediately before the implementation
  command;
- after the implementation command returns (any exit, timeout included):
  `patch, receipt = capture(before, workspace)`;
- after the loop ends: `receipt['changed_by_checks'] = changed_since(after,
  workspace)` (bounded list, status only), when at least one check ran;
- write `diff.patch` (the patch, possibly empty, always written when
  `captured`) and `diff.json` (the receipt; `patch_sha256` is the SHA-256 of
  the bytes of `diff.patch`) into the evidence directory; record an event
  `workspace_diff` with the counts or the reason;
- `summary['workspace_diff'] = {'path': …, 'sha256': <of diff.json>,
  'patch_path': …, 'patch_sha256': …}`;
- pass the receipt to `_context_manifest` as a new keyword
  `workspace_diff=None`.

Capture never changes the attempt's outcome. A capture problem — not a git
repository, git missing, timeout, any `OSError` or `ValueError` inside the
module — is recorded as `captured: False` with the reason, and the attempt
runs and is judged exactly as before. No `diff.patch` is written then.

Modes: `fixture`, `fake_provider`, and `isolation_probe` run in the evidence
directory, not a workspace. Their manifest block is `{'captured': False,
'reason': 'the <mode> mode runs in the evidence directory, not a workspace'}`
and no `diff.patch` is written.

The manifest's `workspace_diff` block: `captured`, `reason`, `path`,
`sha256`, `patch_path`, `patch_sha256`, `head_before`, `head_after`,
`head_moved`, the `stats`, `paths`, the per-file list (bounded by
`MAX_LISTED`: `path`, `status`, `content`, `insertions`, `deletions`),
`pre_existing` (count and bounded paths), `changed_by_checks`, and a `note`:
"the patch is what the workspace held after the implementation command,
compared with its state at the start of the attempt; changes present before
the attempt are not included; ignored files are not seen; renames are not
detected."

`candidate_revision`: when `head_moved` is `True`, the manifest records
`candidate_revision: <head_after>` with the source "git rev-parse HEAD after
the implementation command; HEAD moved during the attempt", and
`candidate_revision` is removed from `unmeasured` for that manifest only. When
HEAD did not move, the worktree is not a revision: `candidate_revision` stays
in `unmeasured`, and the manifest says why. The manifest `version` stays `1`;
the `supplied` list is unchanged.

### 7. What stays true

- The workspace, its index, its HEAD, and its refs are never written.
- Pre-existing content is held in memory and never written to the evidence
  except as context lines of a file the attempt itself changed.
- A secret-named path's content and hash never reach `diff.patch`,
  `diff.json`, the manifest, or an event.
- The verifiers, receipts, publish gate, and states are unchanged: the diff
  informs a reader; nothing judges the attempt by it.

### 7a. Lessons from the skills-provenance review (c1c9637)

That review found an exception escaping a reader and leaving the dispatch
transaction open, so the job stayed queued. Apply the same fixes here:

- **Catch-all around capture in `run_one`.** Each of `snapshot`, `capture`,
  and `changed_since` is called inside a guard that turns *any* exception into
  `captured: False` with the reason `the workspace diff could not be captured:
  <ExceptionType>`. Only the type name goes into the reason, never the message,
  which may carry a path or content. Use a helper like `skills.unchecked()`.
  The run then continues and is judged as before. Test it by patching
  `capture` to raise `RuntimeError`: the job reaches its normal final state and
  is not left `running` or `queued`.
- **Paths that are not UTF-8.** Paths come from `-z` output as bytes. Decode
  them with `errors='surrogateescape'`. A path that does not round-trip to
  UTF-8 is listed as `path_not_utf8` (shown with `backslashreplace`), and its
  content is withheld. Never write a lone surrogate into `diff.patch`, and
  write the patch as UTF-8 bytes. Test it with a file named `b'caf\xe9.txt'`.
- **Every format check uses `re.fullmatch`**, so a trailing newline cannot
  pass `$`.
- **Reads are bounded**: `read(MAX + 1)` after `lstat`, and anything larger
  is `too_large`.

Add two mutations to section 8's list: **M15** the `run_one` guard removed (a
raising `capture` fails the run or leaves it stuck), and **M16** a non-UTF-8
path written into the patch (writing raises, or the bytes do not round-trip).

### 8. Tests

Add tests to `tests/test_factory.py` (a new `class WorkspaceDiffTests`, using
the `git` helper pattern of `tests/test_factory.py:1335`, a temporary git
repository with a committed base, and `Factory(self.db, ...)`).

1. An attempt that modifies a tracked file, adds an untracked file, and deletes
   a tracked file: `diff.patch` lists all three with the right statuses; stats
   match the patch; `git apply` in a copy of the before state reproduces the
   after bytes.
2. A file without a final newline, edited: the patch carries `\ No newline at
   end of file` and applies.
3. Pre-existing edit not attributed: a dirty tracked file and an untracked file
   present before the attempt and untouched by it are absent from the patch and
   listed in `pre_existing`; a pre-existing dirty file the attempt edits again
   is diffed against its before content (the user's edit is not in the patch's
   `-`/`+` lines; the patch applies to the before state).
4. Commit by the attempt: the implementation commits a change; `head_moved` is
   `True`, the committed change is in the patch, `candidate_revision` equals the
   new HEAD and is not in `unmeasured`. Without a commit, `candidate_revision`
   stays in `unmeasured`.
5. Binary file and symlink: `content` `binary` (hashes recorded, no bytes in
   the patch) and `symlink` (target not recorded).
6. Secret-named file `config/secrets.json` written by the attempt with
   `UNIQUE_SECRET_VALUE`: path listed with `secret_name`, the value and any
   hash of it absent from `diff.patch`, `diff.json`, `context.json`, and the
   events.
7. Bounds: a file over `MAX_FILE_BYTES` is `too_large`; patches that pass
   `MAX_PATCH_BYTES` stop at a file boundary with later files
   `omitted_by_bound`, `complete` `False`, and the count identity of section 5
   holds; more than `MAX_DIFF_FILES` changed files gives `files_beyond_bound`.
8. Read-only: `.git/index`, `.git/HEAD`, and `git for-each-ref` output are
   byte-identical before and after a run in which the attempt changes only
   worktree files; `git stash list` is empty.
9. Not a git workspace (the existing `self.root` style): the run's state is
   unchanged from today, `diff.json` records `captured: False` with the reason,
   and no `diff.patch` exists.
10. Fixture, fake-provider, and isolation-probe runs: the manifest block says
    the mode runs in the evidence directory; no `diff.patch`.
11. A failing or timed-out implementation still captures its changes.
12. `changed_by_checks`: a check that writes a file is listed there, and that
    file is not in `diff.patch`.
13. Determinism: two `capture` calls over the same before snapshot and the
    same workspace give identical patch bytes and receipts.
14. The manifest's `workspace_diff` block matches `diff.json`, and
    `summary.json`'s digests match the files.

Mutations — one at a time, show the suite failing, name the failing test,
revert:

- M1 the before snapshot is dropped and paths are diffed against `HEAD`
  (pre-existing edit attributed to the attempt);
- M2 untracked files skipped;
- M3 `git add -N` (or any index write) used to make untracked files visible;
- M4 `GIT_OPTIONAL_LOCKS=0` removed (index refreshed by `status`, test 8);
- M5 a secret-named file's content put in the patch;
- M6 a secret-named file's hash recorded;
- M7 truncation not recorded (`complete` stays `True`);
- M8 the patch cut mid-file instead of at a file boundary;
- M9 a non-git workspace raises and fails the run;
- M10 capture taken after the checks instead of after the implementation;
- M11 `candidate_revision` filled when HEAD did not move;
- M12 insertions counted including withheld files;
- M13 the missing `\ No newline at end of file` marker (patch fails to apply);
- M14 a symlink followed and its target's content read.

Do not weaken, delete, or rewrite existing tests.

### 9. Documentation

Re-derive every `path:line` after the last edit.

- `docs/HARNESS_FRAMEWORK.md:36` — the EVIDENCE row: add the blueprint
  citation `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:311`, and code citations
  for `overseer/workdiff.py` (`snapshot`, `capture`, the read-only runner) and
  the `run_one` lines that write `diff.patch` and `diff.json`. Extend the
  verdict: each command-mode attempt in a git workspace now leaves a patch
  receipt of what the implementation command left in the workspace, compared
  with the state at the start of the attempt, with stats, a digest, and the
  bounds; pre-existing changes are not attributed; ignored files are not seen;
  renames are not detected; secret, binary, oversized, and symlinked content is
  withheld with the reason; a non-git workspace or a non-command mode records
  why nothing was captured; the patch is not a review. Keep the verdict word
  as it is, "implemented for local runs". The "Next increment" cell stays as
  it is (reviewer identity and trace capture wait for a real adapter).
- The CONTEXT row and every other row: re-derive the citations that moved; no
  verdict change. Note in the WORK_LOG that the CONTEXT row's named handoff
  record now has `candidate_revision` in one case (HEAD moved), and that the
  row's next increment is otherwise unchanged.
- "What this framework does not claim": add one bullet — the patch receipt
  shows what the workspace held after the implementation command; it does not
  show which process made a change, it misses ignored files, it does not detect
  renames, and it is not a review or an acceptance.
- `README.md` "Software factory direction" (from line 45): one paragraph on
  `diff.patch` and `diff.json`, the before/after rule, the bounds, and the
  limits.
- `WORK_LOG.md` — a new `###` section after the last line: the user's request
  quoted, the pillar choice and why, the precondition commit, the rules, the
  bounds, the commands and results, the new test count, M1–M16 with the
  failing test of each, that every citation was re-derived, and that the prompt
  was written by the dedicated prompt-writing agent and executed by the primary
  agent.

## Acceptance criteria (observable)

1. Precondition met.
2. `python3 scripts/check` passes: baseline tests unchanged plus at least 14
   new (16 with section 7a). The count is reported.
3. `python3 scripts/check-doc-references`: every reference resolves, count not
   below the baseline.
4. A command-mode attempt in a git workspace leaves `diff.patch` and
   `diff.json`; the patch applies to the before state and reproduces the after
   bytes of every `in_patch` file.
5. Pre-existing changes are not in the patch; secret content and hashes are
   nowhere in the evidence; the workspace index, HEAD, and refs are unchanged.
6. The manifest's `workspace_diff` block matches `diff.json`; the count
   identity holds; `candidate_revision` is filled only when HEAD moved.
7. A non-git workspace and the three non-command modes run exactly as before,
   with the reason recorded.
8. M1–M16 each fail the suite, recorded in the WORK_LOG.
9. `grep -n "^from overseer.factory\|^import overseer.factory" overseer/workdiff.py`
   prints nothing; `grep -n "'add'\|'stash'\|'apply'\|'reset'\|'checkout'\|update-index" overseer/workdiff.py`
   prints nothing.
10. One commit containing the increment and this prompt file; `git status
    --short` prints nothing after it.

## Constraints

- Python 3 standard library only.
- One primary editor. No other objective, no change to the verifiers, publish
  gate, states, ledger schema, monitor, codemap behaviour, recall, or skills.
- File this increment against exactly the EVIDENCE row.
- Do not invent benchmark results, token counts, costs, or savings.

## Verification commands

```text
git status --short          # before: only this prompt untracked, at the skills commit
python3 scripts/check
python3 scripts/check-doc-references
grep -n "^from overseer.factory\|^import overseer.factory" overseer/workdiff.py
grep -n "'add'\|'stash'\|'apply'\|'reset'\|'checkout'\|update-index" overseer/workdiff.py
git diff --stat
git status --short          # after the commit: empty
```

## Allowed work and stopping condition

Allowed: new `overseer/workdiff.py`; `overseer/factory.py` (the command branch
of `run_one`, the summary, `_context_manifest`'s `workspace_diff` keyword,
block, and the `unmeasured` rule of section 6); `tests/test_factory.py` (new
tests only); `docs/HARNESS_FRAMEWORK.md` (the EVIDENCE row, one new
does-not-claim bullet, re-derived citations elsewhere); `README.md`;
`WORK_LOG.md`.

Commit with a message in the repository's voice, for example "Capture the
workspace diff of an attempt as a patch receipt", ending with the attribution
lines the session supplies, and include this prompt file in the commit.

Stop after this one increment and its commit: the patch receipt is captured
read-only and scoped to the attempt, the manifest carries it honestly, the
bounds hold, M1–M16 each fail the suite, the docs are current with re-derived
citations, both commands pass, and the tree is clean. Report the commit hash,
the diff summary, the command outputs, the new test and reference counts, the
mutation results, and the limits that remain. This stopping condition ends this
prompt, not the objective: report `step_done` with the CONTEXT row's pending
"Next increment" (the handoff record) in `remaining`. If the same failure
recurs twice with no new evidence, stop and report it instead of retrying.
