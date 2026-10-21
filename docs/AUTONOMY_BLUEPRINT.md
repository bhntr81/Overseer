# Autonomy blueprint: target scope and unattended multi-loop orchestration

This document is a design blueprint, not an executable prompt. The Overseer
project's dedicated prompt-writing agent wrote it against commit `f28bb7d`
("Reconcile the handoff record's identifier lists against the recorded exit
codes"). Every `path:line` below was measured at that commit, and
`python3 scripts/check-doc-references docs/AUTONOMY_BLUEPRINT.md` checks that each
one resolves. Each increment named here is still a proposal. Every increment
gets its own bounded prompt, red-green phases, and commit, and gets filed
against exactly one row of `docs/HARNESS_FRAMEWORK.md`.

**Scope.** Only the Overseer engine is in scope. Both subsystems are generic
capabilities. Every test runs in a throwaway temporary directory, with a fake
worker script in place of a real model. No external product is planned or
scaffolded here.

**The user's objective for these two subsystems (verbatim excerpt):**

> ### 2. Generalizing Target Scope (`target_dir` / `SPEC.md`) — Introduce a target
> workspace configuration (e.g., via command-line argument or `SPEC.md` pointer) allowing
> the orchestrator to point away from the Overseer repo and target an arbitrary external
> directory. Ensure the harness can scaffold, build, and test a brand-new repository from
> scratch using the factory rules.
> ### 3. Unattended Multi-Loop Orchestration (`overseer/factory.py` / orchestrator runner) —
> Implement a continuous automation loop that feeds `NEXT_AGENT_INSTRUCTION` automatically
> into the worker model. Enforce the 3-retry safety break (freezing or escalating when a
> task fails 3 consecutive self-correction attempts). Automatically route to Claude only
> when execution halts or requires architectural intervention.
> Adhere strictly to AGENTS.md hardening mandates (Red-Green test separation, modules under
> 300 lines, python3 scripts/check, scripts/check-doc-references).

**Baseline at `f28bb7d`, measured by the writer:**
- `python3 scripts/check </dev/null`: `Ran 381 tests`, `OK`.
- `python3 scripts/check-doc-references`: `208 references checked in HARNESS_FRAMEWORK.md`.
- `git status --short`: only the operator's ` M AGENTS.md` and `?? HARDENING_BLUEPRINT.md`.

## 1. What already exists, and what is missing

### 1.1 Subsystem 2: target scope

What exists. Do not propose any of it again.

- **A factory job already targets an arbitrary directory.**
  - A command-mode spec's `workspace` must be an existing absolute directory
    (`overseer/factory.py:387`). Nothing ties it to this repository.
  - The closed set of spec fields is enforced at `overseer/factory.py:385`.
  - Every command runs with `cwd=workspace` (`overseer/factory.py:1581`). Its
    stdout and stderr are merged into a per-command log
    (`overseer/factory.py:1589`).
- **A job already builds and tests a brand-new directory.** The writer probed
  this at `f28bb7d` in a scratch directory. The job's implementation command wrote
  `m.py`, and its check ran `import m`.
  - In an **empty non-git directory** the job reached `passed`.
    - The base revision was unmeasured: "not a git repository".
    - `reconcile_handoff` returned `unverifiable` (`workspace`: "the workspace is
      not a git work tree").
  - In a **`git init` repository with no commit** the job also reached `passed`.
    - The base revision was unmeasured: "ambiguous argument 'HEAD'".
    - `reconcile_handoff` returned **`agree`**. The base-revision comparison is
      `not_applicable` when the record carries no base
      (`overseer/reconcile.py:158`). So an unborn repository reconciles as
      agreeing without any anchored revision.
- **The monitor already scopes panes by directory.** The `target_paths` and
  `targets` settings are validated at `overseer/__main__.py:52`. A relative path
  resolves against the directory holding `config.json` (`overseer/__main__.py:56`).
  Panes are filtered by `Tmux.targeted` (`overseer/tmux.py:116`) using `under`
  (`overseer/tmux.py:18`).
- **The workspace is only read during capture and reconciliation.** The read-only
  git runner sets `GIT_OPTIONAL_LOCKS=0` (`overseer/workdiff.py:52`,
  `overseer/workdiff.py:60`). The snapshot is at `overseer/workdiff.py:157`.

What is missing:

- **M2-a. ~~No scaffold step.~~ LANDED by increment 7.** `overseer/target.py:66`
  creates a target directory, runs `git init`, optionally copies `SPEC.md`, and
  makes one initial commit with a scoped local identity, so the first attempt has
  a measurable base revision. Proven end to end: the factory scaffolds, builds,
  and tests a brand-new repo and the handoff record reconciles as `agree`.
- **M2-b. No `SPEC.md` pointer.** The factory never reads a target's `SPEC.md`.
  The context manifest (`overseer/factory.py:1104`) does not record it. The
  attempt's environment carries recall, codebase, and skill variables
  (`overseer/factory.py:1061`, `overseer/factory.py:1099`) but no spec path. The
  hardening mandate "re-read SPEC.md" therefore has nothing to point at in a target.
- **M2-c. No orchestrator-level target argument.** The factory CLI
  (`overseer/factory.py:2447`) takes a task file, which carries `workspace`.
  Nothing else in the factory takes a target directory, because no orchestrator
  runner exists yet (M3-e).

### 1.2 Subsystem 3: unattended multi-loop orchestration

What exists. Do not propose any of it again.

- **The monitor already runs an unattended feed loop into worker panes.** Its
  pieces:
  - `run` polls (`overseer/__main__.py:260`) and `tick` acts
    (`overseer/__main__.py:211`). With `serial_queue`, `tick_queue` takes over
    (`overseer/scheduler.py:174`).
  - It parses the latest `OVERSEER_REPORT` JSON line (`overseer/policy.py:62`,
    `overseer/policy.py:82`).
  - It sends the report's `remaining` field as the next prompt
    (`overseer/policy.py:189`, `overseer/policy.py:255`).
  - On a `step_done` report it sends a writer-handoff prompt
    (`overseer/policy.py:217`, `overseer/policy.py:158`).
  - It reserves before it sends, so a send is never retried
    (`overseer/__main__.py:248`).
- **The limits a loop must keep already exist:**
  - Stop markers. `OVERSEER_NEEDS_INPUT` anywhere in the current turn always stops
    (`overseer/policy.py:30`, `overseer/policy.py:172`).
  - Permission, approval, and generation screens are never answered
    (`overseer/policy.py:19`, `overseer/policy.py:296`).
  - The idle threshold, "already replied", cooldown, and daily limit apply
    (`overseer/policy.py:319`, `overseer/policy.py:336`, `overseer/policy.py:340`,
    `overseer/policy.py:344`).
  - `dry_run` mode exists (`overseer/__main__.py:240`).
  - Capacity retries are bounded by `capacity_max_retries`
    (`overseer/scheduler.py:283`).
  - Provider-failure routing exists: failure detection
    (`overseer/modelchoice.py:85`), fallback chain (`overseer/modelchoice.py:157`,
    `overseer/modelchoice.py:169`), and session routing (`overseer/route.py:74`,
    `overseer/route.py:53`).
- **The factory already has the safety primitives a loop would use:**
  - Approval gating: a task whose envelope requires a decision waits in
    `awaiting_approval` until `decide` records a grant (`overseer/factory.py:819`).
    `run_one` re-checks the grant inside its dispatch transaction
    (`overseer/factory.py:2230`).
  - An interrupted run becomes `needs_reconciliation`, and `resolve`
    (`overseer/factory.py:771`) closes it as "no automatic retry".
  - The contract declares `budget.repair_allowance`, an integer from 0 to 10
    (`overseer/factory.py:208`). Nothing consumes it: the handoff record's next
    action is `bounded_repair` with `remaining_budget` unmeasured
    (`overseer/handoff.py:139`, `overseer/handoff.py:156`).
  - The worker lock exists (`overseer/factory.py:724`). The `controller` row
    holds the epoch (`overseer/factory.py:427`). Restore re-creates the side
    tables (`overseer/factory.py:2028`).
- **The blueprint's repair policy** (`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:352`)
  is one implementation attempt plus at most two repair attempts, and it says to
  stop earlier when the failure repeats unchanged. That is the user's "3
  consecutive self-correction attempts". The same directive appears in
  `AGENTS.md:31`.

What is missing:

- **M3-a. ~~No consecutive-failure counter and no freeze.~~ LANDED by increment
  1.** A repair lineage now relates each repair job to the job it repairs
  (`overseer/strikes.py:108`), counts the consecutive non-`passed` terminal
  states, and freezes the lineage at its bound (`overseer/strikes.py:132`,
  `overseer/factory.py:2419`). A frozen lineage refuses a further repair until an
  operator releases it (`overseer/factory.py:813`). The counter and freeze this
  bullet named no longer the gap; the remaining M3 items (b–f) are still open.
- **M3-b. ~~The `NEXT_AGENT_INSTRUCTION` status block is never parsed.~~ PARSER
  LANDED by increment 2; wiring still open.** The block that AGENTS.md requires
  (the `STATUS:` / `TESTS_PASSED:` / `FILES_MODIFIED:` / `NEXT_AGENT_INSTRUCTION:`
  lines) now has a bounded, never-evaluated parser (`overseer/statusblock.py:96`).
  It is not yet read by any caller: the monitor still reads only
  `OVERSEER_REPORT`, and the factory still reads only exit codes. Increment 3
  wires the parser into the factory and increment 6 into the monitor.
- **M3-c. ~~`STUCK_NEEDS_ESCALATION` is detected nowhere.~~ FACTORY SIDE LANDED
  by increment 3.** The factory now reads the implementation log, and a
  `STUCK_NEEDS_ESCALATION` block freezes the job's lineage
  (`overseer/factory.py:2424`, `overseer/strikes.py:171`). The monitor still
  does not react to it; increment 6 adds the pane-side hold.
- **M3-d. ~~No operator pause of dispatch.~~ LANDED by increment 5.** `pause`/
  `unpause --note` on the factory CLI record a dispatch pause checked inside the
  dispatch transaction (`overseer/factory.py:2208`); a paused factory starts no
  new job while running work is untouched. It pauses dispatch, not running work.
- **M3-e. No factory-side feed loop.** No runner turns one job's worker
  instruction into the next job.
- **M3-f. No escalation route.** Routing moves a pane only on a *provider* failure
  (`overseer/scheduler.py:148`), never because work halted.

### 1.3 Locality facts that constrain placement

These files are already over the 300-line flag of `HARDENING_BLUEPRINT.md`:

| File | Lines |
|---|---|
| `overseer/policy.py` | 350 |
| `overseer/scheduler.py` | 372 |
| `overseer/__main__.py` | 391 |
| `overseer/modelchoice.py` | 304 |
| `overseer/factory.py` | 2395 |
| `overseer/codemap.py` | 1292 |
| `overseer/workdiff.py` | 494 |

The rule for every increment below:

- New logic goes in a **new module under 300 lines**.
- An existing over-limit file gets only a small call-site edit, at most 15 lines
  per increment, and the work log flags it.
- `overseer/factory.py` may grow by at most 40 lines per increment.
  - 15% of 2395 is 359 lines.
  - This blueprint's total factory budget is about 200 lines, about 8%.

## 2. Ordering principle

**Safety comes before autonomy.** No increment that sends or submits work
unattended (increments 9 and 10) may start before all of these exist and are
tested:

- the 3-strike freeze and its ledger state (1)
- status-block parsing (2)
- worker-report capture and escalation (3)
- the no-new-evidence early freeze (4)
- the dispatch pause (5)
- the monitor-side escalation hold (6)

Subsystem 2 (increments 7 and 8) carries no autonomy risk. It is placed after
the safety work, before the feed loop that needs a target argument.

**The ordered list.** Each item is one commit.

1. **STATE.** A repair lineage and the 3-strike freeze in the factory ledger.
2. **CONTEXT.** A bounded parser for the AGENTS.md status block.
3. **EVIDENCE.** The worker's status block captured as run evidence;
   `STUCK_NEEDS_ESCALATION` freezes the lineage.
4. **EVIDENCE.** The no-new-evidence early freeze: an unchanged repeated failure.
5. **PERMISSIONS.** An operator pause of factory dispatch.
6. **PERMISSIONS.** A monitor-side escalation hold and pane 3-strike freeze.
7. **TOOLS.** Target scaffold: create, `git init`, and make the first commit of a
   brand-new target.
8. **CONTEXT.** The target's `SPEC.md` pointer, recorded in the manifest and
   handed to the attempt.
9. **STATE.** The unattended factory feed loop (`--target`, feeding
   `NEXT_AGENT_INSTRUCTION`).
10. **PERMISSIONS.** Escalation route to a Claude session when a loop halts.

Every increment's prompt carries the house rules:

- Phase 0: re-read the ground truth.
- Phase 1: red. Only `tests/` is written. Record the `sha256sum`.
- Phase 2: green. `tests/` is read-only, and the digest must still match.
- Phase 3: mutations.
- Phase 4: docs. Update the pillar row, the does-not-claim bullet, `README.md`,
  and `WORK_LOG.md`, and re-derive every moved citation by content.
- Phase 5: run `python3 scripts/check </dev/null` and
  `python3 scripts/check-doc-references`, stage files explicitly, and make one
  commit.

## 3. Increments

### Increment 1: repair lineage and the 3-strike freeze (STATE, `docs/HARNESS_FRAMEWORK.md:33`) — LANDED

> **Landed.** Implemented in `overseer/strikes.py` (pure ledger logic, 192 lines,
> under 300) with a +36-line call-site edit to `overseer/factory.py`. All nine
> named tests pass in `tests/test_factory.RepairLineageTests`, the full suite is
> 390 tests, and the three mutation checks below were confirmed to fail the
> suite. The one deviation from the plan below: `overseer/strikes.py` is 192
> lines, not the estimated ≤160; it stays well under the 300-line rule, and the
> `factory.py` delta stayed inside the +40 budget.

**Objective.** Relate each repair job to the job it repairs. Count consecutive
failed attempts of one lineage in the ledger. When the bound is reached, freeze
the lineage with a recorded reason. A frozen lineage refuses further repair
submissions until an operator releases it with a named, recorded note.

**Files and budgets:**
- New `overseer/strikes.py`, ≤ 160 lines. It holds pure functions: the bound,
  the strike count, and the freeze decision. It does not import `overseer.factory`
  or `subprocess`.
- `overseer/factory.py`, ≤ +40 lines:
  - two tables in the schema and in `_ensure_side_tables`
  - a `repair_of` keyword on `submit`
  - the strike recorded inside `run_one`'s final transaction
    (`overseer/factory.py:2426`) and inside `resolve`
  - a `release` method and CLI subcommand
- Tests: a new class in `tests/test_factory.py`.

**Decisions to settle in the prompt** (recommended answers given):

1. **Where the lineage lives.** Recommended: two new tables.
   - `repairs(job_id PRIMARY KEY, parent_id, lineage_id)`
   - `lineages(lineage_id PRIMARY KEY, root_job, state, strikes, bound,
     bound_source, detail, updated)`, with `state` ∈ {`open`, `frozen`,
     `released`, `closed`}

   Do not add a spec field. The spec field set is closed
   (`overseer/factory.py:385`), and the spec hash must stay what it is.
2. **What a strike is.** Recommended:
   - A lineage job that reaches a terminal state other than `passed` is a strike:
     `failed` from `run_one`, or `failed` through `resolve`.
   - `passed` closes the lineage.
   - `cancelled` is an operator act. It is neither a strike nor a reset.
   - Strikes count only *consecutive* failures in the parent chain.
3. **The bound.** Recommended: `bound = min(3, 1 + repair_allowance)`, with
   `bound_source` naming which bound applied: blueprint (3) or contract
   allowance. A contract with `repair_allowance: 0`, like the example task,
   freezes after its first failure. State this honestly rather than override the
   contract.
4. **What freezing does.** Recommended:
   - `submit(spec, repair_of=X)` on a frozen lineage raises `ValueError`, naming
     the lineage, its strikes, and its bound.
   - A `frozen` event goes on the job that tripped the bound.
   - The freeze never changes any job's state.
5. **Release.** Recommended: `release(lineage_id, decider, note)`.
   - The decider and note are required.
   - The decider is recorded, not authorized, exactly as `decide` documents
     (`overseer/factory.py:819`).
   - Release grants a fresh `bound` of attempts, with a `released` event.
6. **Backup and restore.** Both new tables must survive `backup` and `restore`,
   and they must be created by `_ensure_side_tables`.

**Observable acceptance:**
- Three consecutive failed attempts with `repair_allowance: 2` leave the lineage
  `frozen` with `strikes == 3`, `bound == 3`, and `bound_source == 'blueprint'`.
- The fourth `submit(..., repair_of=...)` raises.
- A passed attempt closes the lineage.
- A `release` with a note lets exactly `bound` more attempts be submitted.
- No job's `state` or `detail` is changed by the freeze.

**Named tests:**
- `test_three_consecutive_failures_freeze_the_lineage`
- `test_a_frozen_lineage_refuses_a_further_repair`
- `test_the_contract_repair_allowance_lowers_the_bound`
- `test_a_passed_attempt_closes_the_lineage`
- `test_a_cancelled_job_is_neither_a_strike_nor_a_reset`
- `test_release_requires_a_named_decider_and_a_note`
- `test_a_resolved_interrupted_attempt_counts_as_a_strike`
- `test_the_freeze_never_changes_a_job_state`
- `test_the_lineage_survives_backup_and_restore`

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| bound fixed at 4 | the freeze test |
| `repair_allowance` ignored | the allowance test |
| `passed` not closing the lineage | the closes test |
| cancelled counted as a strike | the cancelled test |
| strike written outside the final transaction, or skipped in `resolve` | the resolve test |
| release without a note | the release test |
| tables missing from `_ensure_side_tables` | the backup and restore test |

### Increment 2: the status-block parser (CONTEXT, `docs/HARNESS_FRAMEWORK.md:32`) — LANDED

> **Landed.** Implemented in `overseer/statusblock.py` (123 lines, under the 180
> budget, standard library plus the monitor's own `ANSI` and `_controls` rules
> reused from `overseer/policy.py`). All eight named tests pass in
> `tests/test_statusblock.py`, the full suite is 398 tests, and the four
> mutation checks below were confirmed to fail the suite. No other file changed;
> the parser has no caller yet (increments 3 and 6 wire it).

**Objective.** Parse the AGENTS.md status block out of bounded terminal or log
text. The result is data: never evaluated, closed values, bounded fields.

**Files and budgets:**
- New `overseer/statusblock.py`, ≤ 180 lines, standard library only.
- New `tests/test_statusblock.py`.
- No other file changes.

**Decisions to settle:**
1. **Grammar.**
   - The last block in the text wins.
   - Keys are exactly `STATUS`, `TESTS_PASSED`, `FILES_MODIFIED`, and
     `NEXT_AGENT_INSTRUCTION`, in that order, one per line.
   - `STATUS` ∈ {`SUCCESS`, `STUCK_NEEDS_ESCALATION`}.
   - `TESTS_PASSED` ∈ {`TRUE`, `FALSE`}.
   - `FILES_MODIFIED` is a bracketed list.
   - `NEXT_AGENT_INSTRUCTION` is one JSON-style double-quoted string, decoded with
     `json.loads`, never YAML.
   - ANSI sequences are stripped first.
2. **Unfilled template.** The literal template line `[SUCCESS |
   STUCK_NEEDS_ESCALATION]` is `invalid` with the reason "template not filled",
   never a status.
3. **Bounds.**
   - The input tail is at most 64 KiB.
   - The instruction is at most 4000 characters, with no control characters.
     Reuse the rule the monitor applies to a sent line (`overseer/policy.py:78`).
   - `FILES_MODIFIED` holds at most 200 entries.
   - An over-bound value is `invalid` with its reason, never truncated into
     validity.
4. **Result shape.** `{found, valid, reason, status, tests_passed,
   files_modified, next_instruction}`.

**Acceptance and tests:**
- `test_a_filled_block_is_parsed_into_closed_values`
- `test_the_last_block_wins`
- `test_the_unfilled_template_is_invalid`
- `test_an_unknown_status_is_invalid`
- `test_an_instruction_with_a_control_character_is_invalid`
- `test_an_over_long_instruction_is_invalid_not_truncated`
- `test_no_block_is_not_found`
- `test_the_parser_never_evaluates_text`: a block carrying `__import__` stays a
  plain string.

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| first block wins | the last-block test |
| template accepted | the template test |
| truncation instead of rejection | the over-long test |
| status values not closed | the unknown-status test |

### Increment 3: worker report as evidence; `STUCK_NEEDS_ESCALATION` escalates (EVIDENCE, `docs/HARNESS_FRAMEWORK.md:36`) — LANDED

> **Landed.** Implemented in `overseer/workerreport.py` (62 lines, under the 150
> budget) with a +25-line call-site edit to `overseer/factory.py` (inside the
> +30 budget) and a small `freeze_for_escalation` added to `overseer/strikes.py`
> (now 212 lines, under 300). All five named tests pass in
> `tests/test_factory.WorkerReportTests`, the full suite is 403 tests, and the
> four mutation checks below were confirmed to fail the suite. The worker report
> is evidence only: exit codes decide the state, and the factory side of
> escalation is wired while the monitor side waits for increment 6.

**Objective.** After the implementation command, the factory reads a bounded tail
of that command's log and parses it with increment 2's parser. It writes
`worker_report.json` into the run evidence and seals its digest with a
`worker_report` event. Escalation:
- When the block says `STUCK_NEEDS_ESCALATION`, the job's lineage is frozen at
  once with the reason "the worker requested escalation".
- A job without a lineage gets an `escalation_requested` event.

**Files and budgets:**
- New `overseer/workerreport.py`, ≤ 150 lines.
- `overseer/factory.py`, ≤ +30 lines: one call after the implementation result,
  one write, and one event.

**Decisions to settle:**
1. **Which log.** The implementation command's log only (`00.log`, written at
   `overseer/factory.py:2331`). Read its last 64 KiB, checking the size before
   opening.
2. **A claim is never a verdict.** Pass or fail stays decided by exit codes
   (`overseer/factory.py:2338`).
   - A `TESTS_PASSED: TRUE` claim on a run whose acceptance failed is recorded as
     `claim_disagrees: true`, naming both sides.
   - It changes nothing.
3. **The report is not part of the handoff record.** The record's ten fields
   stay as they are. The context manifest gains only a pointer and a digest.
4. **Missing or invalid block.** The report records `found: false` or
   `valid: false` with the reason, and that is not a strike by itself.

**Tests:**
- `test_a_worker_block_is_recorded_with_its_log_digest`
- `test_stuck_needs_escalation_freezes_the_lineage`
- `test_a_success_claim_on_a_failed_run_is_recorded_as_disagreeing_and_changes_nothing`
- `test_a_missing_block_is_recorded_not_invented`
- `test_an_oversized_log_is_read_only_at_its_tail`

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| the claim decides the state | the claim test |
| escalation ignored | the freeze test |
| whole log read | the tail test |
| digest event omitted | the recorded test |

### Increment 4: the no-new-evidence early freeze (EVIDENCE, `docs/HARNESS_FRAMEWORK.md:36`) — LANDED

> **Landed.** Implemented in `overseer/strikes.py` (a `fingerprint` function, a
> `strike_evidence` table, and an early-freeze branch in `record_terminal`; the
> module is now 257 lines, under 300, and the added logic is inside the +60
> budget) with a +12-line call-site edit to `overseer/factory.py` (inside the
> +15 budget). Three named tests pass in `tests/test_factory.NoNewEvidenceTests`
> and the two mutation checks were confirmed to fail the suite. Increment 1's
> `test_three_consecutive_failures_freeze_the_lineage` was updated to give each
> attempt a distinct exit code, so it still tests the bound rather than tripping
> the new early freeze; the full suite is 406 tests.

**Objective.** The blueprint says to stop earlier "when the failure repeats
unchanged" (`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:352`). This increment freezes
a lineage before its bound when two consecutive failed attempts carry the same
observable failure evidence.

**Files and budgets:**
- `overseer/strikes.py`, ≤ +60 lines, staying under 300.
- `overseer/factory.py`, ≤ +15 lines.

**Decisions to settle:**
1. **The evidence fingerprint.** All of these observations, from records the
   ledger already seals:
   - the failing and not-run acceptance identifiers
   - the failing command's exit code and timeout flag (from the sealed manifest,
     `overseer/readback.py:102`)
   - the patch digest of the workspace diff receipt, or "no patch"
