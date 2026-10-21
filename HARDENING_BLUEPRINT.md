# Hardening blueprint: failure-mode mandates, wired to the code

This blueprint names the five systemic failure modes of a recursive,
LLM-driven software factory and, for each, states a **detection signal** and a
**preventive mitigation**. Unlike a generic checklist, every claim here is
anchored to the code that exists and carries an honest status, so a reader can
tell a shipped control from an intention.

**Anchoring.** Written against commit `f28bb7d` ("Reconcile the handoff
record's identifier lists against the recorded exit codes"). Every `path:line`
below was measured at that commit and resolves with
`python3 scripts/check-doc-references HARDENING_BLUEPRINT.md`. When the code
moves, the citation is re-derived by content, not guessed.

**Status vocabulary.** Each signal and mitigation is marked:

- **IMPLEMENTED** — code does it now, with the citation.
- **DATA-ONLY** — the factory already records the evidence a check would read,
  but nothing acts on it yet; the gap is a threshold or a rejection, not a
  capture.
- **BY DISCIPLINE** — an `AGENTS.md` mandate enforced by the worker and the
  reviewer, not by code. Honest but unenforced.
- **FILED** — not built; owned by a named increment of
  [docs/AUTONOMY_BLUEPRINT.md](docs/AUTONOMY_BLUEPRINT.md), filed against one
  row of [docs/HARNESS_FRAMEWORK.md](docs/HARNESS_FRAMEWORK.md).
- **OUT OF SCOPE** — deliberately not pursued; the reason is stated.

## 0. How this document relates to the others

Three documents, one design:

- **[docs/HARNESS_FRAMEWORK.md](docs/HARNESS_FRAMEWORK.md)** is the *map*: six
  pillars (CONTRACT, CONTEXT, STATE, TOOLS, PERMISSIONS, EVIDENCE), each with the
  `file:line` that implements it and an honest verdict.
- **[docs/AUTONOMY_BLUEPRINT.md](docs/AUTONOMY_BLUEPRINT.md)** is the
  *executable plan*: ten ordered, bounded increments that add unattended
  operation, each filed against exactly one pillar row.
- **This document** is the *failure-mode layer*: it crosses the five classic
  factory failure modes against that map and that plan, so that no mitigation is
  claimed without either a citation (built) or a filing (owed).

Each mandate in `AGENTS.md` ("HARDENING COMPLIANCE MANDATES",
`AGENTS.md:57`) has its row here, and this document says plainly whether that
mandate is enforced by code or only by discipline.

## A note the whole document keeps

**A claim is never a verdict.** The factory's deciding authority is the exit
code of the acceptance command, read back from the sealed run evidence
(`overseer/readback.py:153`) and checked against the handoff record by the
reconciliation (`overseer/reconcile.py:184`). Every detection signal below is
*evidence the controller records*, not a judgement the model is trusted to
make about itself. A hardening control that depended on the worker telling the
truth would not be a control.

---

## Pillar 1 — the locality trap (global architectural rot)

A worker optimizes the file in front of it and lets the whole grow misshapen:
one module balloons, logic is duplicated, imports tangle.

### 1.1 Detection signals

- **Per-file line delta.** *DATA-ONLY.* Every command-mode attempt in a git
  workspace leaves `diff.json`, a patch receipt whose per-file body counts
  insertions and deletions (`overseer/workdiff.py:291`) from a before/after
  workspace snapshot (`overseer/workdiff.py:157`). The raw `loc_delta` per file
  therefore already exists in sealed evidence. What is missing is the threshold:
  nothing yet flags a file that grew more than 15% in one attempt or crossed
  300 lines. *FILED as a CONTEXT/EVIDENCE check; see 1.3.*
- **Duplication and complexity (AST / cyclomatic).** *OUT OF SCOPE for now.* No
  `radon`-style grade is computed. Pursuing it would add a non-standard-library
  dependency, which the project avoids; if added it must run inside the same
  read-only snapshot, never as a worker self-report.
- **Import-hierarchy drift (cycles, depth).** *OUT OF SCOPE for now.* Not
  measured. A static import-graph pass over the sealed `codebase.json`
  (`overseer/codemap.py:1058`), which already parses Python structure, is the
  honest place to add it.

### 1.2 Preventive mitigations

- **Module size limit.** *BY DISCIPLINE.* `AGENTS.md:59` ("LOCALITY LIMIT")
  tells a worker to split or flag a module that grows more than 15% or spawns
  duplicate functions. No code rejects an oversized diff. The autonomy
  blueprint turns this into a budget it can measure per increment, but it binds
  only new modules and edit sizes — see 1.3.
- **Dual-cadence (worker vs. architect passes).** *BY DISCIPLINE.* Feature work
  and structural simplification are kept to separate prompts by the shared
  optimizer workflow (`AGENTS.md:3`), not by a scheduler that alternates them.
- **Module-boundary declarations / `ARCHITECTURE.md`.** *OUT OF SCOPE for now.*
  There is no machine-checked ownership map; cross-boundary edits are not
  auto-rejected.

### 1.3 Honest reality of the size rule

The "modules under 300 lines" rule can bind **only new modules and edit sizes,
not the files as they stand**. At `f28bb7d` these are already over the flag:

| File | Lines |
|---|---|
| `overseer/policy.py` | 350 |
| `overseer/modelchoice.py` | 304 |
| `overseer/scheduler.py` | 372 |
| `overseer/__main__.py` | 391 |
| `overseer/workdiff.py` | 494 |
| `overseer/codemap.py` | 1292 |
| `overseer/factory.py` | 2395 |

Therefore every autonomy increment puts new logic in a **new module under 300
lines** and allows an over-limit file only a small call-site edit (at most 15
lines, and `overseer/factory.py` at most 40 lines per increment), with the work
log flagging it. The locality rule is stated honestly rather than pretended
met.

**Filed:** detection threshold and the size budget belong to the CONTEXT row
(`docs/HARNESS_FRAMEWORK.md:32`); the per-increment budgets are enforced by the
house rules in every autonomy prompt.

---

## Pillar 2 — gaming the harness (test drift, fake-green builds)

A worker makes the suite pass by weakening it: editing tests during
implementation, deleting cases, or replacing assertions with ones that cannot
fail.

### 2.1 Detection signals

- **A `tests/` file changed during an implementation attempt.** *DATA-ONLY.*
  The patch receipt lists every changed path with its status
  (`overseer/workdiff.py:340`), and a change the acceptance commands made *after*
  the implementation command is listed apart (`overseer/workdiff.py:477`), so a
  worker's edit to `tests/` is distinguishable in sealed evidence from a
  fixture the checks wrote. What is missing is the rejection: nothing yet fails
  the build when an implementation-phase diff touches `tests/`. *FILED; see
  2.3.*
- **Test count or duration dropping.** *OUT OF SCOPE for now.* The factory reads
  exit codes, not a worker's stdout test tally (`overseer/readback.py:153`), so
  a dropped-assertion count is not parsed. Counting would mean trusting a
  worker-printed number; the stronger control is the immutable-test rule below.

### 2.2 Preventive mitigations

- **Red–green separation (immutable tests).** *BY DISCIPLINE, FILED for
  enforcement.* `AGENTS.md:58` forbids a worker from editing any file under
  `tests/` during an implementation task. Today this is honored by the worker,
  not enforced by code. The enforcing control is the `tests/` sha256 the worker
  records in the red phase and must still match in the green phase — a protocol
  every autonomy increment runs, and the `diff.json` status list is the evidence
  that would let the orchestrator reject a violation automatically.
- **Assertion hardening.** *BY DISCIPLINE.* `AGENTS.md` forbids generic
  assertions (for example `assert result is not None`) and requires exact state
  or schema checks. Enforced in review, not by a linter.

### 2.3 What enforcement would be

An implementation-phase attempt whose `diff.json` shows any `tests/` path with a
status other than unchanged is a **fake-green** signal: the orchestrator fails
the attempt before reading exit codes. This is a bounded EVIDENCE check reading
only sealed data; it reuses `overseer/workdiff.py:477`'s separation of
worker edits from check-made changes.

**Filed:** EVIDENCE row (`docs/HARNESS_FRAMEWORK.md:36`). It is *not* one of the
current ten autonomy increments; it is recorded here as the next EVIDENCE
increment after them, so the gap is owned rather than forgotten.

---

## Pillar 3 — context rot and escalation cascades

A worker loops on a sub-task, each prompt drifting further from the spec, until
cost is spent on noise instead of escalating.

### 3.1 Detection signals

- **Repair-lineage strike count.** *IMPLEMENTED (autonomy increment 1).* A
  repair lineage relates each repair job to the job it repairs
  (`overseer/strikes.py:108`) and counts its consecutive non-`passed` terminal
  states, freezing at `min(3, 1 + repair_allowance)` (`overseer/strikes.py:52`,
  `overseer/strikes.py:132`). The strike is recorded in the same transaction as
  the job's final transition, in `run_one` (`overseer/factory.py:2439`) and in
  `resolve` (`overseer/factory.py:789`); a frozen lineage refuses a further
  repair until an operator releases it (`overseer/factory.py:814`). This is the
  user's "3 consecutive self-correction attempts" (`AGENTS.md:31`) and the
  blueprint's one attempt plus two repairs
  (`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:352`). Filed against the STATE row
  (`docs/HARNESS_FRAMEWORK.md:33`).
- **No-new-evidence repeat.** *IMPLEMENTED (autonomy increment 4).* A byte-equal
  fingerprint of the failing and not-run identifiers, the failing command's exit
  code and timeout flag, and the patch digest (`overseer/strikes.py:78`) freezes
  a lineage *before* its bound when two consecutive failed attempts repeat it
  unchanged (`overseer/strikes.py:201`, built at `overseer/factory.py:2414`). The
  comparison is byte-equal, never semantic. Filed against EVIDENCE
  (`docs/HARNESS_FRAMEWORK.md:36`).
- **Explicit escalation request.** *PARTIAL (parser and factory action
  IMPLEMENTED, autonomy increments 2–3; monitor action FILED, increment 6).* The
  `STATUS: STUCK_NEEDS_ESCALATION` line of the `AGENTS.md` status block
  (`AGENTS.md:62`) is parsed by a bounded, never-evaluated parser
  (`overseer/statusblock.py:96`) and now acted on in the factory: after the
  implementation command, the log is read and a stuck block freezes the job's
  lineage (`overseer/factory.py:2444`, `overseer/strikes.py:171`). The monitor
  still does not react to a stuck block in a pane; increment 6 adds that hold.
- **Hop-distance counter.** *FILED (subsumed by the lineage).* A per-prompt
  `hop_count` is realized as the lineage's strike chain rather than a free
  counter, so it is durable in the ledger and cannot be reset by a new prompt.

### 3.2 Preventive mitigations

- **Immutable ground-truth injection.** *PARTIAL + FILED.* The handoff record
  already carries the base and candidate revisions of each attempt
  (`overseer/handoff.py:66`, `overseer/handoff.py:187`), and the codebase map
  (`overseer/codemap.py:1058`) and recall (`overseer/factory.py:987`) hand the
  attempt its selected code and prior decisions. What is not yet injected into
  *every* prompt is the target's own `SPEC.md`; autonomy increment 8 adds the
  `SPEC.md` pointer (CONTEXT row, `docs/HARNESS_FRAMEWORK.md:32`).
- **Context reset on escalation.** *FILED (autonomy increment 10).* When a
  lineage freezes, the escalation prompt is built from ledger facts only — the
  lineage, the run ids, the failing identifiers, the freeze reason, and the
  evidence paths — never raw chat history or raw log text. Filed against
  PERMISSIONS (`docs/HARNESS_FRAMEWORK.md:35`).

---

## Pillar 4 — non-deterministic state and race conditions

Two writers collide on shared state, or a command hangs or flakes, and the
ledger stops reflecting reality.

### 4.1 Detection signals

- **Execution timeout breaker.** *IMPLEMENTED.* Every command runs under a
  wall-clock `timeout` and, in the `finally` path, its whole process group is
  killed with `SIGKILL` (`overseer/factory.py:1595`), so a runaway child cannot
  outlive its attempt. The bound is the task's per-command timeout, **not** a
  fixed 60 seconds; the fixed figure in earlier drafts is corrected here to the
  per-command value the spec sets.
- **Flakiness re-run.** *OUT OF SCOPE for now.* The factory does not re-run a
  failed command to probe for non-determinism; a re-run would be a new attempt
  with its own evidence. Recorded as a deliberate non-feature.

### 4.2 Preventive mitigations

- **Single-writer serialization.** *IMPLEMENTED.* Dispatch runs inside a
  `BEGIN IMMEDIATE` transaction (`overseer/factory.py:2217`), a worker lock
  serializes `run_one` (`overseer/factory.py:725`), and the controller row holds
  the epoch (`overseer/factory.py:428`). The monitor has its own single-writer
  lock (`overseer/__main__.py:265`). This is the race-condition control: shared
  state has exactly one writer at a time.
- **Fenced recovery.** *IMPLEMENTED.* Restore re-creates the side tables and
  fences the restored ledger under a fresh epoch (`overseer/factory.py:2133`,
  `overseer/factory.py:2168`), so a stale lease from before a restore cannot
  publish.
- **Ephemeral execution containers.** *PARTIAL.* A bubblewrap profile probes a
  disposable runtime and fails closed when `bwrap` is absent
  (`overseer/isolation.py:98`, `overseer/isolation.py:138`,
  `overseer/isolation.py:166`). It is a *probe* that records a verdict as
  evidence; it does **not** yet wrap the trusted argument-vector runner, so the
  real implementation command is not sandboxed. The TOOLS row states the same
  limit (`docs/HARNESS_FRAMEWORK.md:34`). Any real sandboxing of the runner is
  added only behind that proven boundary.

---

## Pillar 5 — orchestrator overhead complexity

The orchestrator grows until it, not the product, is where the bugs live, and
its state fragments across stores that disagree.

### 5.1 Detection signals

- **Meta-code ratio.** *OUT OF SCOPE as an automated metric.* No code computes
  orchestrator-LOC versus product-LOC. The locality facts in 1.3 are the honest
  proxy: the orchestrator is large (`overseer/factory.py` is 2395 lines), which
  is exactly why every increment is bounded and placed in a new small module.
  The ratio is watched by the size budgets, not by a threshold job.

### 5.2 Preventive mitigations

- **Single source of truth.** *IMPLEMENTED, with a stated divergence from the
  literal rule.* Overseer keeps **one** authoritative store, the SQLite ledger
  (`overseer/factory.py:414`), written by a single lock; it does not run
  multiple state databases. The literal advice "derive all state from git
  history" is **not** followed, by design: the ledger records tokens, approvals,
  memory kinds, and exit codes that git cannot express. Git is instead the
  **read-only authority for revisions**, and the reconciliation checks the
  ledger's record against the workspace HEAD (`overseer/reconcile.py:158`) and
  against the recorded exit codes (`overseer/readback.py:153`), reporting a
  disagreement rather than letting two stores drift silently
  (`overseer/reconcile.py:184`). The spirit of the mandate — no two stores
  disagreeing unnoticed — is met; the letter is deliberately not.
- **Bounded increments.** *BY DISCIPLINE, with teeth.* Every change is one
  commit with red-green phases, module-size budgets (1.3), and the two
  validators (`scripts/check`, `scripts/check-doc-references`). This is what
  keeps orchestrator complexity from compounding.

---

## Honest limits: what hardening cannot detect

Stated plainly, so no reader over-trusts these controls:

- **Whether a problem is architectural.** A worker that silently loops on a
  design flaw while changing its patch each time produces "new evidence" by the
  fingerprint rule (Pillar 3) and runs to its bound. The freeze is a cost cap,
  not an understanding of the flaw.
- **Whether a claim is honest.** A `SUCCESS` or `TESTS_PASSED: TRUE` claim is
  recorded and checked against exit codes (`overseer/readback.py:153`), never
  trusted. A worker cannot green a build by asserting it.
- **Scope and spec drift.** `SPEC.md` is supplied to the attempt (once increment
  8 lands) but never enforced; nothing proves the work stayed in scope.
- **Duplication, cycles, and complexity.** Not measured today (Pillar 1); the
  data to measure them exists in `codebase.json` and `diff.json`.
- **Flakiness.** Not probed (Pillar 4); a failure is one attempt's result.
- **Two stores still have two clocks.** The factory freeze lives in the ledger;
  the monitor's pane hold (autonomy increment 6) lives in the monitor's JSON
  state file. Neither sees the other, and this document says so rather than
  implying one authority.

## Scorecard at `f28bb7d`

| Failure mode | Detection | Mitigation | Owed to |
|---|---|---|---|
| 1 Locality trap | DATA-ONLY (loc delta in `diff.json`) | BY DISCIPLINE (size rule) | CONTEXT threshold increment |
| 2 Gaming the harness | DATA-ONLY (`tests/` edits in `diff.json`) | BY DISCIPLINE (red-green) | EVIDENCE enforcement increment |
| 3 Context rot / cascades | PARTIAL (lineage strike-count, status-block parser, factory-side stuck-escalation, and no-new-evidence early freeze IMPLEMENTED; monitor-side escalation FILED) | PARTIAL + FILED (ground truth, reset) | Autonomy increments 1–5 and 7–9 landed; 6 and 10 owed |
| 4 Non-determinism / races | IMPLEMENTED (timeout+SIGKILL) | IMPLEMENTED (single writer, fenced restore); PARTIAL (sandbox probe) | TOOLS row for real sandboxing |
| 5 Orchestrator overhead | OUT OF SCOPE (ratio); proxy via size budgets | IMPLEMENTED (one ledger; read-only git authority) | — |

The honest summary: **race-condition and recovery hardening is built; the
consecutive-failure freeze (autonomy increment 1) is now built too, so the
first cost-cap control exists, the status-block parser, the factory-side
stuck-escalation freeze, and the no-new-evidence early freeze are built too
(increments 2–4), while the rest of the cost-cap and escalation hardening is
specified; increments 5, 7, 8, and 9 (the unattended loop) are now built, leaving the monitor-side hold (6) and the Claude escalation route (10); architectural-rot
and test-drift detection have the evidence captured but not yet the thresholds
that act on it.** No mitigation on this page is claimed without a citation or a
filing.
