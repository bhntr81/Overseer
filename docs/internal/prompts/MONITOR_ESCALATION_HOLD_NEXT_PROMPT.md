# Increment 6: monitor escalation hold and pane 3-strike freeze

Repository: `/home/kali/Programming/Projects/Overseer` (branch as-is; work in this checkout).

Authoritative spec: `docs/AUTONOMY_BLUEPRINT.md:540-584` ("Increment 6: monitor escalation
hold and pane 3-strike freeze (PERMISSIONS, `docs/HARNESS_FRAMEWORK.md:35`)"). Pillar row:
`docs/HARNESS_FRAMEWORK.md:35` (PERMISSIONS). Read both before writing code; the three
"Decisions to settle" in the blueprint are settled below and are not open questions.

## 1. Objective

The monitor must stop sending to a pane, permanently, in exactly two situations: (a) the
current turn of that pane carries a valid AGENTS.md status block whose `STATUS:` is
`STUCK_NEEDS_ESCALATION` (parsed with `overseer/statusblock.py`), and (b) three consecutive
step reports of that pane show `TESTS_PASSED: FALSE` or an unchanged `remaining` fingerprint.
While a pane is held, the monitor sends it nothing at all — not a routine continuation, not a
report-based prompt, not a writer-handoff prompt, not a capacity retry, and not a routed-session
resume. The hold is persisted in the monitor's own JSON state file, survives restarts, and is
cleared only by an explicit operator command, `python3 -m overseer unfreeze <pane>`, which
clears exactly the named pane and no other.

## 2. Ground truth to re-read before coding

- `docs/AUTONOMY_BLUEPRINT.md:540-584` — the increment's objective, budgets, decisions, the
  five required test names, and the mutation table.
- `docs/AUTONOMY_BLUEPRINT.md:176-198` — the locality rule: new logic goes in a new module
  under 300 lines; an existing over-limit file gets at most 15 changed lines per increment and
  the work log flags it.
- `docs/HARNESS_FRAMEWORK.md:29-36` — the pillar table; row 35 is PERMISSIONS (this increment
  files against it). `docs/HARNESS_FRAMEWORK.md:71-82` — the "Two systems, not bridged"
  section that names System A (the terminal monitor) and System B (the factory).
- `overseer/policy.py:296` `classify`, `overseer/policy.py:319` `Policy.consider`,
  `overseer/policy.py:172` `stop_requested`, `overseer/policy.py:35` `STOP_REASON`,
  `overseer/policy.py:19` the `BLOCKED` deny list, `overseer/policy.py:40` `current_turn`,
  `overseer/policy.py:58` `fingerprint`, `overseer/policy.py:82` `_report_state` (the
  existing `OVERSEER_REPORT` parser), `overseer/policy.py:256-258` (the house rule: a reason
  is a fixed phrase and never includes report text).
- `overseer/statusblock.py:96` `parse` — returns `found`, `valid`, `reason`, `status`,
  `tests_passed`, `files_modified`, `next_instruction`; the last complete block wins; only
  the last 64 KiB is read.
- `overseer/__main__.py:19` (`STATE`), `:23` (`save`), `:211` (`tick`), `:219` (the
  `"<pane>:<pid>"` state key), `:231` (`policy.consider` in the plain path), `:249`/`:257`
  (the monitor rewrites the whole state file every poll), `:260` (`run`), `:303` (`main`),
  `:305` (subparsers), `:323` (the `model-select` subparser — copy its shape), `:331` (the
  action dispatch), `:371` (the house wording for "applied at the next poll").
- `overseer/scheduler.py:113` `_adopt_resolutions` and `:198` (where the monitor folds
  operator commands into its own state) — the pattern the `unfreeze` command must follow.
- `overseer/modelchoice.py:42` `RESOLUTIONS = "model-resolutions.json"` and
  `overseer/__main__.py:81-95` `resolve_decision` (how an operator command is written where a
  running monitor will read it).
- `overseer/strikes.py` — the factory-side 3-strike lineage freeze. It is a DIFFERENT store
  (sqlite, `overseer/factory.py`). Do not reuse it, do not extend it, do not write to it.
- `tests/test_policy.py` and `tests/test_monitor.py` — the house test style.

## 3. Files to change

| Path | Change | Budget |
|---|---|---|
| `overseer/escalation.py` | new module | ≤ 160 lines |
| `overseer/policy.py` | one hold call in `classify`, one hold gate in `Policy.consider` | ≤ +10 lines (hard ceiling +15, see §11) |
| `overseer/__main__.py` | the `unfreeze` subcommand, its branch, and the release fold in `tick` | ≤ +15 lines |
| `tests/test_policy.py` | the classification and precedence tests | — |
| `tests/test_monitor.py` | the monitor/state/unfreeze tests | — |

`overseer/policy.py` is already 350 lines and `overseer/__main__.py` is already 391 lines.
Both are over the 300-line flag in `docs/AUTONOMY_BLUEPRINT.md:180-188`; keep the edits to
call sites, and say so in `WORK_LOG.md`. `overseer/scheduler.py` should not need to change:
`Policy.consider` is the single send funnel that both `overseer/__main__.py:231` and
`overseer/scheduler.py:288` go through.

## 4. Required behaviour

### 4.1 Trigger A — a valid `STATUS: STUCK_NEEDS_ESCALATION` block in the CURRENT turn

- Take the current turn with `overseer.policy.current_turn(text)` and parse it with
  `overseer.statusblock.parse`.
- The pane is held immediately when the parse is `found` AND `valid` AND
  `status == "STUCK_NEEDS_ESCALATION"` (`overseer.statusblock.STATUS_STUCK`).
- A block in an earlier turn (above the last submitted prompt line) does NOT hold the pane.
- An invalid block (unfilled template, unknown status, bad instruction) does NOT hold the pane.
- A valid `STATUS: SUCCESS` block does NOT hold the pane by itself.

### 4.2 Trigger B — three consecutive failed or unchanged step reports

Definitions, exactly:

- **Step report.** The current turn carries report evidence: a valid AGENTS.md status block
  (`statusblock.parse(current_turn)` is `found` and `valid`) and/or an `OVERSEER_REPORT` line
  whose `status` is `continue` or `step_done` (reuse `overseer.policy._report_state`, which
  returns `("ready", fields)` for `continue` and `("handoff", fields)` for `step_done`; do not
  write a second `OVERSEER_REPORT` parser).
- **Remaining fingerprint.** `overseer.policy.fingerprint` of the whitespace-collapsed
  `remaining` field of the current turn's `OVERSEER_REPORT`; if the turn has no
  `OVERSEER_REPORT`, the fingerprint of the status block's `next_instruction`; if it has
  neither, the step report has no remaining fingerprint.
- **Strike.** A step report is a strike when the status block is valid and its
  `tests_passed` is `False`, OR when its remaining fingerprint equals the remaining
  fingerprint of that pane's previous step report.
- **Reset.** A step report that is neither failed nor unchanged resets the pane's strike
  counter to 0.
- **No report.** A turn with no report evidence at all must NOT reset the counter and must
  NOT advance it. The counter only moves on a step report.
- **One count per report.** The same report evidence observed on two consecutive polls counts
  once. The identity of a counted report is the fingerprint of the canonical report evidence
  (the status block lines plus the `OVERSEER_REPORT` line). Two polls of the same report
  advance the counter by one, not two.
- **Freeze.** The third consecutive strike freezes the pane.

### 4.3 Precedence, on every path (normal, `capacity=True`, `resume=True`)

1. `stop_requested(text)` first. A screen that asks for input still reports exactly
   `"client requested no further automatic continuation"` (`overseer.policy.STOP_REASON`),
   even when the pane is held or carries a `STUCK_NEEDS_ESCALATION` block.
2. Then the hold: `(False, <fixed hold reason>)`.
3. Then everything else: the `BLOCKED` deny list, the handoff decision, the completion
   decision, the routine-continuation question, the capacity retry, and the routed-session
   resume.

The hold therefore precedes every send path. A frozen pane never receives a capacity retry
(`capacity=True`) and never receives a routed-session resume (`resume=True`). Today
`Policy.consider` short-circuits to `"model capacity retry"` / `"routed session needs a
continuation"` without calling `classify` (`overseer/policy.py:325-330`), so `consider` must
evaluate the stop reason and the hold itself before those branches. Put the hold check
immediately after the `stop_requested` check and before the `BLOCKED` deny list, so a frozen
pane reports the freeze rather than a transient screen reason.

Reason phrases are fixed strings that contain no report text (house rule,
`overseer/policy.py:256-258`). Use these two exact phrases so the tests can assert them:

- `HOLD_ESCALATION = "status block reports STUCK_NEEDS_ESCALATION"`
- `HOLD_STRIKES = "three consecutive failed or unchanged step reports"`

### 4.4 Persistence

- The hold lives in the monitor's JSON state file only (`~/.local/state/overseer/state.json`
  by default, `overseer/__main__.py:19`), inside that pane's own entry (the
  `"<pane>:<pid>"` key built at `overseer/__main__.py:219` and `overseer/scheduler.py:185`).