2. **What "unchanged" means.** Byte-equal fingerprints. Nothing is compared
   semantically.
3. **The record.** The freeze reason names both run ids and the fields that
   matched.

**Tests:**
- `test_an_unchanged_repeated_failure_freezes_before_the_bound`
- `test_a_changed_patch_is_new_evidence_and_does_not_freeze_early`
- `test_a_different_failing_identifier_is_new_evidence`

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| patch digest dropped from the fingerprint | the changed-patch test |
| identifiers dropped from the fingerprint | the different-identifier test |

### Increment 5: operator pause of factory dispatch (PERMISSIONS, `docs/HARNESS_FRAMEWORK.md:35`) — LANDED

> **Landed.** A one-row `dispatch_pause` table and `pause`/`unpause`/`_set_pause`
> on `Factory`, with `pause`/`unpause --note` CLI subcommands. The pause is read
> inside `run_one`'s `BEGIN IMMEDIATE` transaction, so a paused factory starts no
> new job; running work is untouched and the pause survives backup and restore.
> `overseer/factory.py` grew by +36 lines (just over the +35 estimate, under the
> +40 cap). Four named tests pass in `tests/test_factory.PauseTests` — the
> dispatch test asserts the pause is read after `BEGIN IMMEDIATE`, catching a
> check placed outside the transaction — and the two mutations were confirmed to
> fail the suite. Full suite 410.

