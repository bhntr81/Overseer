# Persist the blueprint's handoff record for every attempt

Status: **ready to execute at commit `9a88598`**. This prompt was written by
the dedicated prompt-writing agent of the Overseer project. The primary agent
executes it; writing it is not completion.

The user's request, verbatim:

> Execute the next authorized step from AGENTS.md:
>
> Persist the blueprint's handoff record in `docs/HARNESS_FRAMEWORK.md` (for
> the CONTEXT row) based on evidence from commit 9a88598—including candidate
> revision, completed/failing acceptance IDs, and next eligible
> action—leaving unobservable fields marked unmeasured. Verify execution with
> the test suite (`python3 scripts/check`) and `scripts/check-doc-references`
> before reporting.

## What this increment is

The blueprint's handoff sentence is
`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299`:

> On handoff, persist objective, base and candidate revisions, completed
> acceptance IDs, failing IDs, environment state, commands actually run,
> unresolved effects, remaining budget, and next eligible action. The successor
> checks the ledger and workspace before trusting the summary. If they
> disagree, reconcile.

The CONTEXT row of `docs/HARNESS_FRAMEWORK.md:32` names this as its next
increment: *"persist the blueprint's handoff record
`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299` from the run's own evidence —
candidate revision, completed and failing acceptance IDs, and next eligible
action — and keep every field the factory cannot observe marked unmeasured."*

So this increment does two things, and the two must not be confused:

1. **The code.** The factory persists that record, per attempt, from that
   attempt's own evidence, and nothing else changes about how an attempt is
   judged.
2. **The map.** The CONTEXT row of `docs/HARNESS_FRAMEWORK.md:32` records the
   increment: its verdict, its citations, its does-not-claim bullet, and its
   next increment. The record itself is *not* written into the markdown; it is
   written into the run's evidence directory at run time.

The record is the CONTEXT pillar's own artifact. It is context: it never
changes an attempt's outcome, and nothing judges an attempt by it.

## Which pillar row this is filed against

Exactly one: **CONTEXT**, `docs/HARNESS_FRAMEWORK.md:32`. The other five rows'
verdicts do not change; only citations that moved are re-derived.

## Precondition: start from the directives commit