- The factory ledger (sqlite, `overseer/factory.py`) and `overseer/strikes.py` are a
  different store and must not receive the monitor's hold. `overseer/factory.py` and
  `overseer/strikes.py` are not to be modified at all.
- A new turn, a changed screen, and a monitor restart do NOT clear the hold. The hold is in
  the state file, and the state file is reloaded on restart (`overseer/__main__.py:269`).
- A replaced pane process is a new `"<pane>:<pid>"` key, therefore a new entry, therefore
  NOT frozen. This is a real limit of the design and must be named in the docs (§10).
- Only the explicit `unfreeze <pane>` command clears the hold.

### 4.5 The `unfreeze` command

```
python3 -m overseer unfreeze <pane> [--state PATH]
```

- `<pane>` is required and is the tmux pane ID, e.g. `%0`.
- `--state` is the monitor state file; default `STATE` (`overseer/__main__.py:19`), exactly
  like the `model-select` subparser (`overseer/__main__.py:327`).
- Exit 0, stdout: `unfreeze: %0; applied at the next poll (within 30 seconds)` — the number
  comes from `config.json`'s `poll_seconds`, and the wording matches
  `overseer/__main__.py:371`.
- Exit 1, stderr: `No hold is recorded for %0.` when the state file holds no freeze for that
  pane.