**Objective.** Add `pause --note` and `unpause --note` to the factory CLI. While
the factory is paused, `run_one` dispatches nothing, and the pause, its note, and
its time are recorded. Running work is not interrupted. The docs must say so,
because the PERMISSIONS row asks for a pause of *running* work and this pauses
*dispatch* only.

**Files and budgets:**
- `overseer/factory.py`, ≤ +35 lines: a `paused` column or a one-row table
  beside `controller` (`overseer/factory.py:427`), a check at the top of
  `run_one`'s dispatch transaction, two methods, and two subcommands.

**Decisions to settle:**
1. The pause is checked inside the same `BEGIN IMMEDIATE` transaction as dispatch
   (`overseer/factory.py:2203`).
2. A paused `run_one` returns a JSON reason, and the CLI exits 1.
3. The pause survives backup and restore.

**Tests:**
- `test_a_paused_factory_dispatches_nothing`
- `test_unpause_requires_a_note_and_resumes_dispatch`
- `test_the_pause_does_not_touch_a_running_job`
- `test_the_pause_survives_backup_and_restore`

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| check outside the transaction | the dispatch test, using a race helper that pauses between two reads |
| note not required | the unpause test |

### Increment 6: monitor escalation hold and pane 3-strike freeze (PERMISSIONS, `docs/HARNESS_FRAMEWORK.md:35`)