This prompt was written against commit `9a88598` ("Add the factory agent
directives to the project entry point"), branch `main`.

1. `git status --short` prints only `?? CONTEXT_HANDOFF_RECORD_NEXT_PROMPT.md`
   (this prompt itself). If the tree is dirty in any other way, stop and
   report `needs_input`.
2. `HEAD` is `9a88598`. If it is not, stop and report `needs_input`.
3. Re-run both baseline commands and use their counts in place of 335 / 183:
   - `python3 scripts/check` -> `Ran 335 tests ... OK`
   - `python3 scripts/check-doc-references` -> `183 references checked in HARNESS_FRAMEWORK.md`
4. **Re-measure every line reference below** against that commit. The
   references were measured by the prompt-writing agent; the review may have
   moved them. A reference that names the wrong thing is a defect.

Review lessons carried forward, part of the acceptance:

1. **Line citations drift.** Re-derive every citation by hand after the last
   edit, in every row and passage the increment touches. The project's checker
   proves a cited line exists, not that it names the right thing.
2. **A test is evidence only if a plausible wrong implementation fails it.**
   Run the mutations of section 9 one at a time; show the suite failing; name
   the failing test; revert.
3. **Counts describe what is shown.** The number of acceptance identifiers
   reported as completed, failing, or not run describes this run's commands and
   this run's contract, and the counts say which they are.
4. **Evidence is scoped to this attempt.** A record describes the attempt that
   produced its run's evidence. It is never merged with another attempt's
   record, and a later attempt never rewrites an earlier one.
5. **Words claim only what was observed.** A field the factory cannot observe
   is marked unmeasured with the reason. It is never estimated, never guessed,
   and never filled from a value that was observed at a different moment.
6. **An exception must not leave a job stuck** (the `c1c9637` review). The
   handoff record is written after the attempt's outcome is known and must
   never be able to change that outcome or leave a job in a non-final state.
7. **Departures from the prompt are recorded** (the `43be2e5` review). Every
   deviation, and every read-only command the increment needed that the prompt
   did not name, goes into the work log.

## The three decisions this increment makes

The prompt must state these in writing; they are settled here and are part of
the acceptance.

### 1. Where the record lives

**A new file `handoff.json` in the run's evidence directory**, written next to
`context.json` and `summary.json`, plus **a `handoff` block in
`context.json`** that names the file, its SHA-256, and the record's headline
facts.

The evidence directory is created per run at `overseer/factory.py:2057`
(`self.path.parent/'runs'/run_id`) with a fresh `run_id` from
`overseer/factory.py:2056`, so a file inside it is scoped to one attempt by
construction. A successor reads one file, `handoff.json`, and has the whole
record; the manifest points at it and carries its digest.

The `handoff` block in `context.json` carries: `path`, `sha256`, `state`,
`base_revision`, `candidate_revision`, `completed_acceptance_ids`,
`failing_acceptance_ids`, `not_run_acceptance_ids`, `next_eligible_action`,
and `unmeasured`. The block is a projection of the record, and a test asserts
the two agree.

### 2. Whether the ledger records its path and digest

**Yes, without changing the ledger schema.** The ledger's schema is frozen
for this increment, so the record is referenced the way `context.json` and
`diff.json` already are:

- `summary.json` gains `handoff: {'path': ..., 'sha256': ...}`, beside the
  existing `context_manifest` and `workspace_diff` entries
  (`overseer/factory.py:2170-2172` and `:2187-2188`).
- The `events` table gains one row, `handoff`, carrying the path and the
  digest, beside the existing `context_manifest` event
  (`overseer/factory.py:2191-2192`). `event()` is
  `overseer/factory.py:461-463`; the table is `overseer/factory.py:414-416`.
  No table, column, or row type is added.
- The job row's `evidence` column already names the run's evidence directory
  (`overseer/factory.py:2095-2096`).

The `jobs`, `attempts`, `events`, `memory_records`, and `approvals` tables
(`overseer/factory.py:409-455`) are unchanged.

### 3. How the record is scoped to one attempt

The record is written **once per run**, into that run's own evidence
directory, from that run's own facts:

- the spec of this job, this run's `results`, this run's workspace-diff
  receipt, this run's attempt-start repository identity, and the final state
  and detail of this run;
- it names `job_id`, `run_id`, `spec_hash`, `epoch`, and `mode`, so a
  successor can bind it to the ledger row and to the workspace;
- it carries `attempt.attempt_id` and `attempt.lease_generation` **only when
  the ledger holds one for this run**, and otherwise says why there is none
  (the command mode reserves no attempt lease: the `attempts` table is written
  by `_allocate_lease`, `overseer/factory.py:1570-1591`, which the command path
  never calls);
- it carries a `scope.rule` string that says: this record describes the
  attempt that produced this run's evidence; it is never merged with another
  run's record; a later attempt of the same job writes its own record in its
  own run directory;
- a later run of the same job leaves an earlier run's `handoff.json`
  byte-identical. A test proves it.

## The ten blueprint fields and where each one comes from

Every field is an object `{'value': ..., 'source': ...}`. When the factory
cannot observe a field, `value` is `null` and `source` begins with
`unmeasured: ` and gives the reason. A top-level `unmeasured` list names
every field whose value is null, plus every sub-name a field marks
unmeasured. A test asserts that every null value in the record is named in an
`unmeasured` list and carries a reason.

| blueprint field | source | when it is unmeasured |
| --- | --- | --- |
| objective | the spec's `objective` field | never |
| base revision | the attempt-start repository identity: `git rev-parse HEAD` observed at attempt start, before the implementation command | the workspace is not a git repository, or git is unavailable; the reason is the identity probe's own reason |
| candidate revision | the workspace-diff receipt's `head_after`, when the receipt says `head_moved` | HEAD did not move during the attempt, and an uncommitted worktree is not a revision; or no workspace diff was captured |
| completed acceptance IDs | the contract's identifiers whose acceptance command ran and exited 0 | the stored job names no acceptance identifiers |
| failing acceptance IDs | the identifier of the acceptance command that ran and failed or timed out | the stored job names no acceptance identifiers |
| environment state | the runner's own facts: the mode, the epoch, the per-command timeout; tokens and cost are null and never estimated | the sub-facts `tokens`, `cost_usd`, and `environment_digest` are unmeasured and the record says why |
| commands actually run | this run's results, projected to stage, argv, exit code, timeout, elapsed time, and log path | never; the list is empty only when the mode runs no argument-vector command, and the record says so |
| unresolved effects | nothing: the factory observes no effect outside the workspace and the ledger | always unmeasured; the reason says the contract's `external_effects` are a declaration and not an observation, and that the patch receipt shows what the workspace held, not which process made a change |
| remaining budget | nothing: the contract declares an allowance, but the factory tracks no consumption | always unmeasured; the reason names the declared `budget.repair_allowance` and says the consumed count is not tracked, so what remains cannot be derived |
| next eligible action | the run's final state and the run's mode, under the blueprint's bounded-repair policy | never; but the action names what the factory could not decide |

The record also carries `not_run_acceptance_ids`, one step beyond the
blueprint's ten. The blueprint names completed and failing identifiers; the
brief for this increment requires that an identifier whose command **never
ran** is not counted as failing and is distinguishable. The record therefore
carries three identifier lists, and a test asserts they are disjoint and that
their union is the contract's identifier list.

## The acceptance-ID accounting

The contract fixes the mapping: `acceptance_ids` must have the same length as
`spec['checks']` and its entries must be unique
(`overseer/factory.py:242-251`), so `acceptance_ids[i]` names
`spec['checks'][i]`.

The run loop runs `[spec['implementation'], *spec['checks']]`
(`overseer/factory.py:2137`); index 0 is the implementation, index `i+1` is
`spec['checks'][i]`. Each result is tagged `stage` at
`overseer/factory.py:2149` (`'implementation'` for index 0, `'acceptance'`
otherwise). The **loop breaks at the first failing command**
(`overseer/factory.py:2152-2154`), so the acceptance results that exist are
a prefix of the checks and the rest never ran.

The accounting, in this order:

- `ran` = the results whose `stage` is `'acceptance'`, in order;
- `ids` = the contract's `acceptance_ids`, or `[]` when the stored job names
  none (`acceptance_ids_source` is `'absent'`, as the manifest computes it at
  `overseer/factory.py:1106` and `1178`);
- for each `j` below `len(ids)`: if `j < len(ran)`, the outcome of `ids[j]` is
  `ran[j]`'s — **completed** when `exit_code == 0` and it did not time out,
  **failing** when it exited non-zero or timed out; if `j >= len(ran)`, the
  identifier is **not run**;
- the implementation command is not an acceptance command. A failed or timed
  out implementation leaves every identifier not run, and the failing list
  empty. The next eligible action's reason names the implementation command;
- if `len(ran) > len(ids)`, the surplus results are still listed under
  `commands_actually_run` but no identifier is invented for them, and the
  identifier lists' source says so.

## The next eligible action

A closed vocabulary, derived from the run's final state and the run's mode.
The rule for the mode comes first: the three controller-owned modes are
controller-owned slices, not task attempts, so the factory has no task-level
step for them.

| mode | final state | `action` | `decided_by` | the reason must name |
| --- | --- | --- | --- | --- |
| `command` | `passed` | `product_review` | the successor | that every acceptance command exited 0, and that a passed attempt is a candidate and not a product or release acceptance (`docs/FACTORY_EXECUTION.md:45-46`) |
| `command` | `failed` | `bounded_repair` | the successor | the observed evidence: the implementation command's exit code, or the identifier and exit code of the failing acceptance command, or the run's own detail when no command produced a result; and that the blueprint's policy is a bounded repair within the same task budget (`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:352`) |
| `fixture`, `fake_provider`, `isolation_probe` | any | `controller_decided` | the factory | the mode, and that the mode's own receipt (`verification.json`, `isolation-result.json`) is the authority and the factory has no further step for this attempt |

Each action carries `reason` and an `unmeasured` list naming the facts that
bear on the decision and could not be observed:

- `product_review`: `unresolved_effects`;
- `bounded_repair`: `remaining_budget`, `unresolved_effects`, and
  `failure_class` — the factory records the exit code and the log path, not
  the class of the failure, and the blueprint's own failure-class table
  (`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:356-367`) is what a successor
  reads;
- `controller_decided`: none.

`decided_by` is `the factory` or `the successor` and never anything else. A
record must not say the factory decided something it cannot decide.

## Repository and paths

- Repository: `/home/kali/Programming/Projects/Overseer`, branch `main`.
- Python 3 standard library only. No new dependency. `git` is used read-only
  by the code under test.

Measured at `9a88598`; re-measure (precondition 4):

| Path and line | What it is now |
| --- | --- |
| `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299` | the handoff sentence this increment persists |
| `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:352` | the bounded-repair policy: one implementation attempt, at most two repair attempts within the same task budget |
| `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:356-367` | the blueprint's failure-class table; a successor reads it, the factory does not apply it |
| `overseer/factory.py:202-204` | the contract's `repair_allowance`, validated as an integer 0..10; the declared allowance, never the consumed count |
| `overseer/factory.py:242-251` | the acceptance-ID contract: one identifier per acceptance command, unique |
| `overseer/factory.py:326-337` | `repository_identity(workspace)`: the root, `base_commit`, and the source string `git rev-parse HEAD observed at attempt start` |
| `overseer/factory.py:409-455` | the ledger schema, frozen for this increment |
| `overseer/factory.py:461-463` | `event()`: the append-only event log |
| `overseer/factory.py:962` | `recall()` probes the repository identity at attempt start |
| `overseer/factory.py:989` | the recall's return value carries that identity under `repository` |
| `overseer/factory.py:1060-1061` | `_context_manifest(...)`, the CONTEXT pillar's manifest writer |
| `overseer/factory.py:1064` | the manifest's `acceptance_ids` from the contract |
| `overseer/factory.py:1094-1105` | the manifest's `commands_actually_run` projection: stage, argv, exit code, timeout, elapsed time, log path; results without `argv` are skipped |
| `overseer/factory.py:1106` | `acceptance_source`: `contract` or `absent` |
| `overseer/factory.py:1109-1119` | the candidate revision rule: measured only when the receipt says `head_moved`; otherwise unmeasured with a reason |
| `overseer/factory.py:1176` | the manifest's `repository` block — **read this line again before editing it**; see section 1 below |
| `overseer/factory.py:1177-1179` | the manifest's `acceptance_ids`, `acceptance_ids_source`, `commands_actually_run` |
| `overseer/factory.py:1180-1184` | the manifest's `environment` block: the timeout, and tokens and cost as null |
| `overseer/factory.py:1279-1283` | the manifest's `candidate_revision` and its `unmeasured` list |
| `overseer/factory.py:1335-1353` | the guarded-capture pattern: an exception becomes a recorded reason, never a failure |
| `overseer/factory.py:1355-1389` | `_record_diff`: how a receipt is written, digested, and recorded as an event |
| `overseer/factory.py:1570-1591` | `_allocate_lease`: the only writer of the `attempts` table; the command path never calls it |
| `overseer/factory.py:1727-1762` | `publish()`: valid only for a fake-provider attempt |
| `overseer/factory.py:2056-2058` | the per-run `run_id` and evidence directory |
| `overseer/factory.py:2063-2068` | the recall is taken at attempt start; `recall_info` carries the records, the path, and the digest |
| `overseer/factory.py:2095-2096` | the job row's `evidence` column names the run's evidence directory |
| `overseer/factory.py:2137` | the command loop over `[implementation, *checks]` |
| `overseer/factory.py:2149` | the result's `stage`: `implementation` or `acceptance` |
| `overseer/factory.py:2152-2154` | the loop breaks at the first failing command, so later checks never run |
| `overseer/factory.py:2155-2156` | the `else` branch: every command exited 0, and the detail says a product review is still required |
| `overseer/factory.py:2165-2172` | the diff receipt is recorded and `summary['workspace_diff']` is set |
| `overseer/factory.py:2181-2189` | the manifest is built and written, then `summary['context_manifest']` and `summary.json` |
| `overseer/factory.py:2191-2193` | the `context_manifest` event and the final `transition` |
| `overseer/workdiff.py:157` | `snapshot(workspace)`: the read-only state of a git workspace |
| `overseer/workdiff.py:340` | `capture(before, workspace)`: the patch and the receipt |
| `overseer/workdiff.py:449-450` | the receipt's `head_before`, `head_after`, and `head_moved` |
| `overseer/workdiff.py:22` | the capture bounds |
| `tests/test_factory.py:30-51` | `attach_contract`: the helper that gives a spec a valid contract block |
| `tests/test_factory.py:54-61` | `store_legacy_job`: stores a job the way the ledger held it before the contract rule |
| `tests/test_factory.py:1274-1337` | `class ContextTests`, with `command_spec`, `contract`, `manifest_of`, and a `git` helper |
| `tests/test_factory.py:1350` | the manifest's `version` is asserted to be 1; it stays 1 |
| `tests/test_factory.py:1357-1374` | the existing test of the manifest's `commands_actually_run`; it must keep passing unchanged |
| `tests/test_factory.py:1412-1416` | the existing test of the manifest's `repository` block: `present`, `base_commit`, `root`, and the `rev-parse` source string; it must keep passing unchanged |
| `tests/test_factory.py:1447-1458` | the existing test that the manifest marks unmeasured values as unmeasured, and that the manifest carries no stdout or stderr |
| `tests/test_factory.py:3389-3467` | `class WorkspaceDiffTests`: a git workspace with a committed base, and the `spec`/`run_spec` helpers |
| `docs/HARNESS_FRAMEWORK.md:32` | the CONTEXT row |
| `docs/HARNESS_FRAMEWORK.md:84-142` | "What this framework does not claim" |
| `docs/HARNESS_FRAMEWORK.md:154-155` | "This file stays a map. Prescriptions live in the blueprint; evidence lives in the execution record." |
| `docs/HARNESS_FRAMEWORK.md:130-131` | "A factory run marked passed is not product or release acceptance." |
| `docs/FACTORY_EXECUTION.md:45-46` | "`passed` requires every command to exit successfully and is explicitly not product/release acceptance." |
| `README.md:45-161` | the "Software factory direction" section; the manifest paragraph begins at line 84 |
| `WORK_LOG.md:2819` | the last section; the file ends at 2840 |

## Required behavior

### 1. The attempt-start base revision, and a mislabelled observation

The prompt-writing agent measured this at `9a88598` and the primary agent
must re-measure it before acting on it:

> The manifest's `repository` block is built by calling
> `repository_identity(workspace)` **at manifest-write time**
> (`overseer/factory.py:1176`, reached from `overseer/factory.py:2181`,
> after the command loop). The identity's own `base_commit_source` string says
> *"git rev-parse HEAD observed at attempt start"*
> (`overseer/factory.py:337`), but the manifest's copy is observed **after**
> the attempt. In a probe where the attempt committed, the manifest's
> `base_commit` was the **new** commit, while the recall's copy — taken at
> attempt start by `recall()` at `overseer/factory.py:962`, reached from
> `overseer/factory.py:2063` — was the **old** one. The manifest therefore
> labelled a post-attempt HEAD as the attempt-start base commit.

The handoff record's base revision must be the attempt-start commit, and the
manifest's copy must be that same commit, so the two artifacts cannot
disagree and the existing source string becomes true.

Required:

- `recall_info` (`overseer/factory.py:2067-2068`) carries the attempt-start
  identity it already holds, under `repository`.
- `_context_manifest` uses that identity for its `repository` block instead of
  probing again. When no attempt-start identity is available, the block is
  `{'present': False, 'reason': 'the attempt-start repository identity was not observed'}` — never a fresh, later probe presented as the base.
- The record's `base_revision.value` equals the manifest's
  `repository.base_commit`, and the record's `source` says the revision was
  observed at attempt start, before the implementation command.
- The manifest's `repository` block keeps its existing keys
  (`present`, `root`, `base_commit`, `base_commit_source`) and its existing
  source string, so `tests/test_factory.py:1412-1416` keeps passing
  unchanged.
- The record's `candidate_revision` comes from the diff receipt's
  `head_after` when `head_moved` is true, and is otherwise unmeasured with the
  manifest's own reason (`overseer/factory.py:1115-1119`).

A test proves the distinction: an attempt that commits records the
attempt-start commit as the base revision, the new commit as the candidate
revision, and the manifest's `repository.base_commit` as the same attempt-start
commit.

### 2. A new module `overseer/handoff.py`

In the style of `overseer/workdiff.py` and `overseer/skills.py`: module
constants for every bound, small functions whose docstrings state the reason,
dict results, a `reason` wherever something could not be done.

It imports nothing from `overseer.factory` and nothing from
`overseer.codemap`; it is a pure function of facts the factory hands it.

```python
def commands(results):
    """Return the commands this run actually ran, as the manifest projects them."""

def build(job_id, run_id, spec, spec_hash, epoch, results, receipt,
          base_identity, state, detail):
    """Return the blueprint's handoff record for one attempt."""
```

- `commands(results)` returns the same projection the manifest builds at
  `overseer/factory.py:1094-1105`: `stage`, `argv`, `exit_code`,
  `timed_out`, `elapsed_seconds`, `log`; results without `argv` are skipped.
  The manifest and the record use it, so the two lists cannot drift, and
  `tests/test_factory.py:1357-1374` keeps passing unchanged.
- `build(...)` returns the record. It never raises for a missing identity, a
  missing receipt, a result without `argv`, or a spec without a contract: it
  records the reason in the field that could not be measured.
- The record's shape:

```python
{
  'version': 1,
  'kind': 'handoff_record',
  'job_id': ..., 'run_id': ..., 'spec_hash': ..., 'epoch': ..., 'mode': ...,
  'state': ..., 'detail': ...,
  'attempt': {'attempt_id': ..., 'lease_generation': ..., 'source': ...},
  'scope': {'rule': ...},
  'objective': {'value': ..., 'source': ...},
  'base_revision': {'value': ..., 'source': ...},
  'candidate_revision': {'value': ..., 'source': ...},
  'completed_acceptance_ids': {'value': [...], 'source': ...},
  'failing_acceptance_ids': {'value': [...], 'source': ...},
  'not_run_acceptance_ids': {'value': [...], 'source': ...},
  'acceptance_ids_source': 'contract' | 'absent',
  'environment_state': {'value': {...}, 'source': ..., 'unmeasured': [...]},
  'commands_actually_run': {'value': [...], 'source': ...},
  'mode_result': {...} | None,
  'unresolved_effects': {'value': None, 'source': 'unmeasured: ...'},
  'remaining_budget': {'value': None, 'source': 'unmeasured: ...'},
  'next_eligible_action': {'value': {'action': ..., 'reason': ...,
                                     'decided_by': ...},
                           'source': ..., 'unmeasured': [...]},
  'unmeasured': [...],
  'note': ...,
}
```

- `mode_result` carries the controller-owned mode's own result — `stage`,
  `exit_code`, `timed_out`, and `detail` where the mode recorded one — for
  `fixture`, `fake_provider`, and `isolation_probe`, and is `None` in command
  mode. It never carries command output.
- The record's `note` says, in the blueprint's terms, that the ledger row and
  the workspace are the authority: the successor checks the ledger and the
  workspace before trusting this summary, and reconciles a disagreement. It
  also says that a run that was interrupted leaves no record, so a missing
  `handoff.json` is itself information.
- Bounds, as module constants, recorded in the record's `limits`: the
  identifier lists and the command list are bounded by the contract and by
  `spec['checks']`, which is at most 20 commands
  (`overseer/factory.py:386`); the objective and the reason strings are
  bounded in length, and a string that is cut is marked as cut rather than
  silently shortened.
- The record carries no stdout, no stderr, and no `output_truncated` key, the
  same way the manifest does not
  (`tests/test_factory.py:1454-1457`).

### 3. Writing the record in `run_one`

In `run_one`, command mode and the three controller-owned modes alike:

- after the command loop and the diff receipt are recorded
  (`overseer/factory.py:2165-2166`), and before the manifest is built
  (`overseer/factory.py:2181`), build the record with `handoff.build(...)`
  and write it to `evidence/'handoff.json'`, in the style of
  `overseer/factory.py:1371-1378` (write, then take the SHA-256 of the bytes
  on disk);
- the write is guarded the way `_diff_step` and `_diff_capture` are
  (`overseer/factory.py:1335-1353`): any exception becomes a recorded reason,
  never a failed attempt, and never a job left in a non-final state. On
  failure no file is written, the manifest's `handoff` block records
  `written: False` and the reason, and the attempt still reaches its final
  state;
- the manifest's `handoff` block carries `path`, `sha256`, `written`,
  `state`, `base_revision`, `candidate_revision`,
  `completed_acceptance_ids`, `failing_acceptance_ids`,
  `not_run_acceptance_ids`, `next_eligible_action`, and `unmeasured`, taken
  from the record;
- `summary['handoff']` carries `path` and `sha256`
  (`overseer/factory.py:2187-2188`);
- one event `handoff` carries the path and the digest
  (`overseer/factory.py:2191-2192`);
- the record's `state` and `detail` equal `summary.json`'s `state` and
  `detail` (`overseer/factory.py:2167-2169`), and a test asserts it.

The `final` state and `detail` are already known when the record is built
(`overseer/factory.py:2110-2111`, `:2153`, `:2156`); the record is written
before the final `transition` at `overseer/factory.py:2193`, exactly as
`summary.json` is written before it (`overseer/factory.py:2189`). The ledger
row stays the authority and the record says so.

The record is written where the manifest is written, so a run that returns
early leaves neither: the fake provider's `interrupted` scenario returns at
`overseer/factory.py:2122-2125`, and an interrupted worker leaves the job for
`reconcile()` (`overseer/factory.py:739-757`) or `resolve()`
(`overseer/factory.py:759-773`).

### 4. What stays true

- The handoff record never changes an attempt's outcome, and nothing judges an
  attempt by it. The verifier, the publish gate, the state machine, the
  ledger schema, the monitor, the codemap, the recall, the skills reader, and
  the workspace-diff capture semantics are unchanged.
- Every field is traceable to this run's evidence, or is explicitly
  unmeasured with a reason. No field is estimated, guessed, or carried over
  from another run.
- A record is written once, into this run's evidence directory, and a later
  run of the same job leaves it byte-identical.
- The record carries no command output and no secret-named file's content.
- The manifest's `version` stays 1 (`tests/test_factory.py:1350`).

## Tests

Add a new class `class HandoffRecordTests(unittest.TestCase)` to
`tests/test_factory.py`, after `class WorkspaceDiffTests`
(`tests/test_factory.py:3389-3467`), reusing its git workspace, `spec`, and
`run_spec` helpers. Use `attach_contract`
(`tests/test_factory.py:30-51`) for a spec with a contract and
`store_legacy_job` (`tests/test_factory.py:54-61`) for a job stored before
the contract rule.

At least fifteen tests:

1. A passing command-mode attempt writes `handoff.json` into the run's
   evidence directory, and the record carries the blueprint's ten fields, each
   with a `value` and a `source`.
2. The base revision is the attempt-start commit and the candidate revision is
   the commit the attempt made; the manifest's `repository.base_commit` is the
   same attempt-start commit, and the two differ.
3. The candidate revision is unmeasured with the manifest's reason when the
   attempt does not move HEAD.
4. A failing acceptance check reports that identifier, and only that
   identifier, as failing.
5. The checks after the first failure are reported as not run, and are in
   neither the completed nor the failing list.
6. A failed implementation leaves every identifier not run and the failing
   list empty, and the action's reason names the implementation command.
7. A timed-out acceptance command is failing, and is not completed.
8. A job stored before the contract rule names no identifiers: the three
   identifier lists are empty with the reason, and the commands that ran are
   still listed.
9. The environment state marks `tokens`, `cost_usd`, and `environment_digest`
   unmeasured, with reasons, and no number stands in for them.
10. The unresolved effects and the remaining budget are unmeasured, with
    reasons that name what the factory cannot observe.
11. The next eligible action is `product_review` for a passed command attempt,
    `bounded_repair` for a failed one, and `controller_decided` for a
    controller-owned mode; `decided_by` is never anything but `the factory` or
    `the successor`.
12. A record names only its own run: a second job in the same workspace leaves
    the first run's `handoff.json` byte-identical, and the two records name
    different `job_id`s and `run_id`s.
13. A failing write of the record leaves the attempt's outcome unchanged and
    the job in a final state, and the manifest says why the record is
    missing.
14. The record carries no stdout, no stderr, and no `output_truncated`, and
    every null value in it is named in an `unmeasured` list with a reason.
15. The manifest's `handoff` block, `summary.json`'s `handoff` entry, and the
    `handoff` event agree with the file on disk: the same path, the same
    digest, and the same headline facts.

The record's `state` and `detail` equal `summary.json`'s, and the three
identifier lists are disjoint and cover the contract's identifiers, are
asserted inside the relevant tests.

Mutations — one at a time, show the suite failing, name the failing test,
revert:

- M1 the base revision is taken from the manifest's later probe instead of the
  attempt-start identity (test 2);
- M2 the acceptance identifiers are mapped off by one, so the implementation
  result names the first identifier (test 4);
- M3 the not-run identifiers are counted as failing (test 5);
- M4 a failed implementation is counted as a failing acceptance identifier
  (test 6);
- M5 a timed-out command is not counted as failing (test 7);
- M6 identifiers are invented when the stored job names none (test 8);
- M7 `tokens` or `cost_usd` is given a number (test 9);
- M8 `remaining_budget` is filled with the declared repair allowance (test
  10);
- M9 the next eligible action is always `product_review` (test 11);
- M10 the record merges the previous run's record, or the later run
  overwrites the earlier file (test 12);
- M11 the write of the record is unguarded, so a raising writer leaves the job
  stuck (test 13);
- M12 the record carries the command's output (test 14);
- M13 an unmeasured name is dropped from the `unmeasured` list (test 14);
- M14 the manifest's `handoff` block carries the wrong digest (test 15).

Do not weaken, delete, or rewrite existing tests.

## Documentation

Re-derive every `path:line` after the last edit.

- `docs/HARNESS_FRAMEWORK.md:32` — the CONTEXT row: add the blueprint
  citation `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299`, the code citations
  for `overseer/handoff.py` (`commands`, `build`) and for the `run_one` lines
  that write `handoff.json`, the manifest's `handoff` block, and the event.
  Extend the verdict: every attempt that produces a context manifest now also
  leaves a `handoff.json` in the run's evidence directory, carrying the
  blueprint's ten fields — the objective, the attempt-start base revision, the
  candidate revision when the attempt moved HEAD, the completed, failing, and
  not-run acceptance identifiers, the environment state, the commands actually
  run, the unresolved effects, the remaining budget, and the next eligible
  action — with every field the factory cannot observe marked unmeasured and
  the reason given; the record is scoped to one attempt by its run directory
  and names its `job_id`, `run_id`, and `spec_hash`; the manifest's
  `repository.base_commit` is the attempt-start commit, so the base revision
  in the two artifacts is the same observation. Keep the verdict word `partial`.
  The **Next increment** cell becomes: *"read the persisted handoff record
  back and reconcile it against the ledger row and the workspace — the
  blueprint's 'the successor checks the ledger and workspace before trusting
  the summary; if they disagree, reconcile'
  (`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299`) is still done by hand, and
  no code reads `handoff.json`."*
- `docs/HARNESS_FRAMEWORK.md:84-142` — "What this framework does not claim":
  add one bullet — *the handoff record is a summary of one attempt's own
  evidence. It does not prove which process made a change, it does not
  measure the remaining budget or the unresolved effects, an unmeasured field
  is not measured, and the successor still has to check the ledger and the
  workspace and reconcile a disagreement.* Cite the record's own path.
- `docs/HARNESS_FRAMEWORK.md:36` and the other four rows: re-derive every
  citation that moved. No verdict changes.
- `README.md:45-161` — one paragraph in "Software factory direction" on
  `handoff.json`: the ten fields, the three identifier lists, the
  attempt-start base revision, the unmeasured fields, and the limit that the
  successor must still reconcile.
- `WORK_LOG.md` — a new `###` section after line 2840: the user's request
  quoted, the pillar choice and why, the three decisions (location, the
  ledger's path and digest, the scoping), the rules, the commands and their
  real output, the new test count, M1-M14 with the test each broke, the
  finding that the manifest's `repository.base_commit` was a post-attempt
  observation labelled as the attempt-start one and is now the attempt-start
  one, that every citation was re-derived, and that the prompt was written by
  the dedicated prompt-writing agent and executed by the primary agent.

## Acceptance criteria (observable)

1. Precondition met: a clean tree at `9a88598` apart from this prompt.
2. `python3 scripts/check` passes: the 335 baseline tests unchanged, plus at
   least the fifteen new ones. The count is reported.
3. `python3 scripts/check-doc-references`: every reference resolves, and the
   count is not below 183.
4. Every attempt that writes a `context.json` also leaves a `handoff.json` in
   the same evidence directory, carrying the blueprint's ten fields, with
   every unobserved field null and its reason naming what could not be
   observed.
5. The record's base revision is the attempt-start commit; the candidate
   revision is the post-implementation HEAD when HEAD moved and is otherwise
   unmeasured; the manifest's `repository.base_commit` is the same
   attempt-start commit.
6. The three identifier lists are disjoint, cover the contract's identifiers,
   and an identifier whose command never ran is in none of the completed or
   failing lists.
7. The next eligible action is one of the three closed values, its `reason`
   names the observed evidence, and `decided_by` is `the factory` or `the
   successor`.
8. A second run of the same job leaves the earlier run's `handoff.json`
   byte-identical, and the two records name different runs.
9. The record carries no stdout, no stderr, and no `output_truncated`; every
   null value in it is named in an `unmeasured` list and carries a reason.
10. A failing write of the record leaves the attempt's outcome unchanged and
    the job in a final state.
11. M1-M14 each fail the suite, recorded in the work log with the test each
    broke.
12. `grep -n "overseer.factory\|overseer.codemap" overseer/handoff.py` prints
    nothing.
13. The CONTEXT row of `docs/HARNESS_FRAMEWORK.md:32` records the increment,
    its verdict, its citations, and a next increment that is a real gap, and
    the does-not-claim list carries the new bullet.
14. One commit containing the increment and this prompt file; `git status
    --short` prints nothing after it.

## Constraints

- Python 3 standard library only. No new dependency.
- One primary editor. No other pillar row, no new objective, and no change to
  the verifiers, the publish gate, the state machine, the ledger schema, the
  monitor, the codemap, the recall, the skills reader, or the workspace-diff
  capture semantics.
- File this increment against exactly the CONTEXT row.
- The handoff record is context: it never changes an attempt's outcome, and
  nothing judges an attempt by it.
- No invented values, no estimated tokens or costs, no fabricated identifiers.
- Do not invent benchmark results, token counts, costs, or savings.

## Verification commands

```text
git status --short          # before: only this prompt untracked, at 9a88598
python3 scripts/check
python3 scripts/check-doc-references
grep -n "overseer.factory\|overseer.codemap" overseer/handoff.py
grep -rn "TODO\|FIXME\|XXX" overseer/handoff.py overseer/factory.py
git diff --stat
git status --short          # after the commit: empty
```

## Allowed work and stopping condition

Allowed: a new `overseer/handoff.py`; `overseer/factory.py` (the
`recall_info` identity, the manifest's `repository` block and its new
`handoff` block, the `run_one` lines that build, write, digest, and record
the handoff, and the shared `commands` projection);
`tests/test_factory.py` (the new class only); `docs/HARNESS_FRAMEWORK.md`
(the CONTEXT row, the does-not-claim bullet, and re-derived citations
elsewhere); `README.md`; `WORK_LOG.md`.

Commit with a message in the repository's voice, for example "Persist the
blueprint's handoff record for every attempt", ending with the attribution
lines the session supplies, and include this prompt file in the commit.

Stop after this one increment and its commit: the record is persisted per
attempt from that attempt's own evidence, every unobservable field is marked
unmeasured with a reason, the base revision is the attempt-start commit, the
identifier lists distinguish completed from failing from never run, the next
eligible action is one of the three closed values and says who decides, a
later run never rewrites an earlier record, M1-M14 each fail the suite, the
docs are current with re-derived citations, both commands pass, and the tree
is clean. Report the commit hash, the diff summary, the command outputs, the
new test and reference counts, the mutation results, and the limits that
remain.

This stopping condition ends this prompt, not the objective: report
`step_done` with the CONTEXT row's new "Next increment" (the successor-side
reconciliation of the persisted record) in `remaining`. If the same failure
recurs twice with no new evidence, stop and report it instead of retrying.

End the report with the status block `AGENTS.md` names:

```yaml
STATUS: [SUCCESS | STUCK_NEEDS_ESCALATION]
TESTS_PASSED: [TRUE | FALSE]
FILES_MODIFIED: [<list of files>]
NEXT_AGENT_INSTRUCTION: "<clear self-contained prompt for next iteration>"
```