- It clears ONLY the named pane: every state entry whose key starts with `"<pane>:"`. Every
  other pane keeps its freeze and its strike counter.
- The release also resets that pane's strike counter, so the pane starts clean and the
  counter can build again.
- **Race with a running monitor.** The monitor keeps the state in memory and rewrites the
  whole file on every poll (`overseer/__main__.py:249`, `:257`, `overseer/scheduler.py:312`,
  `:361`). The CLI must therefore NOT write the state file. Follow the pattern the codebase
  already uses for operator model decisions: the CLI writes a sidecar file beside the state
  file (`<state dir>/escalation-releases.json`, the name exported as `RELEASES` from
  `overseer/escalation.py`), and the monitor folds that file into its own state at the start
  of each tick — the way `overseer/scheduler.py:_adopt_resolutions` folds
  `model-resolutions.json`.
- The release record must name the specific hold it releases (the hold's `id`), so a stale
  release record left in the sidecar can never clear a later freeze of the same pane. The
  fold ignores a record whose id does not match the pane's current hold.
- The fold must run for both monitor paths. `overseer/__main__.py:211` `tick` delegates to
  `overseer/scheduler.py:174` `tick_queue` when `serial_queue` is on (it is on in the shipped
  `config.json`), so fold the releases in `overseer/__main__.py:tick` BEFORE that delegation
  — one fold site covers the plain path and the queue path.

## 5. The module contract for `overseer/escalation.py`

- `RELEASES = "escalation-releases.json"` — the sidecar name, written beside the state file.
- `HOLD_ESCALATION`, `HOLD_STRIKES` — the two fixed reason phrases from §4.3.
- The pane entry carries one key, `"escalation"`, whose value is
  `{"held": {"reason": str, "at": float, "id": str} | None, "strikes": int,
  "last_remaining": str | None, "last_report": str | None}`. The `id` is
  `overseer.policy.fingerprint` of the reason and the time it was set, so it is unique per
  freeze and can be matched exactly by a release record.
- At least these operations, with these responsibilities (names may differ if the behaviour
  and the tests below are unaffected):
  - evaluate the two triggers for one pane entry against a screen, record the strike counter
    and the freeze in the entry, and return the hold reason or `None`;
  - read the recorded freeze of an entry;
  - the CLI side: find the frozen entries of one pane in a state dict and write the release
    record to the sidecar;
  - the monitor side: read the sidecar and clear the matching freezes in a state dict.
- Import rule (mandatory): `overseer/escalation.py` MAY import `overseer.policy` and
  `overseer.statusblock` at module level. `overseer/policy.py` MUST NOT import
  `overseer.escalation` (and therefore must not import `overseer.statusblock`) at module
  import time, because `overseer/statusblock.py:24` imports from `overseer.policy` — a
  module-level import in `policy.py` closes the cycle. The call into `overseer.escalation`
  must be a lazy import inside the function body.
- `classify` needs the pane's state to record a hold, so give it an optional keyword
  argument (e.g. `state=None`) and have `Policy.consider` pass the pane entry. `classify(text)`
  with no state still detects trigger A (it is a property of the text) but cannot record
  anything.
- `overseer/scheduler.py:67` calls `classify(text)` as a phase heuristic with no state. A
  `STUCK_NEEDS_ESCALATION` screen therefore classifies as not-eligible there and the pane's
  queue phase becomes `unknown` instead of `finished`. That is acceptable: the pane is still
  never sent to, because `Policy.consider` applies the hold. Record this consequence
  honestly in `WORK_LOG.md`.

## 6. The five required tests

The names are verbatim from `docs/AUTONOMY_BLUEPRINT.md:570-575`. All five must exist and pass.

### `tests/test_policy.py`

**`test_stuck_needs_escalation_holds_the_pane`** — classification behaviour.
- A screen whose current turn carries a valid status block with
  `STATUS: STUCK_NEEDS_ESCALATION` plus a routine continuation question:
  `classify(screen)` returns `(False, HOLD_ESCALATION)` — assert the exact phrase.
- The same screen with `STATUS: SUCCESS` is still eligible: `classify(screen)[0]` is `True`.
- The unfilled template (`STATUS: [SUCCESS | STUCK_NEEDS_ESCALATION]`) does not hold the pane:
  `classify(screen)[0]` is `True`.
- A `STUCK_NEEDS_ESCALATION` block above a submitted prompt line (an earlier turn) does not
  hold the pane: `classify(screen)[0]` is `True`.
- `Policy.consider(entry, screen, 0)` returns `(False, HOLD_ESCALATION)` and the entry
  records the freeze (`entry["escalation"]["held"]` is not `None`).

**`test_a_frozen_pane_is_not_sent_a_capacity_retry`** — the capacity path.
- Freeze the pane first (a `Policy.consider` on the `STUCK_NEEDS_ESCALATION` screen, or by
  writing the hold into the entry).
- `policy.consider(entry, CAPACITY_SCREEN, now, capacity=True)` returns
  `(False, HOLD_ESCALATION)`; the reason is NOT `"model capacity retry"`.
- `policy.consider(entry, ROUTED_SCREEN, now, resume=True)` returns `(False, HOLD_ESCALATION)`;
  the reason is NOT `"routed session needs a continuation"`.
- The held consider reserves nothing: the entry has no `last_sent` and no new `sent_times`
  entry.
- `CAPACITY_SCREEN` is the house capacity text
  (`"■ Selected model is at capacity. Please try a different model.\n›"`).

**`test_the_daily_limit_and_needs_input_still_stop_first`** — precedence.
- A screen that carries `OVERSEER_NEEDS_INPUT` AND a `STUCK_NEEDS_ESCALATION` block, on an
  entry that is already frozen: `policy.consider(entry, screen, 0)` returns
  `(False, "client requested no further automatic continuation")` — the exact `STOP_REASON`,
  not the hold reason.
- `classify(NEEDS_INPUT_SCREEN)` returns `(False, STOP_REASON)`.
- The daily limit still applies unchanged on a pane that is not held:
  `Policy(max_per_day=1)` with `sent_times == [0]` and `now == 100` returns
  `(False, "daily reply limit")` on an eligible screen.
- The hold does not count a reply: after a held `consider`, the entry's `sent_times` is
  unchanged and `last_sent` is absent.

### `tests/test_monitor.py`

**`test_three_failed_step_reports_freeze_the_pane`** — the strike counter, across polls.
- Drive `overseer.__main__.tick` over a sequence of screens for one pane
  (`Snapshot("%0", "codex", "123", text, "›", "0", "0")`, the shape used in
  `tests/test_monitor.py:12`):
  1. failing report A (a valid status block with `TESTS_PASSED: FALSE` and/or an
     `OVERSEER_REPORT` with `status: "continue"`);
  2. the SAME screen A again (a second poll);
  3. a screen with NO report evidence at all;
  4. failing report B;
  5. failing report C.
- After step 2 the counter is exactly 1: the same report observed twice counts once.
- After step 3 the counter is still exactly 1: a screen with no report neither advances nor
  resets it. (This is the assertion that kills the "counter reset on any new screen"
  mutation.)
- After step 5 the counter is exactly 3, `entry["escalation"]["held"]` is not `None`, and its
  reason is `HOLD_STRIKES`.
- The pane is never sent to after it is frozen: `backend.send` is not called for report C or
  for any later poll (a further poll with a plain routine question is also not sent).
  Assert the exact `backend.send.call_count` for the whole sequence and state in the test
  which sends are expected before the freeze. Screens 1–4 must be constructed so that the
  only reason screen C is not answered is the freeze: give them a routine continuation
  question so that an implementation without the freeze would answer them.
- The freeze survives a restart: reload the state from the state file
  (`json.loads(path.read_text())`) and the hold is still there.

**`test_unfreeze_clears_only_the_named_pane`** — the command and the monitor fold.
- Freeze two panes (`%0` and `%1`) through ticks so that the state file on disk holds both
  freezes.
- Run the command end to end (`subprocess` like `tests/test_cli.py:14`, or `main()` with a
  patched `sys.argv`): `python3 -m overseer unfreeze %0 --state <path>`.
  - exit code 0, and stdout contains `unfreeze: %0`;
  - the release record was written beside the state file
    (`<state dir>/escalation-releases.json`);
  - the state file on disk is untouched by the command itself (the monitor owns it).
- Run one more monitor tick: the release is folded, `%0`'s entry has no freeze and its strike
  counter is 0, while `%1`'s entry still holds its freeze and its counter.
- `python3 -m overseer unfreeze %2 --state <path>` for a pane that was never frozen: exit code
  1 and stderr contains `No hold is recorded for %2.`

## 7. Mutations that must fail

Break each mutation on purpose, watch the named test fail, then revert it. Record the real
result in `WORK_LOG.md`. From `docs/AUTONOMY_BLUEPRINT.md:577-583`:

| Mutation | Must be caught by |
|---|---|
| hold skipped for capacity | `test_a_frozen_pane_is_not_sent_a_capacity_retry` |
| counter reset on any new screen | `test_three_failed_step_reports_freeze_the_pane` |
| hold placed before `stop_requested` | `test_the_daily_limit_and_needs_input_still_stop_first`, through the stop reason |

## 8. Verification (execute, do not assume)

```sh
python3 scripts/check </dev/null
python3 scripts/check-doc-references
python3 scripts/check-doc-references docs/AUTONOMY_BLUEPRINT.md
python3 scripts/check-doc-references README.md
```

- `scripts/check` runs the whole suite with an isolated `TMUX_TMPDIR`. It must end with
  `OK` and no failures or errors. The baseline before your change is `Ran 463 tests ... OK`,
  so the finished suite must report at least 468 tests (463 + the 5 new named tests).
- `scripts/check-doc-references` must exit 0 for all three documents: every `path:line`
  citation must resolve to an existing file and an in-range line.
- The edits shift line numbers, so every citation into the files you changed must be
  re-mapped by content, not by arithmetic: 18 `overseer/policy.py` and 7
  `overseer/__main__.py` citations in `docs/HARNESS_FRAMEWORK.md`, and 15
  `overseer/policy.py` and 6 `overseer/__main__.py` citations in
  `docs/AUTONOMY_BLUEPRINT.md`. `README.md` carries no `path:line` citations today; keep it
  that way or fix them if you add any.
- Red-green discipline: write the five tests first, record the `sha256sum` of
  `tests/test_policy.py` and `tests/test_monitor.py`, then implement. During the
  implementation phase `tests/` is read-only and the digests must still match. Phase 0
  re-reads the ground truth above; Phase 3 is the mutation table; Phase 4 is the docs;
  Phase 5 is this verification and one commit.

## 9. Documentation and bookkeeping

- `docs/AUTONOMY_BLUEPRINT.md` — mark increment 6 LANDED in the increment 6 section
  (`:540`), in the same style as the landed increments 5 and 7 (a short quoted note with
  what landed, the real line counts, the real test counts, and the honest limits). Update the
  M3-b and M3-c bullets (`:153-164`) so they no longer say the monitor does not react to
  `STUCK_NEEDS_ESCALATION`.
- `docs/HARNESS_FRAMEWORK.md` — update the PERMISSIONS pillar row (`:35`) with the hold, the
  unfreeze command, and citations to the new code; update the System A description in
  "Two systems, not bridged" (`:73-76`); and add a bullet under "What this framework does
  not claim" naming the honest limits: the freeze lives in the monitor's JSON state file and
  the factory's freeze lives in the sqlite ledger, and neither sees the other; a replaced
  pane process (a new `<pane>:<pid>` key) is a new entry and is not frozen; the hold is a
  gate on sending, not a way to verify that the work is progressing.
- `README.md` — add the `unfreeze` command to the monitor's command list (beside the pane
  management commands at `:448-455`) and describe the hold behaviour and its limits in the
  monitor section.