**Objective.** The monitor holds a pane, never sending to it, in two cases:

- the current turn carries a valid status block with `STATUS:
  STUCK_NEEDS_ESCALATION`
- three consecutive step reports of that pane show `TESTS_PASSED: FALSE` or an
  unchanged `remaining` fingerprint

The hold is persisted in the monitor's state file. An explicit operator
`unfreeze <pane>` command clears it.

**Files and budgets:**
- New `overseer/escalation.py`, ≤ 160 lines.
- `overseer/policy.py`, ≤ +10 lines: one call in `classify`
  (`overseer/policy.py:296`). The file is already at 350 lines, so flag it.
- `overseer/__main__.py`, ≤ +15 lines: the subcommand. The file is already at
  391 lines, so flag it.
- Tests in `tests/test_policy.py` and `tests/test_monitor.py`.

**Decisions to settle:**
1. **Precedence.** The hold is evaluated after `stop_requested` and before any
   send path, including the capacity retry path (`overseer/policy.py:319`). The
   capacity retry must never send to a frozen pane.
2. **Persistence.** The freeze lives in the monitor's state file, not in the
   factory ledger. The docs say plainly that the two stores are separate.
3. **Clearing.** Only the explicit command clears the freeze. A new turn, a
   restart, or a changed screen does not clear it. A replaced pane process
   (a new `pane:pid` key) is a new entry, and the docs name that limit.

