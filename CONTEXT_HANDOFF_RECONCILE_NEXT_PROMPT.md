# Read the handoff record back and reconcile it against the ledger and the workspace

Status: **ready to execute at commit `fcf5586`**. This prompt was written by
the dedicated prompt-writing agent of the Overseer project. The primary agent
executes it; writing it is not completion.

The objective, quoted from the CONTEXT row's "Next increment" cell of
`docs/HARNESS_FRAMEWORK.md:32`, verbatim:

> read the persisted handoff record back and reconcile it against the ledger
> row and the workspace — the blueprint's "the successor checks the ledger and
> workspace before trusting the summary; if they disagree, reconcile"
> (`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299`) is still done by hand, and no
> code reads handoff.json

The blueprint sentence this increment serves
(`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299`, measured):

> On handoff, persist objective, base and candidate revisions, completed
> acceptance IDs, failing IDs, environment state, commands actually run,
> unresolved effects, remaining budget, and next eligible action. The successor
> checks the ledger and workspace before trusting the summary. If they
> disagree, reconcile.

The previous increment persisted the record (commit `fcf5586`, "Persist the
blueprint's handoff record for every attempt"). This increment adds the
**successor side**: code that reads a persisted `handoff.json` back, checks it
against the ledger row for that job and against the current state of the
workspace, and says plainly where they disagree and what it did about it.

## What this increment is

Two things, and they must not be confused:

1. **The code.** A new module and a thin factory surface that read a persisted
   record back and report the disagreements between it, the ledger row, and the
   workspace. It is a read-only report: it records a disagreement, it does not
   resolve one.
2. **The map.** The CONTEXT row of `docs/HARNESS_FRAMEWORK.md:32` records the
   increment: its verdict, its citations, its does-not-claim bullet, and its
   next increment. The reconciliation itself is *not* written into the
   markdown; it is written into the run's evidence directory at run time, or
   when an operator asks for it.

## Which pillar row this is filed against

Exactly one: **CONTEXT**, `docs/HARNESS_FRAMEWORK.md:32`. The other five rows'
verdicts do not change; only citations that moved are re-derived.

## Preconditions

This prompt was written against commit `fcf5586` ("Persist the blueprint's
handoff record for every attempt"), branch `main`.

1. `HEAD` is `fcf5586`. If it is not, stop and report `needs_input`.
2. The working tree is **not** clean, and that is expected. Measured at the
   time this prompt was written:

   ```text
   $ git status --short
    M AGENTS.md
   ?? HARDENING_BLUEPRINT.md
   ?? CONTEXT_HANDOFF_RECONCILE_NEXT_PROMPT.md
   ```

   `AGENTS.md` is modified and `HARDENING_BLUEPRINT.md` is untracked. Both are
   the operator's, not this increment's:

   - **Do not edit them.** `AGENTS.md` now carries the hardening compliance
     mandates quoted in the next section, and `HARDENING_BLUEPRINT.md` is the
     blueprint they come from.
   - **Do not commit them.** Commit only the paths named in "Allowed work".
     Use an explicit `git add <path> ...` — never `git add -A` and never
     `git commit -a` — so the operator's two files stay uncommitted.
   - `CONTEXT_HANDOFF_RECONCILE_NEXT_PROMPT.md` is this prompt; it is committed
     with the increment.
3. Baseline commands, measured by the prompt-writing agent on the tree as it
   is now, with the real output:

   ```text
   $ python3 scripts/check
   ...
   Ran 350 tests in 44.759s

   OK

   $ python3 scripts/check-doc-references
   189 references checked in HARNESS_FRAMEWORK.md
   ```

   Use **350** and **189** as the baselines, and re-run both before you change
   anything; if either number differs, report the difference instead of
   assuming it.
4. **Re-measure every line reference below** against `fcf5586` before you act
   on it. The references were measured by the prompt-writing agent; an edit
   moves them. `scripts/check-doc-references` proves that a cited path exists
   and that the line is inside the file — it does **not** prove that the line
   says what is claimed. Read each cited line by content and say so in the
   work log.
5. The primary spec of this increment is the blueprint sentence at
   `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299` and the CONTEXT row at
   `docs/HARNESS_FRAMEWORK.md:32`. There is **no `SPEC.md`** in this
   repository (measured), so the blueprint and the pillar map are the ground
   truth to re-read before writing code.

## The directives that bind this increment

`AGENTS.md` binds every agent that works on this project. The hardening
mandates added to it now are part of the acceptance, not advice:

- **RED-GREEN SEPARATION.** `AGENTS.md:58`: *"When assigned an implementation
  task, you are STRICTLY FORBIDDEN from modifying any file inside `tests/`.
  Test files are read-only during coding phases."* This increment is therefore
  executed in two separated phases — a **red phase** that writes only
  `tests/test_factory.py`, and a **green phase** that writes only
  implementation files. The phases, their boundary, and the evidence that the
  boundary held are specified under "Execution order".
- **LOCALITY LIMIT.** `AGENTS.md:59`: *"Keep file growth lean. If a single
  module modification adds more than 15% new lines or creates massive
  duplicate functions, split the logic or flag it for structural review."*
  `overseer/factory.py` is 2304 lines, so 15% is about 345 lines; the
  factory's share of this increment must stay far below that, and the new
  module must stay below the 300-line flagging threshold that
  `HARDENING_BLUEPRINT.md:10` names.
- **GROUND TRUTH RE-READ.** `AGENTS.md:60`: re-read the core feature intent
  from the primary spec before writing code. The primary spec is named in
  precondition 5.
- `HARDENING_BLUEPRINT.md:28` also requires exact assertions: *"Forbid generic
  assertions (e.g., `assert result is not None`); require exact state or
  schema validations."* Every new test asserts an exact value, an exact set,
  or an exact schema — never a bare "is not None".
- `HARDENING_BLUEPRINT.md:47` kills any terminal command that runs longer than
  60 seconds with `SIGKILL`. The full suite measured 44.8 s, so it fits; run
  the commands one at a time, never several in one shell invocation.

The house rules carried forward from the earlier reviews are part of the
acceptance too:

1. **Line citations drift.** Re-derive every `path:line` citation by hand
   after the last edit, in every row and passage the increment touches, and
   re-read each one by content. The project's checker proves a cited line
   exists, not that it names the right thing.
2. **A test is evidence only if a plausible wrong implementation fails it.**
   Run the mutations one at a time; show the suite failing; name the failing
   test; revert.
3. **Counts describe what is shown.** A count says what it counts.
4. **Words claim only what was observed.** An unobservable field is marked
   unmeasured with the reason, and is never estimated.
5. **An exception must never leave a job stuck or change an attempt's
   outcome.** The reconciliation is a report; nothing it does may alter the
   job's state or the attempt's verdict.
6. **Every departure from this prompt, and every read-only command the
   increment needed that this prompt did not name, goes into the work log.**

## The decisions this increment makes

These are settled here, in writing, and are part of the acceptance.

### 1. Where the reconciliation lives

**A new module `overseer/reconcile.py`**, in the style of `overseer/handoff.py`
and `overseer/workdiff.py`: module constants for every bound, small functions
whose docstrings state the reason, dict results, and a `reason` wherever
something could not be done.

It **imports nothing from `overseer.factory` and nothing from
`overseer.codemap`**. It imports only the standard library: `hashlib`, `json`,
`os`, `re`, and `pathlib.Path`.

**The rule:** the module reads no ledger and starts no process. The factory
hands it three sets of facts — the record's bytes and path, the ledger row's
facts, and the workspace's facts — and the module compares them. The factory
gathers the ledger row (it owns the database) and the workspace facts (it owns
the read-only git surface).

`Factory.reconcile_handoff(job_id)` is the factory's thin surface: it reads
the row, gathers the workspace facts, calls the module, writes the report, and
records the event. It holds the worker lock (`overseer/factory.py:713-733`,
the same lock `decide()` and `resolve()` take), so it cannot run while a
factory worker owns the database; when it cannot, it raises `RuntimeError`
and the CLI reports it as a JSON error.

### 2. What "the ledger row" means

**The `jobs` row for that job id**, read with
`SELECT * FROM jobs WHERE id=?` (the table is `overseer/factory.py:410-414`),
plus **the `handoff` event of that job** in the `events` table
(`overseer/factory.py:415-417`), whose detail is
`'handoff.json sha256=%s'` (`overseer/factory.py:1421`).

The row's fields that are compared, and how a mismatch is reported:

| ledger field | compared with | disagreement kind |
| --- | --- | --- |
| `id` | the record's `job_id` | `job_id_mismatch` |
| `run_id` | the record's `run_id` | `run_id_mismatch` |
| `spec_hash` | the record's `spec_hash` | `spec_hash_mismatch` |
| `state` | the record's `state` | `state_mismatch` |
| `detail` | the record's `detail` | `detail_mismatch` |
| `spec` (the stored specification's `contract.acceptance_ids`) | the record's three identifier lists | `acceptance_ids_mismatch` |
| the `handoff` event's recorded SHA-256 | the digest of the record file as read back | `digest_mismatch` |

The row's `evidence` column names the run's evidence directory
(`overseer/factory.py:2131-2132` writes it), and the record file is
`<evidence>/handoff.json` — the same name `overseer/factory.py:1410` writes.

**A measured fact the executor must not contradict:** the `jobs` table has **no
commit column**. It holds `seq, id, spec, spec_hash, state, created, started,
finished, run_id, evidence, detail, child_group` (`overseer/factory.py:410-414`).
So no code can read the attempt-start commit back out of the ledger row, and
the brief's phrase "the ledger's observed base commit" has no counterparty in
the schema. The revisions are therefore anchored in the **workspace**, which is
the only authority that can name a commit without a second file read; the
ledger's part is the job's identity, state, detail, specification hash, run
id, and the recorded digest. This is stated here so that nobody goes looking
for a column that does not exist. Record this reading in the work log.

### 3. What "the workspace" means

**The read-only git facts of the workspace the ledger's stored specification
names** (`spec['workspace']` in the `jobs` row's `spec` column), taken through
the existing read-only surface: `workdiff.snapshot(workspace, hold=False)`
(`overseer/workdiff.py:157-209`), whose git runner
(`overseer/workdiff.py:52-75`) sets `GIT_OPTIONAL_LOCKS=0` and uses no pager,
prompt, hook, fsmonitor, or untracked cache.

The facts are: the repository root (`root`), the current HEAD commit
(`head`), whether the worktree is dirty (`bool(status)`), and — when the
workspace cannot be read — the real reason (`reason`).

**Never** a write, never a checkout, never a reset, never a stash, never
`git add`, never `git commit`. The reconciliation runs no git command of its
own; it uses the snapshot the codebase already takes.

`workdiff.snapshot()` reports the real reason when it cannot read the
workspace: `'the workspace is not a directory'`, `'the workspace is not a git
work tree'`, `'git is not available on this machine'`
(`overseer/workdiff.py:66`), and the other git failures it already names.

### 4. What counts as a disagreement — the closed list

Exactly these nine kinds, and no others:

| kind | the record says | the authority says |
| --- | --- | --- |
| `job_id_mismatch` | its `job_id` | the ledger row's `id` |
| `run_id_mismatch` | its `run_id` | the ledger row's `run_id` |
| `spec_hash_mismatch` | its `spec_hash` | the ledger row's `spec_hash` |
| `state_mismatch` | its `state` | the ledger row's `state` |
| `detail_mismatch` | its `detail` | the ledger row's `detail` |
| `base_revision_unanchored` | its `base_revision.value` | the workspace's HEAD is neither the record's base revision nor, when the record says HEAD moved, its candidate revision |
| `candidate_revision_mismatch` | its `candidate_revision.value` | the workspace's current HEAD, compared only when the record says HEAD moved |
| `acceptance_ids_mismatch` | its completed, failing, and not-run identifier lists | the contract's `acceptance_ids` stored in the ledger row's specification |
| `digest_mismatch` | the SHA-256 of the record file as read back | the SHA-256 the ledger recorded for it in the `handoff` event |

**The rule for every disagreement:** it names **both sides** — what the record
says and what the authority says — and it never silently prefers one. Each
entry is a dict with the keys `kind`, `record`, `authority`, and `reason`,
where `reason` is one sentence saying which two facts were compared and why
they differ.

The rules that decide the two revision comparisons, in full:

- The record's `base_revision` and `candidate_revision` are objects of the
  shape `{'value': ..., 'source': ...}` (`overseer/handoff.py:203-229`). A
  `value` of `None` means the factory could not observe that revision, and the
  `source` says why.
- **`candidate_revision_mismatch`** is reported only when the record's
  `candidate_revision.value` is not `None` — that is, when the record says the
  attempt moved HEAD — and that value is not the workspace's current HEAD. When
  the record's candidate revision is `None`, the comparison is **not**
  applicable: the record said HEAD did not move, and there is nothing to
  compare. It is recorded as not applicable, not as a disagreement and not as
  an agreement.
- **`base_revision_unanchored`** is reported when the workspace was read, the
  record's `base_revision.value` is not `None`, and the workspace's HEAD is
  neither the record's base revision nor the record's candidate revision. In
  that case the record does not describe the workspace's current revision.
  When the record's base revision is `None`, the comparison is not applicable,
  exactly as above.
- A workspace that moved on after the attempt therefore yields
  `base_revision_unanchored`. That is a report, not a verdict: the does-not-
  claim bullet must say it is not proof that the record is wrong.

**The identifier comparison.** The contract's `acceptance_ids` are a list of
unique identifiers, one per acceptance command
(`overseer/factory.py:243-252`). The record's three lists — completed,
failing, not run — must be **disjoint** and their **union** must equal the
contract's identifiers. The comparison is on **sets**, not on list order: a
record whose lists hold the same identifiers in a different order agrees. A
record that names an identifier the contract does not name, misses one the
contract names, or puts one identifier in two lists, is an
`acceptance_ids_mismatch`. A partial overlap is a mismatch; it is never
accepted as agreement.

### 5. Whether the reconciliation may change anything

**It may not change the attempt.** It must not change the job's state, must
not rewrite `handoff.json`, must not re-run or re-accept anything, must not
decide an attempt's outcome, and must not touch the verifiers, the publish
gate, or the state machine.

**It is a read-only report.** "Reconciling" means *recording* the
disagreement, not resolving it by fiat. No disagreement is ever closed by the
code; the ledger row and the workspace stay the authority.

The only writes it performs are the three named in decision 6. There is **no**
operator-facing *decision* action in this increment: the one operator-facing
thing is the explicit command of decision 7, which reports and never decides.

### 6. Where the reconciliation result goes

Three places, and **not** a fourth:

1. **A new file `reconciliation.json` in the run's evidence directory** —
   beside `handoff.json`, `context.json`, and `summary.json`. It is the
   reconciliation's own output; `handoff.json` is never rewritten.
2. **An entry in `summary.json`** — the key `reconciliation`, carrying
   `path`, `sha256`, `verdict`, `disagreement_count`, and `unverifiable_count`.
   The reconciliation **adds that key and changes nothing else** in
   `summary.json`; a test asserts that every other key is byte-identical
   before and after. `summary.json` has no digest recorded in the ledger, so
   adding a key contradicts nothing.
3. **One `reconciliation` event in the ledger** — `self.event(job_id,
   'reconciliation', detail)` (`overseer/factory.py:462-464`), whose detail
   carries the verdict, the disagreement count, the path, and the digest of
   `reconciliation.json`. The `events.state` column already holds free-form
   state names (`'handoff'` at `overseer/factory.py:1421`, `'context_manifest'`
   at `overseer/factory.py:2237`); the new value follows that pattern.

**The context manifest is NOT rewritten, and this is a decision with a
measured reason.** The manifest's SHA-256 is recorded in the ledger's
`context_manifest` event (`overseer/factory.py:2237`) *and* in
`summary.json`'s `context_manifest` entry (`overseer/factory.py:2233-2234`),
and the existing test `tests/test_factory.py:1552-1563` asserts that the
file's digest on disk equals both. Rewriting `context.json` to add a
`reconciliation` block would leave the ledger claiming a digest the file no
longer has — the reconciliation would make the ledger false, which is the one
thing this increment must never do. The report says so explicitly: it carries
`manifest_updated: False` and a `manifest_reason` naming this reason. The
brief listed a manifest block among the destinations; this increment does not
write one, and the departure is recorded in the work log.

**No ledger table, column, or row type is added.** The `jobs`, `events`,
`approvals`, `memory_records`, `attempts`, `fixture_verifications`, and
`fake_provider_verifications` tables (`overseer/factory.py:410-455`) are
unchanged.

### 7. How a successor asks for it

**A method on `Factory` plus a CLI subcommand.**

- `Factory.reconcile_handoff(job_id)` returns the report dict.
- The CLI subcommand is **`reconcile-handoff <id>`**:
  `python3 -m overseer.factory reconcile-handoff <id>`.

  The name is not `reconcile`: `reconcile` is already a subcommand
  (`overseer/factory.py:2253`) that marks interrupted jobs
  `needs_reconciliation` (`overseer/factory.py:740-758`). The two must never
  be confused.

**The CLI keeps the existing contract.** `main()` catches only
`(ValueError, OSError, RuntimeError, sqlite3.Error)`
(`overseer/factory.py:2296`), so:

- Invalid input prints the JSON object `{"error": ...}` and exits 1, never a
  traceback. An unknown job id is invalid input: `reconcile_handoff` raises
  `ValueError('unknown job')`, exactly as `inspect()` does at
  `overseer/factory.py:492-493`.
- **A finding is not invalid input.** A missing record, a malformed record, a
  workspace that is not a git repository, and a `disagree` verdict are all
  *reports*: the command prints the report and exits **0**. Only invalid
  input exits 1.
- `reconcile_handoff` must raise **only** the four types `main()` catches. In
  particular `RecursionError` must never escape the module — `main()` does not
  catch it — and `json.JSONDecodeError` (a `ValueError`) is caught but must be
  turned into a reason inside the module anyway, because the report needs to
  say *why*.

### 8. Fail-closed behavior

Each of these is reported **with the real reason**, never as "no
disagreement", and never as a crash:

| situation | the report says |
| --- | --- |
| `handoff.json` does not exist | `unverifiable`, reason: the record does not exist |
| it is not JSON | `unverifiable`, reason: the record is not JSON |
| it is a JSON array, not an object | `unverifiable`, reason: the record is not a JSON object |
| its `kind` is not `handoff_record` | `unverifiable`, reason naming the kind it has |
| one of its fields has the wrong type | `unverifiable`, reason naming the field and the type it has |
| it is nested deeper than the bound | `unverifiable`, reason naming the bound |
| it is larger than the bound | `unverifiable`, reason naming the bound and the size |
| the job has no `handoff` event, so the ledger records no digest | the digest check is unverifiable, reason: the ledger records no digest for the record |
| the workspace is unreadable | the workspace facts are absent, with the reason |
| the workspace is not a git repository | the workspace facts are absent, reason: the workspace is not a git work tree |
| git is unavailable | the workspace facts are absent, reason: git is not available on this machine |

A missing record is **information**, not a failure: the record's own note says
so (`overseer/handoff.py:22-26`).

### 9. Bounds

As module constants in `overseer/reconcile.py`, recorded in the report's
`limits`, in the style of `overseer/handoff.py:16-20` and
`overseer/workdiff.py:22-36`:

- `MAX_RECORD_BYTES = 64 * 1024` — the record file. The size is checked
  **before** the file is opened (`os.stat`), the read is
  `MAX_RECORD_BYTES + 1` bytes, and a longer read is refused. This is the
  pattern of `overseer/skills.py:180-191`.
- `MAX_JSON_DEPTH = 64` — the parsed record's nesting depth is measured, and a
  deeper one is refused. The JSON parse itself is wrapped so that a
  `RecursionError` becomes a reason instead of a crash. This is the pattern of
  `overseer/factory.py:596-598`, which already handles a receipt of 2000
  nested arrays.
- `MAX_IDENTIFIERS = 20` — the contract's acceptance identifiers, the same
  bound the record uses (`overseer/handoff.py:18`).
- `MAX_DISAGREEMENTS = 32` — the disagreement list; the ones past the bound
  are counted apart with the reason, exactly as the codebase counts what a
  cap left out elsewhere.

**The reconciliation reads exactly one file: the record.** `results.json`,
`context.json`, `diff.json`, and `summary.json` are not read for their
content — `summary.json` is only *added to*, and the expected digest comes
from the ledger's event, not from `summary.json`.

**It never reads a secret-named file.** The path's name is checked with the
secret rule before the file is opened. Because the module must not import
`overseer.codemap`, it carries its **own copy** of the rule
(`SECRET_NAMES`, `SECRET_SUFFIXES`, and an `is_secret_path` function, matching
`overseer/codemap.py:66-71` and `overseer/codemap.py:166-173`). A new test
asserts that the copy and `overseer.codemap.is_secret` agree on a list of
sample names, so the copy cannot drift silently; the duplication and that
test are named in the work log.

### 10. The verdict

A closed set of three:

- **`agree`** — the record was read and validated, the ledger row was found,
  the ledger's digest was found, the workspace was read, and no disagreement
  was found.
- **`disagree`** — at least one disagreement was found.
- **`unverifiable`** — no disagreement was found, but at least one required
  fact could not be obtained. The report names each missing fact and its
  reason in an `unverifiable` list, and the verdict's `reason` says why the
  answer is not an agreement.

**Precedence:** a found disagreement outranks an unverifiable fact. When both
are present the verdict is `disagree`, and the unverifiable reasons are still
carried in the report.

**`unverifiable` is a first-class answer and is never reported as agreement.**

## Repository and paths

- Repository: `/home/kali/Programming/Projects/Overseer`, branch `main`.
- Python 3 standard library only. No new dependency.
- `git` is used read-only, through `overseer/workdiff.py`.

Measured at `fcf5586`; re-measure (precondition 4) before acting on any of
them:

| Path and line | What it is now |
| --- | --- |
| `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299` | the handoff sentence: persist the ten fields, and the successor checks the ledger and workspace and reconciles a disagreement |
| `docs/HARNESS_FRAMEWORK.md:32` | the CONTEXT row |
| `docs/HARNESS_FRAMEWORK.md:84` | the heading "What this framework does not claim"; its bullets run to line 147 |
| `docs/HARNESS_FRAMEWORK.md:119-123` | the handoff-record bullet: the successor still has to check the ledger and the workspace and reconcile a disagreement |
| `docs/HARNESS_FRAMEWORK.md:149-160` | "Filing an increment against a pillar": a verdict is raised only with a cited file and line, or a named test |
| `overseer/handoff.py:16-20` | the record module's bounds and its `LIMITS` |
| `overseer/handoff.py:22-26` | the record's own `NOTE`: the ledger row and the workspace are the authority, and a missing `handoff.json` is itself information |
| `overseer/handoff.py:187` | `build(...)`: the record builder |
| `overseer/handoff.py:271-272` | the record's `version: 1` and `kind: 'handoff_record'` |
| `overseer/factory.py:312-324` | `_run_git(workspace, *arguments)`: a read-only git fact, with the real reason when git fails |
| `overseer/factory.py:327-338` | `repository_identity(workspace)`: root, `base_commit`, and the attempt-start source string |
| `overseer/factory.py:410-414` | the `jobs` table; it has **no** commit column |
| `overseer/factory.py:415-417` | the `events` table |
| `overseer/factory.py:462-464` | `event(job_id, state, detail)` |
| `overseer/factory.py:492-493` | `inspect()` raises `ValueError('unknown job')` |
| `overseer/factory.py:596-598` | the pattern that turns a `RecursionError` and a bad receipt into a reason |
| `overseer/factory.py:713-733` | `worker_lock()`: the lock `decide()` and `resolve()` take |
| `overseer/factory.py:735-738` | `transition(job_id, state, detail)` — the call the reconciliation must never make |
| `overseer/factory.py:740-758` | the existing `reconcile()`: marks interrupted jobs `needs_reconciliation` |
| `overseer/factory.py:1261` | the manifest's `handoff` block key |
| `overseer/factory.py:1269-1290` | `_manifest_handoff(...)`: how a block is projected from a record |
| `overseer/factory.py:1397-1424` | `_record_handoff(...)`: builds, writes, digests, and records the record |
| `overseer/factory.py:1410-1414` | `handoff.json`'s path and its SHA-256 |
| `overseer/factory.py:1421` | the `handoff` event: `'handoff.json sha256=%s'` |
| `overseer/factory.py:2060` | `run_one()` |
| `overseer/factory.py:2092` | the per-run evidence directory |
| `overseer/factory.py:2131-2132` | the job row's `run_id` and `evidence` columns are written |
| `overseer/factory.py:2211-2219` | the run summary, and `summary['handoff']` |
| `overseer/factory.py:2227-2235` | the manifest is built and written, then `summary['context_manifest']`, then `summary.json` |
| `overseer/factory.py:2233-2234` | `summary['context_manifest'] = {'path', 'sha256'}` |
| `overseer/factory.py:2237` | the `context_manifest` event: `'context.json sha256=...'` |
| `overseer/factory.py:2245-2263` | `main()` and its subcommands |
| `overseer/factory.py:2253` | `sub.add_parser('reconcile')` — the name the new subcommand must not take |
| `overseer/factory.py:2294-2298` | the JSON print, and the error handler that catches only `(ValueError, OSError, RuntimeError, sqlite3.Error)` |
| `overseer/workdiff.py:22-36` | the capture bounds and `LIMITS` |
| `overseer/workdiff.py:52-75` | the read-only git runner: `GIT_OPTIONAL_LOCKS=0`, no pager, no prompt, no hook |
| `overseer/workdiff.py:157-209` | `snapshot(workspace, hold=True)`: root, prefix, head, status; the real reason when it cannot read the workspace |
| `overseer/workdiff.py:492-494` | `unchecked(reason)`: the receipt of a capture that could not be made |
| `overseer/codemap.py:66-71` | `SECRET_SUFFIXES` and `SECRET_NAMES` |
| `overseer/codemap.py:166-173` | `is_secret(path)` |
| `overseer/skills.py:180-191` | the size-check-before-open pattern the record read follows |
| `tests/test_factory.py:30-51` | `attach_contract`: the helper that gives a spec a valid contract block |
| `tests/test_factory.py:54-62` | `store_legacy_job`: stores a job the way the ledger held it before the contract rule |
| `tests/test_factory.py:1552-1563` | the test that the manifest's digest on disk equals the digest in `summary.json` and in the `context_manifest` event — the reason the manifest is not rewritten |
| `tests/test_factory.py:3389-3467` | `class WorkspaceDiffTests`: a git workspace with a committed base, and the `spec`/`run_spec` helpers |
| `tests/test_factory.py:3689-3950` | `class HandoffRecordTests`: the record's own tests, and the `spec`, `run_record`, `manifest_of`, `git`, and `commit` helpers to reuse |
| `README.md:80-100` | the paragraph that describes `handoff.json`; the new paragraph goes after it |
| `WORK_LOG.md:2842-2974` | the last section; the file ends at 2974 |

## Required behavior

### 1. Reading the record back

`overseer/reconcile.py` provides a bounded reader over the record file:

- the path is checked for a secret name before it is opened (decision 9);
- `os.stat` gives the size, and a file larger than `MAX_RECORD_BYTES` is
  refused **before** it is opened;
- the bytes are read with a `MAX_RECORD_BYTES + 1` cap;
- the digest is the SHA-256 of the bytes as read;
- the bytes are decoded as UTF-8 and parsed as JSON; a `UnicodeDecodeError`,
  a `json.JSONDecodeError`, and a `RecursionError` each become a reason, never
  an exception;
- the parsed value must be a **JSON object**; a JSON array is refused with the
  reason "the record is not a JSON object";
- the object's `kind` must be `handoff_record`; anything else is refused with
  the reason naming the kind it has;
- the fields the comparison needs must have the right types:
  `job_id`, `run_id`, `spec_hash`, `state`, and `detail` are text; `base_revision`
  and `candidate_revision` are objects with a `value` and a `source`; the
  three identifier lists are lists of text. A field with the wrong type is
  refused with the reason naming the field and the type it has;
- the nesting depth of the parsed value is measured and a value deeper than
  `MAX_JSON_DEPTH` is refused.

Every refusal produces the same shape — the record was not read, and here is
the reason — so that the caller never has to distinguish "no disagreement"
from "could not look".

### 2. The ledger facts

The factory reads the row and hands the module plain values:

- `id`, `state`, `spec_hash`, `run_id`, `evidence`, `detail`;
- the stored specification's `contract.acceptance_ids` — a list, possibly
  empty, and `None` when the stored job names no contract (the legacy case
  `store_legacy_job` creates). When the stored job names no contract, the
  identifier comparison is **not applicable**: there is no authority to compare
  the record's lists against, and the report says so rather than reporting a
  disagreement or an agreement;
- the `handoff` event's recorded digest, parsed from the event detail
  `'handoff.json sha256=<digest>'`. When the job has no `handoff` event, the
  digest is `None` and the reason is "the ledger records no digest for the
  handoff record"; the digest check is then unverifiable, not agreeing.

The stored specification is parsed with the same care: a `spec` column that is
not JSON, or a contract that is not an object, is a reason and not a crash.

### 3. The workspace facts

The factory takes the workspace from the ledger row's stored specification and
calls `workdiff.snapshot(workspace, hold=False)`:

- `captured` true → the facts are `root`, `head`, `dirty` (`bool(status)`), and
  `reason` is `None`;
- `captured` false → the facts are absent and `reason` is the snapshot's own
  reason, unchanged.

The snapshot is the only git surface the reconciliation touches, and it is
read-only (`GIT_OPTIONAL_LOCKS=0`, `overseer/workdiff.py:60-61`).

### 4. The comparison

The module compares, in this order, and records a disagreement for each fact
that differs:

1. `job_id` against the row's `id`;
2. `run_id` against the row's `run_id`;
3. `spec_hash` against the row's `spec_hash`;
4. `state` against the row's `state`;
5. `detail` against the row's `detail`;
6. the three identifier lists against the contract's identifiers, as sets,
   disjoint and covering;
7. the digest of the record file as read back against the digest the ledger
   recorded;
8. the candidate revision against the workspace's HEAD, when the record says
   HEAD moved and the workspace was read;
9. the base revision against the workspace's HEAD, when the record carries one
   and the workspace was read.

The comparisons that could not be made — no digest recorded, no contract
stored, a workspace that could not be read, a revision the record does not
carry — are recorded in the report's `unverifiable` list with their reason.
They are **never** counted as agreement.

### 5. The report

The report is a dict with this shape:

```python
{
  'version': 1,
  'kind': 'handoff_reconciliation',
  'job_id': ..., 'run_id': ..., 'verdict': 'agree' | 'disagree' | 'unverifiable',
  'reason': <one sentence>,
  'record': {'path': ..., 'sha256': ..., 'read': True, 'reason': None},
  'ledger': {'found': True, 'state': ..., 'detail': ..., 'spec_hash': ...,
             'run_id': ..., 'evidence': ..., 'recorded_sha256': ...,
             'recorded_sha256_source': 'the ledger handoff event',
             'recorded_sha256_reason': None},
  'workspace': {'path': ..., 'read': True, 'reason': None, 'root': ..., 'head': ...,
                'dirty': False},
  'disagreements': [{'kind': ..., 'record': ..., 'authority': ..., 'reason': ...}],
  'disagreement_count': 0,
  'unverifiable': [{'fact': ..., 'reason': ...}],
  'manifest_updated': False,
  'manifest_reason': <why the context manifest is not rewritten>,
  'limits': {...},
  'note': <one sentence>,
}
```

- The `record` block carries the record's **path and digest as read back**,
  and the reason when it was not read.
- The `ledger` block carries the **ledger row's facts**.
- The `workspace` block carries the **workspace's facts**.
- `disagreements` is the closed list, each entry naming **both sides** and a
  reason. `disagreement_count` describes that list.
- `unverifiable` names each fact that could not be obtained and why.
- The verdict is one of the three closed values, and `reason` says why.
- `note` says, in one sentence, that the report records a disagreement and
  does not resolve one, that the ledger row and the workspace remain the
  authority, and that nothing in the report changes an attempt's outcome.
- The report carries no stdout, no stderr, and no `output_truncated` key, the
  same way the record does not.

### 6. Writing the report

`Factory.reconcile_handoff(job_id)`:

1. takes the worker lock;
2. reads the `jobs` row; an unknown id raises `ValueError('unknown job')`;
3. reads the `handoff` event's digest;
4. gathers the workspace facts with `workdiff.snapshot(workspace,
   hold=False)`;
5. calls the module and gets the report;
6. writes `<evidence>/reconciliation.json` — the evidence directory named by
   the row's `evidence` column, exactly as `overseer/factory.py:1410` writes
   `handoff.json` beside it — and digests the bytes as written;
7. adds the `reconciliation` key to `summary.json` and changes nothing else
   in it;
8. records **one** `reconciliation` event in the ledger;
9. returns the report.

Every write is guarded the way `_diff_step` and `_diff_capture` are
(`overseer/factory.py:1340-1359`): a failure becomes a recorded reason, never
a crash and never a job left in a non-final state. If `reconciliation.json`
cannot be written, the report says so (`written: False` with the reason) and
the attempt is exactly as it was.

The reconciliation **never** calls `transition()` and never writes to
`handoff.json`.

### 7. What stays true

- The reconciliation never changes the job's state, never changes an attempt's
  outcome, and never decides one.
- `handoff.json` is byte-identical before and after a reconciliation.
- The verifiers, the publish gate, the state machine, the ledger schema, the
  monitor, the codemap, the recall, the skills reader, the workspace-diff
  capture semantics, and the handoff record's own shape are unchanged.
- The workspace is only read. No git command writes to the workspace, the
  index, or a ref.
- Every field the factory cannot observe is marked with the reason. Nothing is
  estimated, and no disagreement is resolved by the code.

## Tests

Add a new class `class HandoffReconciliationTests(unittest.TestCase)` to
`tests/test_factory.py`, **after** `class HandoffRecordTests`
(`tests/test_factory.py:3689-3950`), reusing its git workspace and its
`git`, `commit`, `spec`, `run_record`, and `manifest_of` helpers. Use
`attach_contract` (`tests/test_factory.py:30-51`) for a spec with a contract
and `store_legacy_job` (`tests/test_factory.py:54-62`) for a job stored before
the contract rule.

Every test uses a temporary database and a temporary workspace, never the
default runtime database (`overseer/factory.py:24`).

Two helpers the class needs, both in the test file:

- a helper that rewrites the record in the run's evidence directory with a
  mutated record **and** rewrites the ledger's `handoff` event detail to the
  new file's digest, so that exactly one check is under test and the digest
  check still passes. Name it `reseal_record`.
- a helper that reads the ledger row and the report's counts, for the
  "nothing changed" assertions.

At least fifteen tests, each naming the specific behaviour it proves:

1. `test_a_record_that_agrees_with_the_ledger_and_the_workspace_is_agree` —
   the verdict is `agree`, `disagreements` is empty, `unverifiable` is empty,
   and the report carries the record's path and digest as read back, the
   ledger row's facts, and the workspace's facts.
2. `test_a_ledger_state_changed_after_the_attempt_is_a_disagreement` — the
   ledger row's state is changed after the run; the report's verdict is
   `disagree` and the `state_mismatch` entry names **both** sides: the
   record's `passed` and the ledger's new state.
3. `test_a_spec_hash_mismatch_is_a_disagreement` — the record's `spec_hash`
   differs from the row's; the `spec_hash_mismatch` entry names both sides.
4. `test_a_run_id_mismatch_is_a_disagreement` — the record's `run_id` differs
   from the row's; the entry names both sides.
5. `test_a_candidate_revision_that_is_not_the_workspace_head_is_a_disagreement`
   — the workspace is committed to after the attempt; the record's candidate
   revision is not the workspace's HEAD; the `candidate_revision_mismatch`
   entry names both sides.
6. `test_acceptance_identifiers_that_do_not_match_the_stored_contract_are_a_disagreement`
   — the record's identifier lists are resealed to name an identifier the
   contract does not name; the `acceptance_ids_mismatch` entry names both
   sides.
7. `test_the_identifier_lists_are_compared_as_sets` — the record's lists are
   resealed in a different order; the verdict is still `agree`.
8. `test_a_tampered_record_whose_digest_differs_from_the_ledger_is_a_disagreement`
   — the record file is changed without resealing; the digest as read back
   differs from the ledger's recorded digest; the `digest_mismatch` entry
   names both sides.
9. `test_a_missing_record_is_unverifiable_with_the_real_reason` — the record
   file is removed; the verdict is `unverifiable`, never `agree`, and the
   reason says the record does not exist.
10. `test_a_malformed_record_that_is_a_json_array_is_unverifiable_with_the_real_reason`
    — the record file holds a JSON array; the verdict is `unverifiable` and the
    reason says the record is not a JSON object.
11. `test_a_record_with_a_wrong_typed_field_is_unverifiable_with_the_real_reason`
    — the record's `state` is a number; the verdict is `unverifiable` and the
    reason names the field.
12. `test_a_workspace_that_is_not_a_git_repository_is_unverifiable_with_the_reason`
    — the workspace is a plain directory; the workspace facts are absent with
    the reason "the workspace is not a git work tree", and the verdict is
    `unverifiable`, never `agree`.
13. `test_git_unavailable_is_unverifiable_with_the_reason` — `git` is made
    unavailable by patching `overseer.workdiff.subprocess.run` with
    `side_effect=FileNotFoundError`; the reason is "git is not available on
    this machine" and the verdict is `unverifiable`.
14. `test_the_reconciliation_never_changes_the_job_state` — the `jobs` row's
    `state` and `detail` are byte-identical before and after; the `events`
    table gained exactly one row, the `reconciliation` event; and no
    `transition` happened.
15. `test_the_reconciliation_never_writes_to_the_workspace_or_to_git` — the
    workspace's HEAD is unchanged, `git status --porcelain` is unchanged and
    empty, the index file's size and `st_mtime_ns` are unchanged, and every
    git argument vector the reconciliation caused to run is recorded and
    asserted to be a read-only command (none of `add`, `commit`, `checkout`,
    `reset`, `stash`, `write-tree`, `update-index`, `clean`, `fetch`, `pull`,
    `push`, `gc`).
16. `test_the_result_is_recorded_in_the_evidence_directory_the_summary_and_the_event`
    — `reconciliation.json` is in the run's evidence directory, `summary.json`
    gained the `reconciliation` key, and the event's detail names the verdict
    and the digest; the three agree. `summary.json`'s other keys are
    byte-identical before and after, and the context manifest is byte-identical
    before and after.
17. `test_the_record_itself_is_not_rewritten` — `handoff.json`'s bytes are
    identical before and after a reconciliation that found a disagreement.
18. `test_the_cli_reports_an_unknown_job_as_a_json_error` — the CLI prints
    `{"error": ...}` and exits 1 for an unknown job id, and prints no
    traceback.
19. `test_the_reconciliation_does_not_resolve_a_disagreement` — after a
    reconciliation that found a `state_mismatch`, the ledger row still holds
    the state it held before, and the report still names the disagreement.
20. `test_the_secret_name_rule_agrees_with_the_codemap_rule` — the module's
    own copy of the secret-name rule and `overseer.codemap.is_secret` agree on
    a list of sample names, including `.env`, `id_rsa`, `credentials.json`,
    `token.json`, and `server.pem`.

Do not weaken, delete, or rewrite existing tests.

### Mutations

One at a time, each shown failing the suite with the test that catches it,
then reverted. Each mutation edits **implementation code only** — never a
test. Run the new class alone for each mutation:

```text
TMUX_TMPDIR=/tmp/opencode/overseer-check python3 -m unittest discover -s tests -p 'test_factory.py' -k HandoffReconciliation -v
```

(measured: the existing `HandoffRecordTests` class runs 15 tests in 5.5 s
with this command; the new class must be comparable.)

- **M1** the state comparison is dropped (`state_mismatch` is never reported)
  — test 2 fails.
- **M2** a mismatch is reported as agreement (the verdict is forced to
  `agree` when the disagreement list is non-empty) — test 2 fails.
- **M3** `unverifiable` is reported as `agree` — tests 9, 12, and 13 fail.
- **M4** the digest check is dropped — test 8 fails.
- **M5** the contract's identifiers are compared against the record's own
  lists instead of the ledger's stored contract — test 6 fails.
- **M6** the workspace is probed with a git command that writes (the optional
  index refresh is no longer disabled, or a writing command is added) —
  test 15 fails.
- **M7** a malformed record is treated as "no disagreement" (the parse failure
  yields an empty record and the verdict becomes `agree`) — tests 10 and 11
  fail.
- **M8** the reconciliation is allowed to change the job's state (it calls
  `transition`) — test 14 fails.
- **M9** the record is rewritten by the reconciliation — test 17 fails.
- **M10** the identifier lists are compared order-sensitively (`==` on lists
  instead of a set comparison) — test 7 fails.
- **M11** the identifier comparison is a subset test, so a record that names
  only some of the contract's identifiers passes — test 6 fails.
- **M12** a disagreement names only the record's side and not the authority's
  — tests 2, 3, 4, and 5 fail.
- **M13** the `unverifiable` reasons are dropped from the report — tests 9,
  12, and 13 fail.
- **M14** the CLI prints a traceback instead of a JSON error object — test 18
  fails.
- **M15** the reconciliation rewrites `summary.json`'s other keys — test 16
  fails.

Run the whole set again, alone and reverted, against the final tree, and
report each failure with the test that caught it.

## Documentation

Re-derive every `path:line` after the last edit, by hand, and read each cited
line by content. The checker proves a path exists and a line is in range; it
does not prove the line says what is claimed.

- **`docs/HARNESS_FRAMEWORK.md:32` — the CONTEXT row.** Add the citations for
  the new module (`overseer/reconcile.py`: the reader, the comparison, the
  verdict) and for the factory lines that read the record back, write the
  report, and record the event. Extend the verdict honestly: a successor can
  now read the record back and reconcile it — the factory compares the record
  with the ledger row (the job's identity, state, detail, specification hash,
  and run id), with the contract the ledger stored (the three identifier
  lists), with the digest the ledger recorded for the record file, and with
  the workspace (the HEAD commit and whether the worktree is dirty); it
  reports a closed list of disagreements, each naming what the record says and
  what the authority says, with a verdict of `agree`, `disagree`, or
  `unverifiable`; the reconciliation is a read-only report — it records a
  disagreement and does not resolve it, it re-verifies nothing, and it changes
  no attempt's outcome. Keep the verdict word `partial`.

  The **Next increment** cell becomes exactly this, and it must be true after
  the increment:

  > the reconciliation reports a disagreement and nothing acts on it, and it
  > never re-reads the run's own results: the completed, failing, and not-run
  > identifier lists are checked against the contract the ledger stored but
  > not against the exit codes the commands actually produced, so a record
  > that was written wrongly and digested faithfully is reported as agreeing;
  > the ledger also holds one evidence pointer per job, so only the latest
  > run's record is reachable through it

- **`docs/HARNESS_FRAMEWORK.md:84-147` — "What this framework does not
  claim."** Add one bullet, next to the handoff-record bullet at lines
  119-123:

  > - The reconciliation is a read-only report. It records a disagreement
  >   between the handoff record, the ledger row, and the workspace, and it
  >   does not resolve one: it re-verifies nothing, it re-runs and re-accepts
  >   nothing, it does not change the job's state or an attempt's outcome, and
  >   the ledger row and the workspace stay the authority. A workspace that
  >   moved on after the attempt is reported as an unanchored revision, which
  >   is not proof that the record is wrong. `overseer/reconcile.py:<line>`

  The cited line must be re-derived after the last edit.

- **The other five pillar rows** (`docs/HARNESS_FRAMEWORK.md:31, 33, 34, 35,
  36`): re-derive every citation that moved. **No verdict changes.**

- **`README.md:80-100`**: one paragraph after the `handoff.json` paragraph,
  describing the reconciliation: the successor-facing command, the three
  things it compares, the closed list of nine disagreement kinds, the three
  verdicts, the fact that it is a read-only report that records a
  disagreement and does not resolve one, and that the context manifest is not
  rewritten because its digest is already in the ledger.

- **`WORK_LOG.md`**: a new `###` section after line 2974, in the house voice
  of the last section (2842-2974). It must contain:
  - the objective quoted, and the pillar choice with the reason;
  - the ten decisions, including the two that depart from the brief's
    wording — the base-commit authority (the `jobs` table has no commit
    column, so the revisions are anchored in the workspace) and the context
    manifest not being rewritten (its digest is already recorded in the
    ledger) — each with its reason;
  - the commands and their **real** output;
  - the new test count and the new reference count;
  - every mutation M1-M15 with the test it broke;
  - the red-green separation evidence: the SHA-256 of `tests/test_factory.py`
    at the end of the red phase and at the end of the green phase, and the
    statement that they are equal;
  - the limits that remain, including that the reconciliation never re-reads
    the run's own results and that the ledger holds one evidence pointer per
    job;
  - the statement that the prompt was written by the dedicated
    prompt-writing agent and executed by the primary agent.

## Execution order: five phases

The phases are separated on purpose, and the boundary between the first two is
mandated by `AGENTS.md:58`.

**Phase 0 — read the ground truth.** Re-read
`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299` and the CONTEXT row at
`docs/HARNESS_FRAMEWORK.md:32`. Re-measure every line reference this prompt
gives. Run `python3 scripts/check` and
`python3 scripts/check-doc-references` and record their real output.

**Phase 1 — red. `tests/` is writable; no implementation file is written.**
Write only the new test class in `tests/test_factory.py`. Run it and show it
failing, with the real output (the expected failure is an import or an
attribute error, because `overseer.reconcile` and
`Factory.reconcile_handoff` do not exist yet). Record the SHA-256 of
`tests/test_factory.py` at the end of this phase:

```text
sha256sum tests/test_factory.py
```

**Phase 2 — green. `tests/` is READ-ONLY.** Implement `overseer/reconcile.py`,
the factory surface, and the CLI. Do not modify `tests/test_factory.py` in
this phase. If a test's expectation turns out to be wrong, stop, go back to
Phase 1, fix the test there, record the phase change and the reason in the
work log, and re-run Phase 1's red check before continuing. At the end of
this phase, `sha256sum tests/test_factory.py` must print the same digest as
in Phase 1; if it does not, the separation was broken and the increment is not
acceptable.

**Phase 3 — mutation proof.** Each mutation edits implementation code only.
Show the failing test, revert, and record it.

**Phase 4 — documentation.** The pillar row, the does-not-claim bullet, the
other rows' re-derived citations, the README paragraph, and the work-log
section.

**Phase 5 — verification and commit.** Run the verification commands below,
commit the allowed paths explicitly, and report.

## Acceptance criteria (observable)

1. `HEAD` is `fcf5586` at the start, and the operator's `AGENTS.md` and
   `HARDENING_BLUEPRINT.md` are neither edited nor committed.
2. `python3 scripts/check` passes: the 350 baseline tests unchanged, plus at
   least the fifteen new ones. The count is reported.
3. `python3 scripts/check-doc-references` passes and the count is **not
   below 189**. The count is reported.
4. `overseer/reconcile.py` exists, imports nothing from `overseer.factory` and
   nothing from `overseer.codemap`, starts no process, and reads no ledger:
   `grep -n "overseer.factory\|overseer.codemap\|subprocess" overseer/reconcile.py`
   prints nothing.
5. `python3 -m overseer.factory reconcile-handoff <id>` reconciles a run and
   prints the report; an unknown job id prints `{"error": ...}` and exits 1
   with no traceback.
6. The report carries the record's path and digest as read back, the ledger
   row's facts, the workspace's facts, the closed list of disagreements each
   naming both sides, and a verdict of `agree`, `disagree`, or `unverifiable`.
7. Every one of the nine disagreement kinds is reachable, and the test that
   proves it is named.
8. `unverifiable` is never reported as `agree`: a missing record, a malformed
   record, a JSON array, a wrong-typed field, a workspace that is not a git
   repository, and git unavailable each yield `unverifiable` with the real
   reason.
9. The reconciliation changes no job state, changes no attempt's outcome,
   rewrites no `handoff.json`, and touches no other key of `summary.json`.
10. The workspace is only read: no git command the reconciliation causes to
    run writes to the workspace, the index, or a ref.
11. The result is written to `reconciliation.json` in the run's evidence
    directory, added to `summary.json` under the key `reconciliation`, and
    recorded as exactly one `reconciliation` event; the three agree, and the
    context manifest is byte-identical before and after.
12. No ledger table, column, or row type is added.
13. M1-M15 each fail the suite, alone and reverted, and the failing test is
    named for each.
14. The red-green separation held: the SHA-256 of `tests/test_factory.py` is
    the same at the end of Phase 1 and at the end of Phase 2.
15. The new module stays under 300 lines and the factory's additions stay far
    below 15% of `overseer/factory.py`'s 2304 lines.
16. The CONTEXT row of `docs/HARNESS_FRAMEWORK.md:32` records the increment,
    its verdict, its citations, and the new next increment quoted above; the
    does-not-claim list carries the new bullet; the other five rows' verdicts
    are unchanged and their citations are re-derived.
17. `README.md` carries the new paragraph, and `WORK_LOG.md` carries the new
    section with everything listed above.
18. One commit containing the increment and this prompt file. After it,
    `git status --short` prints only the operator's ` M AGENTS.md` and
    `?? HARDENING_BLUEPRINT.md`.

## Constraints

- Python 3 standard library only. No new dependency.
- One primary editor.
- File this increment against exactly the CONTEXT row. No new objective.
- No change to the verifiers, the publish gate, the state machine, the ledger
  schema, the monitor, the codemap, the recall, the skills reader, the
  workspace-diff capture semantics, or the handoff record's own shape.
- The reconciliation is a read-only report. It resolves nothing.
- No invented values, no estimated tokens or costs, no fabricated identifiers,
  no invented benchmark results, token counts, costs, or savings.
- No sandbox claims. No claim that the reconciliation is a review, an
  acceptance, or a repair.
- Do not touch the live tmux server, the live monitor service, the live
  factory ledger at `~/.local/state/overseer/factory`, `config.json`, or the
  monitor's modules. Run every check through `scripts/check`, which isolates
  `TMUX_TMPDIR`.
- Every test uses a temporary database and a temporary workspace, never the
  default runtime database (`overseer/factory.py:24`).
- `tests/` is read-only in Phase 2, and no mutation may edit a test.

## Verification commands

```text
git status --short
python3 scripts/check
python3 scripts/check-doc-references
grep -n "overseer.factory\|overseer.codemap\|subprocess" overseer/reconcile.py
grep -rn "TODO\|FIXME\|XXX" overseer/reconcile.py overseer/factory.py
git diff --check
git diff --stat
git status --short          # after the commit: only the operator's two files
```

## Allowed work and stopping condition

Allowed: a new `overseer/reconcile.py`; `overseer/factory.py` (the
`reconcile_handoff` method, the `reconcile-handoff` CLI subcommand, and the
import of the new module); `tests/test_factory.py` (the new class only, and
only in Phase 1); `docs/HARNESS_FRAMEWORK.md` (the CONTEXT row, the
does-not-claim bullet, and re-derived citations elsewhere); `README.md`;
`WORK_LOG.md`; and this prompt file.

Commit with a message in the repository's voice, for example "Reconcile the
handoff record against the ledger row and the workspace", ending with the
attribution lines the session supplies. Stage the allowed paths explicitly:

```text
git add overseer/reconcile.py overseer/factory.py tests/test_factory.py \
        docs/HARNESS_FRAMEWORK.md README.md WORK_LOG.md \
        CONTEXT_HANDOFF_RECONCILE_NEXT_PROMPT.md
git commit -m "..."
```

Stop after this one increment and its commit: a successor can read a persisted
`handoff.json` back, the factory compares it with the ledger row and with the
workspace, the report names both sides of every disagreement it finds, the
verdict is one of three closed values and `unverifiable` is never an
agreement, nothing is resolved and no outcome changes, the workspace is only
read, M1-M15 each fail the suite, the docs are current with re-derived
citations, both commands pass, the red-green separation held, and the tree
holds only the operator's two files. Report the commit hash, the diff
summary, the command outputs, the new test and reference counts, the mutation
results, the red-green evidence, and the limits that remain.

This stopping condition ends this prompt, not the objective: report
`step_done` with the CONTEXT row's **new** "Next increment" (quoted in the
Documentation section above) in `remaining`. If the same failure recurs twice
with no new evidence, stop and report it instead of retrying.

End the report with the status block `AGENTS.md` names:

```yaml
STATUS: [SUCCESS | STUCK_NEEDS_ESCALATION]
TESTS_PASSED: [TRUE | FALSE]
FILES_MODIFIED: [<list of files>]
NEXT_AGENT_INSTRUCTION: "<clear self-contained prompt for next iteration>"
```