- `WORK_LOG.md` — append an honest entry: what landed, the real line counts per file, the
  real test counts (before and after), the real mutation results (which mutation was broken
  and which named test failed), the citation remap count, and the honest limits (the
  replaced-pane-process limit, the separate stores, the phase-heuristic consequence in
  `overseer/scheduler.py:67`, and the sidecar's one-poll delay).
- Commit: stage files explicitly, one commit, house-style message, e.g.
  `Hold a pane that asks for escalation or fails three times in a row`.

## 10. Constraints

- Stay inside this one increment. Do not start increment 7, increment 10, or any other
  objective; do not add features that the blueprint does not name.
- Do not modify `overseer/factory.py`, `overseer/strikes.py`, or anything in the sqlite
  ledger. The monitor's hold and the factory's lineage freeze are separate stores.
- Do not weaken, skip, disable, or delete any existing test. The 463 existing tests must all
  still pass.
- No placeholder stubs, no `TODO`, no dead code: production-ready code with complete logic.
- The working tree already has unrelated uncommitted changes: `AGENTS.md`,
  `HARDENING_BLUEPRINT.md`, `docs/AUTONOMY_BLUEPRINT.md`, `docs/HARNESS_FRAMEWORK.md`,
  `overseer/orchestrate.py`, `tests/test_loop.py`. Preserve them and commit them WITH this
  work; do not revert them, and do not rewrite them beyond the doc edits this increment
  requires.
- Do not stage the untracked scratch files (`DESCRIPTION.txt`,
  `ESCALATION_ROUTE_NEXT_PROMPT.md`, `MONITOR_ESCALATION_HOLD_NEXT_PROMPT.md`,
  `future_ideas_and_architecture_roadmap.md`). Stage explicitly the six modified tracked
  files plus the increment's own files.
- The verification must actually be executed. Do not report a result you did not observe.

## 11. Done when

1. `overseer/escalation.py` exists, is at most 160 lines, and holds no I/O outside the state
   file, the sidecar, and the standard library.
2. `overseer/policy.py` grew by at most 15 changed lines (target ≤ 10) and
   `overseer/__main__.py` by at most 15; `overseer/factory.py` and `overseer/strikes.py` are
   byte-identical to their committed state.
3. The five named tests exist in the two specified files and pass.
4. `python3 scripts/check` ends with `OK`, at least 468 tests, no failures and no errors.
5. `python3 scripts/check-doc-references` exits 0 for `docs/HARNESS_FRAMEWORK.md`,
   `docs/AUTONOMY_BLUEPRINT.md` and `README.md`, with every citation re-mapped by content.
6. Each of the three mutations was confirmed to fail the named test and was reverted.
7. A frozen pane is not sent to on any path: normal, capacity retry, and routed resume.
   `python3 -m overseer unfreeze %0` clears that pane only, and the release reaches the
   running monitor through the sidecar fold.
8. `docs/AUTONOMY_BLUEPRINT.md`, `docs/HARNESS_FRAMEWORK.md`, `README.md` and `WORK_LOG.md`
   carry the honest update, and the work is committed in one clean commit with the six
   pre-existing modified files included.

## 12. Stopping condition

Stop when increment 6 is implemented, verified, documented, and committed, and the commit
exists. Then report the real numbers: the line counts per file, the test counts before and
after, which mutation failed which named test, and the honest limits. Do not begin increment
7, increment 10, or any other objective, and do not add work beyond this increment.