**Tests:**
- `test_stuck_needs_escalation_holds_the_pane`
- `test_three_failed_step_reports_freeze_the_pane`
- `test_a_frozen_pane_is_not_sent_a_capacity_retry`
- `test_unfreeze_clears_only_the_named_pane`
- `test_the_daily_limit_and_needs_input_still_stop_first`

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| hold skipped for capacity | the capacity test |
| counter reset on any new screen | the three-reports test |
| hold placed before `stop_requested` | the needs-input test, through the stop reason |

### Increment 7: target scaffold (TOOLS, `docs/HARNESS_FRAMEWORK.md:34`) — LANDED

> **Landed.** `overseer/target.py` (117 lines, under 200) adds
> `python3 -m overseer.target init <dir> [--spec FILE]`: it creates or accepts an
> empty directory, runs `git init`, copies an optional `SPEC.md`, and makes one
> initial commit with a fixed identity passed through environment variables, via
> its own writing git runner that never loosens the read-only runner. It refuses
> a non-empty directory, a path inside a work tree (this repo included), a
> relative path, and a symlink. Five tests pass, including an end-to-end test
> where the factory scaffolds, builds, and tests a brand-new repo and the handoff
> record reconciles `agree` with an empty unverifiable list; three mutations were
> confirmed caught. The factory is unchanged.

**Objective.** Add `python3 -m overseer.target init <dir> [--spec FILE]`. It:
- creates an absent directory, or accepts an empty existing one
- runs `git init`
- copies the optional `SPEC.md`
- makes one initial commit with a fixed, local committer identity

After that, the first attempt has a measurable base revision. Then prove that
the factory scaffolds, builds, and tests a brand-new repository from scratch.

**Files and budgets:**
- New `overseer/target.py`, ≤ 200 lines. It has its own git runner, which
  *writes*. It never reuses or loosens the read-only runner in
  `overseer/workdiff.py:52`.
- No factory change.
- New `tests/test_target.py`.

**Decisions to settle:**
1. **Refusals.** Refuse a non-empty directory, a path inside an existing git work
   tree (this includes this repository), a relative path, and a symlinked path.
2. **The commit.** Use `git commit --allow-empty` when there is no `--spec`. The
   identity comes from environment variables scoped to that one call, and the
   user's git config is never written.
3. **Output.** Print one JSON object: the path, the head commit, and whether a
   spec was copied. Exit 0. Any refusal exits 1 with a JSON error.

**Tests:**
- `test_init_creates_a_repository_with_one_commit`
- `test_init_refuses_a_non_empty_directory`
- `test_init_refuses_a_path_inside_a_work_tree`
- `test_init_copies_the_spec`
- `test_a_scaffolded_target_runs_builds_and_tests_from_scratch`: submit a job
  whose implementation writes a package and its test, and whose check runs
  `python -m unittest`. Assert `passed`, a measured `base_revision`, and a
  reconciliation verdict of `agree` with an empty `unverifiable` list.

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| no initial commit | the end-to-end test: base unmeasured |
| non-empty directory accepted | the refusal test |
| work-tree check removed | the inside-work-tree test |

### Increment 8: the target's `SPEC.md` pointer (CONTEXT, `docs/HARNESS_FRAMEWORK.md:32`)

**Objective.** At attempt start, the factory reads `<workspace>/SPEC.md`,
bounded. It records the file's path and digest, or its absence and the reason,
in the context manifest. It hands the attempt `OVERSEER_SPEC_PATH` and
`OVERSEER_SPEC_SHA256`. No spec field is added.

**Files and budgets:**
- `overseer/factory.py`, ≤ +30 lines: one manifest block and two environment
  variables beside the skills variables (`overseer/factory.py:1099`).
- Bounded reading reuses `overseer/readback.py`.

**Decisions to settle:**
1. **Bound and secrecy.** The size bound is 64 KiB. The secret-name rule does not
   apply, since the name is fixed, but a symlink out of the workspace is refused.
2. **Absence.** A missing `SPEC.md` is recorded as absent, never as an error, and
   never blocks the attempt.
3. **Context only.** The factory supplies the spec and does not enforce it. The
   docs say that nothing checks the work against it.

**Tests:**
- `test_a_target_spec_is_recorded_with_its_digest`
- `test_a_missing_spec_is_recorded_as_absent_with_the_reason`
- `test_an_oversized_spec_is_not_read`
- `test_a_symlinked_spec_outside_the_workspace_is_refused`
- `test_the_spec_path_reaches_the_attempt_environment`

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| digest omitted | the digest test |
| symlink followed | the symlink test |
| size check removed | the oversized test |

### Increment 9: the unattended factory feed loop (STATE, `docs/HARNESS_FRAMEWORK.md:33`)

> **Building block ready (out of order).** The worker-invocation adapter this
> loop needs is already built: `overseer/provider.py:45` constructs the OpenCode
> argv with the instruction as one whole, un-shell-interpolated element,
> `overseer/provider.py:25` registers the free gateway models,
> `overseer/provider.py:131` detects and (optionally) inherits the active
> session's runner with the free OpenCode gateway as the execution-safe default,
> and `overseer/provider.py:163` builds a submittable task from an instruction. A
> real free model has written files the factory's checks verified via that
> builder (see the work log). This loop still only needs to call `build_task` per
> iteration and feed the next instruction from the worker report. It remains
> unwritten, and the safety brake of increment 6 lands before it, since this is
> the first increment that sends work unattended.

**Objective.** Add `python3 -m overseer.orchestrate --db DB --loop LOOP.json
--target DIR [--once] [--dry-run]`. Each iteration:

1. Builds a command-mode job from the loop spec. The target is the `workspace`.
   Exactly one argv element of the worker command equals the placeholder
   `{instruction}` and is replaced *whole*. The instruction is never formatted
   into a string or passed through a shell.
2. Submits the job. After a failure it submits with `repair_of` set to the
   previous job.
3. Runs it.
4. Reads the worker report (increment 3).
5. Feeds the report's `NEXT_AGENT_INSTRUCTION` into the next iteration.

**Files and budgets:**
- New `overseer/orchestrate.py`, ≤ 280 lines.
- No factory change beyond a public read of lineage state, if increment 1 did
  not already provide one (≤ +10 lines).

**Decisions to settle:**
1. **The first instruction** is the loop spec's `objective`. A later instruction
   comes only from a *valid* status block. A missing or invalid block stops the
   loop with `needs_input`. No instruction is ever invented.
2. **Stop conditions.** The loop checks these before each submission, in order:
   - dispatch paused (increment 5)
   - lineage frozen (increments 1, 3, 4)
   - the last job is `awaiting_approval`: the loop never calls `decide`
   - the worker output carries `OVERSEER_NEEDS_INPUT`
   - the daily iteration cap is reached
   - done

   **Done** means the last job `passed`, its block says `SUCCESS`, and it carries
   `OVERSEER_DONE` with no further instruction.
3. **The daily cap.** It is counted from ledger events in the last 86400 seconds,
   so it holds across restarts. Default 12, matching `max_per_day` in
   `config.json`.
4. **Approvals.** The loop spec's envelope is copied as is. A loop never weakens
   `requires_decision` and never records a grant.
5. **Exit codes.** 0 when done. 2 for needs_input, frozen, paused, or the cap. 1
   for an error. The last line is `OVERSEER_DONE` or `OVERSEER_NEEDS_INPUT`, so a
   monitor pane running the loop stops on it (`overseer/policy.py:172`).
6. **One loop per ledger.** An `flock` sits beside the database. The factory's
   worker lock still serializes `run_one`.

**Tests** use a fake worker: a Python script in the temp directory whose output
is driven by a counter file.
- `test_the_loop_feeds_the_next_instruction_as_one_argv_element`
- `test_the_loop_stops_at_the_freeze_after_three_failures`
- `test_the_loop_stops_when_dispatch_is_paused`
- `test_the_loop_never_decides_an_approval`
- `test_the_loop_stops_on_needs_input`
- `test_the_daily_cap_holds_across_a_restart`
- `test_an_invalid_block_stops_the_loop_without_inventing_an_instruction`
- `test_the_loop_finishes_on_done`
- `test_dry_run_submits_nothing`

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| freeze check removed | the freeze test |
| pause check removed | the pause test |
| `decide` called | the approval test |
| fallback instruction invented | the invalid-block test |
| cap kept in memory only | the restart test |
| instruction substituted into a substring | the argv test |

### Increment 10: escalation route to a Claude session (PERMISSIONS, `docs/HARNESS_FRAMEWORK.md:35`)

**Objective.** When a loop stops because a lineage froze, from increments 1, 3,
or 4, the loop may start one escalation session. The route is configured by the
loop spec's `escalate_to`, one of `none` (the default) or a client from
`overseer/tmux.py:15`. The session is started through the existing router
(`overseer/route.py:53`) in the target directory, with a bounded prompt built
from ledger facts only:
- the lineage
- the run ids
- the failing identifiers
- the freeze reason
- the paths of the evidence files

**Files and budgets:**
- `overseer/orchestrate.py`, ≤ +60 lines, staying under 300. Otherwise use a new
  `overseer/escalate.py`.
- No factory change.

**Decisions to settle:**
1. **When to route.** Only for a freeze. Never for `awaiting_approval`, a pause,
   or `OVERSEER_NEEDS_INPUT`. Those wait for a human, and no model may answer a
   human decision.
2. **At most once per freeze.** Each escalation is recorded as an
   `escalation_routed` event. A second stop on the same frozen lineage does not
   route again.
3. **Limits.** The route honours `--dry-run` and the daily cap. The started
   session is an ordinary pane, still under every monitor limit.

**Tests** monkeypatch the router, so no tmux session starts:
- `test_a_frozen_loop_routes_once_to_the_configured_client`
- `test_an_approval_wait_is_never_routed_to_a_model`
- `test_the_escalation_prompt_carries_only_ledger_facts`
- `test_dry_run_routes_nothing`

**Mutations that must fail:**

| Mutation | Must be caught by |
|---|---|
| routing for an approval wait | the approval test |
| no once-only record | the routes-once test |
| prompt includes raw log text | the ledger-facts test |

## 4. Honest limits

**"Route to Claude on architectural intervention" can be detected only from
observable signals:**

- a valid `STATUS: STUCK_NEEDS_ESCALATION` block, in a pane (increment 6) or in a
  job's implementation log (increment 3)
- a lineage reaching its bound of consecutive failed attempts (increment 1)
- an unchanged repeated failure: a byte-equal fingerprint of failing identifiers,
  exit codes, and patch digest (increment 4)
- the existing provider failures, detected by `overseer/modelchoice.py:85`.
  These route to another provider and are not an architectural escalation.

**What cannot be detected:**

- **Whether a problem is architectural.** A worker that silently loops on a
  design flaw, while changing its patch every time, produces "new evidence" by
  the fingerprint rule and runs to the bound.
- **Whether a claim is honest.** A `SUCCESS` or `TESTS_PASSED: TRUE` claim is
  recorded, never trusted. Exit codes decide.
- **Scope expansion and spec drift.** `SPEC.md` is supplied, not enforced.
- **Whether a routed Claude session started work, has credit, or succeeded.**
  Starting a session is not completion.
- **Whether a prompt-writing agent actually ran.** The monitor already says the
  writer handoff is instructed, not verified (`overseer/policy.py:217`).

**Other honest limits:**

- **The factory and the monitor keep separate stores.** The factory freeze lives
  in the SQLite ledger. The pane freeze lives in the monitor's JSON state file.
  Neither sees the other.
- **The pause stops dispatch, not running work.**
- **The exit codes are the factory's own record** (the current CONTEXT limit,
  `docs/HARNESS_FRAMEWORK.md:32`). Only the latest run's evidence is reachable
  through the ledger's single evidence pointer per job.
- **The default bound can mean one attempt.** With `repair_allowance: 0`, as in
  `factory/tasks/overseer-checks.json`, the bound is one attempt. That is the
  contract's choice, recorded as such.
- **Tests use a fake worker.** No real model is exercised by the suite, so the
  loop's behaviour with a real model is unmeasured.

## 5. Where the coordinator's measurements need correcting

- **An empty non-git directory** does make the base revision and the
  reconciliation unverifiable. That part is confirmed.
- **A `git init` repository with no commit is different.** The base is unmeasured,
  yet `reconcile_handoff` returns `agree`, because the base comparison is
  `not_applicable`. This is why increment 7 makes an initial commit.
- **The validation line has moved.** It is `overseer/factory.py:387` (validate
  starts at `overseer/factory.py:354`), not about 384.
- **The monitor already feeds report-derived prompts unattended.** What is
  missing is the AGENTS.md status block, not a feed loop as such.
- **Four monitor modules are already over 300 lines**: `policy.py`,
  `scheduler.py`, `__main__.py`, and `modelchoice.py`. The rule "modules under
  300 lines" can bind only new modules and edit sizes, not these files as they
  stand.

## 6. Objective text for increment #1 (for the next executable prompt)

> Add a repair lineage and the 3-strike freeze to the factory ledger (STATE row,
> `docs/HARNESS_FRAMEWORK.md:33`). A job submitted with `repair_of=<job id>` joins that
> job's lineage; each lineage job that ends in a terminal state other than `passed` —
> through `run_one` or through `resolve` — is a strike recorded in the same transaction as
> its final transition; `passed` closes the lineage and `cancelled` is neither a strike nor
> a reset. When the consecutive strikes reach `min(3, 1 + contract budget.repair_allowance)`
> (the blueprint's one attempt plus two repairs, `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:352`,
> lowered by the contract), the lineage becomes `frozen` with a recorded reason and bound
> source, and a further `submit(..., repair_of=...)` on it raises without changing any job's
> state; only `release <lineage> --decider NAME --note TEXT` reopens it, recorded and not
> authorized. The lineage tables survive backup and restore. Pure logic goes in a new
> `overseer/strikes.py` under 300 lines; `overseer/factory.py` grows by at most 40 lines;
> tests are written only in the red phase; finish with `python3 scripts/check </dev/null`
> and `python3 scripts/check-doc-references` passing.
