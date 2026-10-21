# Increment 11: explicit halted status — record, announce and render intentional monitor halts

Repository: `/home/kali/Programming/Projects/Overseer` (branch as-is; work in this checkout).

Authoritative spec: `docs/AUTONOMY_BLUEPRINT.md`. Its increment list runs 1..10 (increment 10 is
`docs/AUTONOMY_BLUEPRINT.md:796`, landed); **this work is increment 11**. Pillar row:
`docs/HARNESS_FRAMEWORK.md:35` (PERMISSIONS) — the monitor's gate on sending. Read both documents
before writing code. The operator's task is reproduced in §1; every design decision below is
settled and is **not** an open question. Do not re-open them.

The prompt that produced this work was written by the dedicated prompt-writing agent
(`MONITOR_HALT_NOTICE_NEXT_PROMPT.md`); the executing agent implements it and records that
authorship in `WORK_LOG.md`.

## 1. Objective

The monitor currently stops answering a pane silently. When a pane hits a policy gate — the client
asked for no further automatic continuation, the turn carries `OVERSEER_NEEDS_INPUT`, a report
ended the continuation, the pane is held by the escalation gate, the model decision is pending,
the credits are exhausted, the work was routed away, or the capacity retry limit was reached — the
monitor either logs a bare debug line or stops logging entirely, and `overseer status` shows
nothing about it, so an intentional wait looks exactly like a crash, a stall or a socket failure.
This increment makes those halts explicit, without changing a single send decision:

1. **Status view visibility** — `python3 -m overseer status` gains a dedicated section (header
   containing the word `HALTED` and the word `PAUSED`) that lists every halted pane, including
   panes whose tmux session has already closed, each with its kind, the exact reason printed as
   `Reason: <reason>`, and the action that resumes it.
2. **Explicit event logging** — on the transition *into* a halt the monitor logs exactly
   `[OVERSEER] Session <session_name> paused automatic turns: <reason>` through the `overseer`
   logger at INFO, plus a second line naming what resumes it. The same reason is never
   re-announced on every poll.
3. **Guardrails preserved** — nothing changes about *when* the monitor sends. `overseer/policy.py`
   keeps its send decisions byte-for-byte; a stopped or held pane still receives no automated
   reply of any kind. The work is recording, announcing and rendering only.
4. **Testing and verification** — new unit tests cover the state transitions for
   `client requested no further automatic continuation` and `OVERSEER_NEEDS_INPUT`, and the full
   suite passes (`python3 scripts/check`).

## 2. Ground truth to re-read before coding

- `docs/AUTONOMY_BLUEPRINT.md:176-198` — the locality rule: new logic goes in a **new module under
  300 lines**; an existing over-limit file gets **at most 15 changed lines** per increment and the
  work log flags it. `docs/AUTONOMY_BLUEPRINT.md:215-230` — the ordered increment list (add item
  11 there). `docs/AUTONOMY_BLUEPRINT.md:796-849` — the house format of a landed increment (the
  quoted "Landed" note). `docs/AUTONOMY_BLUEPRINT.md:850-889` — the honest-limits section.
- `docs/HARNESS_FRAMEWORK.md:29-36` — the pillar table; row 35 is PERMISSIONS (this increment files
  against it). `docs/HARNESS_FRAMEWORK.md:71-86` — "Two systems, not bridged" (System A is the
  terminal monitor). `docs/HARNESS_FRAMEWORK.md:87-168` — "What this framework does not claim",
  where this increment's honest limits go.
- `HARDENING_BLUEPRINT.md:95-114` — the honest reading of the 300-line rule: it binds new modules
  and edit sizes, not the files as they stand.
- `overseer/__main__.py` — the monitor. `STATE` at `:20` (the state file path), `save` at `:24`,
  `LOG` at `:21`, `settings` at `:35`, `decisions` at `:66` (the tolerant state-file read pattern),
  `tick` at `:212` (the plain, non-queue send path), the pane key `f"{pane}:{snapshot.pid}"` at
  `:221`, `entry = state.setdefault(key, {})` at `:222`, `policy.consider(...)` at `:233`, the
  `not eligible` branch at `:234-236`, `next_prompt` at `:237`, the `prompt is None` branch at
  `:238-241`, `policy.acknowledge` at `:250`, `backend.send` at `:252`, `run` at `:262`, `main` at
  `:305`, the `status` subcommand branch at `:338-366`, the `unfreeze` branch at `:383-390`.
- `overseer/scheduler.py` — the FIFO queue path. `LOG` at `:18`, `phase` at `:48`, `tick_queue` at
  `:174`, the per-pane loop at `:225-306`, the `stopped` phase branch at `:233-235` (it sets
  `entry['queue_reason']` to the client stop reason **without** calling `consider`), the
  `model_blocked` branch at `:236-275` (it sets `model decision pending: …`, `routed to …` and the
  exhausted-credit status), the capacity retry limit at `:283-285`, `entry['queue_reason'] = reason`
  at `:298`, `save(path, state)` at `:312`, `backend.send` at `:362`.
- `overseer/policy.py` — `STOP` at `:29`, `DONE_MARK` at `:30`, `NEEDS_INPUT_MARK` at `:31`,
  `STOP_REASON` at `:35`, `current_turn` at `:40`, `stop_requested` at `:172`,
  `next_prompt` at `:255`, the report stop reason `"output report requested no further
  continuation"` at `:272`, `hold` at `:290`, `classify` at `:296`, `Policy` at `:318`,
  `Policy.consider` at `:325`, the stop/hold gate at `:333`. The house rule at `:256-258`: a reason
  is a fixed phrase and never contains report text.
- `overseer/escalation.py` — `HOLD_ESCALATION` at `:24`, `HOLD_STRIKES` at `:25`, `classify` at
  `:56`, `release` at `:117`, `adopt` at `:137`. These two phrases are intentional halts.
- `overseer/route.py:39` — `session_name(pane)`, the existing way to read a pane's tmux session
  name. Reuse it; do not write a second tmux query.
- `overseer/modelchoice.py:51` — `EXHAUSTED = "CREDITS_EXHAUSTED_WAITING"`, the default
  exhausted-credit status (overridable by `fallback_policy.exhausted_status` in `config.json`).
- `overseer/tmux.py` — `Snapshot` at `:51` (it carries no session name), `inventory` at `:99`,
  `panes` at `:136`, `snapshot` at `:152`.
- `tests/test_monitor.py` — the plain-path tick pattern (`:43-57`, `:117-140`), the escalation
  tests (`:195-268`), the `Snapshot` shape at `:15`.
- `tests/test_scheduler.py` — the queue-path setup (`:19-37`), the stopped-pane test at `:86-95`.
- `tests/test_model_choice.py:193-200` — the house pattern for driving the `status` command:
  `patch.object(sys, 'argv', ['overseer', 'status', '--state', str(path)])`, `patch('sys.stdout',
  buffer)`, `main()`.

## 3. Files to change and budgets

| Path | Change | Budget |
|---|---|---|
| `overseer/halt.py` | **new** module: halt vocabulary, per-pane halt record, transition notice, status rendering | under 300 lines (target ≤ 200) |
| `overseer/__main__.py` | 3 call sites in `tick` (`:234-241`, `:252`), the `status` branch (`:338-366`), 1 import | **≤ 15 changed lines** |
| `overseer/scheduler.py` | the queue-path record call, the clear-on-send call, 1 import | **≤ 15 changed lines** |
| `tests/test_halt.py` | **new** file: the new module's own unit tests | — |
| `tests/test_monitor.py` | the plain-path halt tests | — |
| `tests/test_scheduler.py` | the queue-path halt test | — |
| `docs/AUTONOMY_BLUEPRINT.md` | increment 11 marked LANDED, ordered list, honest limits | — |
| `docs/HARNESS_FRAMEWORK.md` | PERMISSIONS row + a "does not claim" bullet | — |
| `README.md` | the halted-session section | — |
| `WORK_LOG.md` | the honest entry | — |
| `MONITOR_HALT_NOTICE_NEXT_PROMPT.md` | this prompt, committed with the work (house pattern, see commit `cd3cc3b`) | — |

`overseer/__main__.py` is 404 lines and `overseer/scheduler.py` is 372 lines; both are already over
the 300-line flag (`docs/AUTONOMY_BLUEPRINT.md:180-188`). Their edits are **call sites only**, at
most 15 changed lines each, and `WORK_LOG.md` must say so.

**These files must not change at all** (byte-identical to their committed state):
`overseer/policy.py`, `overseer/escalation.py`, `overseer/factory.py`, `overseer/strikes.py`,
`overseer/statusblock.py`, `overseer/modelchoice.py`, `overseer/route.py`, `overseer/tmux.py`,
`overseer/orchestrate.py`. `overseer/policy.py` staying untouched is how requirement 3
("preserve the safety guardrails") is proved, not merely asserted.

## 4. Required behaviour

### 4.1 The new module `overseer/halt.py`

It owns the halt vocabulary, the per-pane halt record, the transition notice and the rendering of
the halted status section. It must expose (names may differ if the behaviour below is unaffected):

- the two kind tokens `HALTED` and `PAUSED`;
- `note(entry, reason, text, pane, now, session=None)` — classify the reason, record the halt in
  the pane's own state entry, and log the notice when the transition is new. It returns the record
  when it created or changed one, and `None` otherwise. It never clears a record.
- `clear(entry)` — remove the pane's halt record after a successful send.
- `render(state)` — the lines of the halted status section for a whole state dict.
- `session_of(pane)` — the tmux session name of a pane, falling back to the pane id.

**Import rules (mandatory).** `overseer/halt.py` MAY import `overseer.policy` (for `STOP_REASON`,
`NEEDS_INPUT_MARK`, `current_turn`) and `overseer.escalation` (for `HOLD_ESCALATION`,
`HOLD_STRIKES`) and `overseer.route` (for `session_name`) at module level. Nothing in those
modules imports `overseer.halt`, so no cycle is created. Note the existing pattern:
`overseer/statusblock.py` imports `overseer.policy` at module level, and `overseer/policy.py`
imports `overseer.escalation` **lazily inside `classify`** (`:301-304`) for exactly this reason —
do not add a module-level import of `overseer.halt` to `overseer/policy.py`.

**The record.** In the pane's own state entry (the `"<pane>:<pid>"` key), under the key `"halt"`:

```python
entry["halt"] = {"reason": str, "kind": "HALTED" | "PAUSED", "resume": str,
                 "session": str, "pane": str, "at": float}
```

It lives **only** in the monitor's JSON state file. It is never written to the factory's sqlite
ledger, and it is never written to any other store.

### 4.2 Which reasons are intentional halts

Only the reasons in this table are recorded. Everything else is transient.

| Recorded reason (exact text) | Kind | Resume action |
|---|---|---|
| `client requested no further automatic continuation` (`overseer.policy.STOP_REASON`) | HALTED | the client asked to stop; answer it in the pane to resume |
| `OVERSEER_NEEDS_INPUT` | HALTED | the client is waiting for an answer; answer it in the pane to resume |
| `output report requested no further continuation` (`overseer/policy.py:272`) | HALTED | the report ended the automatic continuation; continue the work in the pane to resume |
| `status block reports STUCK_NEEDS_ESCALATION` (`overseer.escalation.HOLD_ESCALATION`) | HALTED | `python3 -m overseer unfreeze <pane>` |
| `three consecutive failed or unchanged step reports` (`overseer.escalation.HOLD_STRIKES`) | HALTED | `python3 -m overseer unfreeze <pane>` |
| `model decision pending: <name>` | PAUSED | `python3 -m overseer model-select <pane>` |
| the exhausted-credit status: `CREDITS_EXHAUSTED_WAITING` or any other `CREDITS_EXHAUSTED…` status | PAUSED | wait for the credits to reset |
| `routed to <provider>` / `routed to <provider> (<session>)` | PAUSED | the work moved to another session; this pane stays paused |
| `capacity retry limit reached; manual intervention needed` | PAUSED | manual intervention needed; the pane is not retried |

**Transient reasons — never recorded, never written over an existing record, and never used to
clear one:** `waiting for idle threshold`, `cooldown`, `already replied to this screen`,
`no recognized routine continuation question`, `active generation, permission, or sensitive action
visible`, `dead or stale process`, `output report withheld`, and **every reason not in the table
above** — including `daily reply limit`, `model capacity retry`, `routed session needs a
continuation`, `routine continuation question`, `completed turn with empty composer`,
`invalid output report`, `report has no remaining work`, `step report belongs to an earlier turn`,
`finished step; writer handoff due` and `model decision applied: …`. The default is transient:
a reason that is not in the table is not a halt.

### 4.3 The exact recorded reason

The policy returns one reason for two different situations, so the module must distinguish them
from the screen text:

- When the **current turn** carries the `OVERSEER_NEEDS_INPUT` marker, the recorded and printed
  reason is the marker itself: `OVERSEER_NEEDS_INPUT`.
- Any other client stop (an `OVERSEER_DONE` marker, or a plain stop) records the fixed phrase
  `client requested no further automatic continuation`.

Use `overseer.policy.NEEDS_INPUT_MARK` and `overseer.policy.current_turn` — do not re-write the
marker pattern, and do not search the whole screen: a marker in an **earlier** turn (above the last
submitted prompt line) must not change the recorded reason. Keep the house rule that a reason is a
fixed phrase and never contains report text.

### 4.4 The notice

On the transition **into** a halt — a halting reason recorded where the entry had no halt record,
or a **different** halting reason — log exactly these two lines through the `overseer` logger at
INFO (the logger every monitor module uses: `overseer/__main__.py:21`, `overseer/scheduler.py:18`):

```text
[OVERSEER] Session <session_name> paused automatic turns: <reason>
[OVERSEER] Session <session_name> resumes when: <resume action>
```

The first line's text must be exactly `[OVERSEER] Session <session_name> paused automatic turns:
<reason>`. The second line names what input or action is expected to resume the automatic turns
(the `resume` text of §4.2, which for the escalation holds is the `python3 -m overseer unfreeze
<pane>` command).

- The **same** reason must not re-announce on every poll. A second poll with the same reason
  returns `None`, logs nothing, and leaves the record's `at` unchanged.
- A **different** halting reason is a new transition: the record is replaced and the notice is
  logged again.
- The session name is the tmux session name of the pane, **resolved once at the transition** and
  stored in the record, so it is still printable after the session is gone. Resolve it with
  `overseer.route.session_name(pane)`; when that fails (the pane or the tmux server is gone) fall
  back to the pane id. Do not resolve it on every poll.

### 4.5 Where the recording happens

**The plain path — `overseer/__main__.py:tick`.**

- The `not eligible` branch (`:234-236`): the reason from `policy.consider` is a halt reason for
  a stopped or held pane → record it.
- The `prompt is None` branch (`:238-241`): `hold(entry, snapshot.text, kind)` records the report
  stop reason (`output report requested no further continuation`) → record it.
- A **successful** `backend.send(snapshot, prompt)` (`:252`) clears the pane's halt record: the
  session resumed. A send that raises must **not** clear it (the delivery is uncertain).

**The queue path — `overseer/scheduler.py:tick_queue`.**

- The `stopped` phase branch (`:233-235`) sets `entry['queue_reason']` to the client stop reason
  without calling `consider`; that reason must reach the halt record.
- The `model_blocked` branch (`:236-275`) sets `model decision pending: …`, `routed to …` or the
  exhausted-credit status; those must reach the halt record.
- The capacity retry limit (`:283-285`) sets `capacity retry limit reached; manual intervention
  needed`; that must reach the halt record.
- The reason from `policy.consider` (`:298`) can be an escalation hold reason; that must reach the
  halt record.
- A **successful** `backend.send(s, outgoing)` (`:362`) clears the pane's halt record. A failed or
  uncertain send must not clear it.

The simplest complete implementation for the queue path is **one note pass over the observed
panes** after the per-pane loop and before `save(path, state)` (`:312`), because every branch that
sets a halting `queue_reason` is then covered by construction:

```python
for key, snapshot in snapshots.items():
    entry = state.get(key)
    if isinstance(entry, dict):
        note(entry, entry.get('queue_reason'), snapshot.text, snapshot.pane, now)
```

An explicit `note(...)` call at each of the four sites listed above is equally acceptable, as long
as every halting reason reaches the record and no transient reason ever does. The `stopped` branch
in particular must be covered. Keep the whole `overseer/scheduler.py` edit within 15 changed
lines including the import.

### 4.6 The status view

`python3 -m overseer status` (`overseer/__main__.py:338-366`) gains a dedicated section built from
the monitor's state file, printed **after** the existing queue, inventory and model-decision
output:

```text
HALTED / PAUSED SESSIONS:
  %0 session=my-project HALTED
    Reason: client requested no further automatic continuation
    Resume: the client asked to stop; answer it in the pane to resume
```

- The section header contains the word `HALTED` **and** the word `PAUSED`.
- Every halted pane is listed, **including panes whose tmux session has closed** — the section is
  read from the state file, not from the live tmux inventory.
- Each pane's line carries the pane id and its kind token (`HALTED` or `PAUSED`), and the exact
  reason on a line of its own in the form `Reason: <exact reason>`.
- The resume action is printed on a `Resume: <action>` line.
- The section is printed only when at least one halted pane exists.
- The state file's **top-level** keys (`_queue`, `_model_decisions`, `_routes`, `_stale_notices`) are
  not pane entries and must never appear in the section.
- The state file is read tolerantly: a missing or malformed state file must not break `status`
  (the house pattern is `decisions()` at `overseer/__main__.py:66-73`, which catches `OSError`
  and `ValueError`).
- The rendering logic lives in `overseer/halt.py`; the `status` branch only reads the state and
  prints the lines it returns (at most 4 changed lines there).

### 4.7 What must not change

Nothing about **when** the monitor sends changes. `overseer/policy.py` is not modified at all: its
`STOP_REASON`, its `classify`, its `Policy.consider` and its send gate keep their current
behaviour. A stopped, held or paused pane still receives no routine continuation, no report prompt,
no writer handoff, no capacity retry and no routed resume — exactly as today. The new work only
records, announces and renders.

## 5. The required tests

Red-green discipline: write the tests first, record the `sha256sum` of every test file you touch,
then implement. During the implementation phase `tests/` is **read-only** and the digests must
still match. Every test name below is mandatory and must appear verbatim.

### 5.1 `tests/test_halt.py` (new file — the new module's own unit tests)

**`test_a_client_stop_records_a_halted_entry_with_the_exact_reason`**
- Call `note(entry, STOP_REASON, text, "%0", 100.0)` on a fresh entry.
- Assert `entry["halt"]["reason"] == "client requested no further automatic continuation"`,
  `entry["halt"]["kind"] == "HALTED"`, `entry["halt"]["pane"] == "%0"`,
  `entry["halt"]["at"] == 100.0`, and `entry["halt"]["session"]` is a non-empty string.
- Assert the notice: with `self.assertLogs("overseer", level="INFO")`, exactly one logged line
  contains `paused automatic turns: client requested no further automatic continuation`, and that
  line contains `[OVERSEER] Session `.

**`test_a_needs_input_turn_records_the_marker_itself`**
- A screen whose **current turn** carries `OVERSEER_NEEDS_INPUT` → `entry["halt"]["reason"] ==
  "OVERSEER_NEEDS_INPUT"`.
- The same marker in an **earlier** turn (above a submitted prompt line, e.g. a `› prompt` line)
  → the recorded reason is `client requested no further automatic continuation`.

**`test_the_notice_is_logged_once_and_not_repeated`**
- Two `note` calls with the same reason → the second returns `None`, the record's `at` is
  unchanged, and the captured logs contain exactly one `paused automatic turns` line.
- A third `note` call with a **different** halting reason → a second notice is logged and the
  record's reason changes.

**`test_a_transient_reason_neither_records_nor_clears_a_halt`**
- On a fresh entry, `note(entry, "waiting for idle threshold", ...)` (and `cooldown`) → the entry
  has no `"halt"` key at all.
- On an entry that already has a halt record, `note(entry, "cooldown", ...)` → the existing record
  is unchanged (same reason, same `at`, same kind).

**`test_a_successful_send_clears_the_halt_record`**
- `note(...)` then `clear(entry)` → `"halt" not in entry`; `clear` on an entry with no halt is a
  no-op.

**`test_the_halted_section_lists_a_pane_whose_session_is_gone`**
- Build a state dict with one pane entry carrying a halt record and a `_queue` key.
- `render(state)` returns lines whose header contains `HALTED` and `PAUSED`; one line contains
  `Reason: client requested no further automatic continuation`; the pane id appears; the `_queue`
  key does not appear in the output.

**`test_the_status_command_shows_the_halted_section`**
- Write a state file whose only pane entry carries a halt record with the reason
  `client requested no further automatic continuation` (the pane's tmux session does not exist).
- Drive the command with the house pattern of `tests/test_model_choice.py:193`:
  `patch.object(sys, 'argv', ['overseer', 'status', '--state', str(path)])`,
  `patch('sys.stdout', buffer)`, `main()`.
- Assert the captured stdout contains a line with `HALTED`, contains
  `Reason: client requested no further automatic continuation`, and contains the pane id.

### 5.2 `tests/test_monitor.py` (the plain path)

**`test_a_stopped_pane_records_a_halt_and_is_not_sent_to`**
- Drive `overseer.__main__.tick` with a `Snapshot("%0", "codex", "123", text, "›", "0", "0")`
  whose text carries a client stop (`OVERSEER_DONE` on its own line), using the pattern of
  `tests/test_monitor.py:43-57`.
- Assert `state["%0:123"]["halt"]["reason"] == "client requested no further automatic
  continuation"` and `entry["halt"]["kind"] == "HALTED"`.
- **Guardrail:** `backend.send.assert_not_called()` — a stopped pane still receives no automated
  reply.
- Assert the notice was logged (one `paused automatic turns` line in `assertLogs("overseer", …)`).

**`test_a_needs_input_pane_records_the_marker_reason`**
- The same drive with a screen carrying `OVERSEER_NEEDS_INPUT` →
  `state["%0:123"]["halt"]["reason"] == "OVERSEER_NEEDS_INPUT"`, and `backend.send` was not
  called.

**`test_the_halt_notice_is_not_repeated_on_the_next_poll`**
- Two ticks with the same stopped screen → the captured logs contain exactly one
  `paused automatic turns` line, and the record's `at` is the first tick's timestamp.
- A third tick with the same screen still logs nothing new.

### 5.3 `tests/test_scheduler.py` (the queue path)

**`test_the_queue_path_records_a_halt_for_a_stopped_pane`**
- Use the existing setup (`tests/test_scheduler.py:19-37`, `serial_queue: True`), change the pane's
  text to a stopped screen and run a tick.
- Assert `state["%0:0"]["halt"]["reason"]` is `client requested no further automatic continuation`
  (or `OVERSEER_NEEDS_INPUT` for a needs-input screen — assert the marker case separately in the
  same test if you prefer) and that the pane was not sent to.

## 6. Mutations that must fail

Break each mutation on purpose, watch the named test fail, then revert it. Record the real result
in `WORK_LOG.md`.

| Mutation | Must be caught by |
|---|---|
| the notice logged on every poll | `test_the_halt_notice_is_not_repeated_on_the_next_poll` |
| a transient reason clearing the halt record | `test_a_transient_reason_neither_records_nor_clears_a_halt` |
| the `OVERSEER_NEEDS_INPUT` marker not distinguished from the plain client stop | `test_a_needs_input_turn_records_the_marker_itself` |
| the halted section dropped from the status view | `test_the_status_command_shows_the_halted_section` |
| the halt record not cleared after a successful send | `test_a_successful_send_clears_the_halt_record` |

## 7. Verification (execute, do not assume)

```sh
python3 scripts/check </dev/null
python3 scripts/check-doc-references
python3 scripts/check-doc-references docs/AUTONOMY_BLUEPRINT.md
python3 scripts/check-doc-references README.md
```

- `python3 scripts/check` runs the whole suite with an isolated `TMUX_TMPDIR`. It must end with
  `OK` and no failures or errors. The baseline before your change is **`Ran 470 tests ... OK`**,
  and this increment adds 11 named tests, so the finished suite must report **at least 480 tests**.
- `scripts/check-doc-references` must exit 0 for all four documents: every `path:line` citation
  must resolve to an existing file and an in-range line.
- **The edits shift line numbers, so every citation into a changed file must be re-mapped by
  content, not by arithmetic.** These citations all move (the imports shift every line below
  them):
  - `docs/HARNESS_FRAMEWORK.md`: 11 `overseer/__main__.py:*` references (10 distinct lines,
    `overseer/__main__.py:20` twice) and 6 `overseer/scheduler.py:*` references.
  - `docs/AUTONOMY_BLUEPRINT.md`: 8 `overseer/__main__.py:*` references (`:53`, `:57`, `:212`,
    `:242`, `:250`, `:262`, `:383` twice) and 3 `overseer/scheduler.py:*` references (`:148`,
    `:174`, `:283`).
  - `README.md` carries no `path:line` citations today; keep it that way.
- Every **new** citation — into `overseer/halt.py` and into the changed call sites — must name the
  line it claims: open the file, look at that line, and confirm it is the thing the citation says.
  A citation that resolves to the right file but the wrong line is a failure.
- Red-green: record the `sha256sum` of `tests/test_halt.py`, `tests/test_monitor.py` and
  `tests/test_scheduler.py` **before** the implementation and confirm the digests are **unchanged
  after** it.
- Phase 0 re-reads the ground truth in §2; Phase 1 is the tests; Phase 2 is the implementation with
  `tests/` read-only; Phase 3 is the mutation table; Phase 4 is the docs; Phase 5 is this
  verification and one commit.

## 8. Documentation and bookkeeping

- **`docs/AUTONOMY_BLUEPRINT.md`** — add a new section
  `### Increment 11: explicit halted status for intentional monitor halts (PERMISSIONS, …) — LANDED`
  after the increment 10 section (`:796-849`) and before `## 4. Honest limits` (`:850`), in the house
  style of the landed increments: a short quoted note with what landed, the **real** line counts
  per file, the **real** test counts (before and after), the **real** mutation results, and the
  honest limits. Add item `11. **PERMISSIONS.** Explicit halted status: intentional halts are
  recorded, announced and rendered.` to the ordered list at `:215-230`. Add the honest limits to
  §4 (`850-889`): the section reads the monitor's state file and does not prove the session is
  stuck; a closed tmux session stays listed until a successful send clears the record; the notice
  is informational and changes no send decision; a pane whose process was replaced is a new
  `<pane>:<pid>` entry and therefore a new record.
- **`docs/HARNESS_FRAMEWORK.md`** — update the **PERMISSIONS row (`:35`)** with the halt record, the
  notice and the status section, with citations into `overseer/halt.py` and into the changed call
  sites. Add a bullet under **"What this framework does not claim"** (`:87-168`) naming the honest
  limits: the section is read from the monitor's state file, so it does not prove that a session is
  stuck or that the work is progressing; a closed tmux session stays listed from the state until a
  successful send clears the record; the notice is informational and changes no send decision; the
  record is a separate store from the factory's sqlite ledger, and neither sees the other.
- **`README.md`** — add a short section (after "The escalation hold", which ends at `:486`, and
  before "## Model decisions" at `:488`) titled `## Halted sessions`, that shows the notice line and
  the `status` section, and states the limits: the section lists what the monitor recorded, a
  closed session stays listed until it is sent to again, and a halt never changes what the monitor
  sends.
- **`WORK_LOG.md`** — append an honest entry under the current date: what landed, the real line
  counts per file (and the fact that `overseer/__main__.py` and `overseer/scheduler.py` were
  already over the 300-line flag and took a call-site edit of at most 15 lines each), the real
  test counts (470 before, the new count after), the real mutation results (which mutation broke
  which named test), the citation remap count, the CLI smoke output of the new status section, and
  the honest limits listed above. Record that the prompt was written by the dedicated
  prompt-writing agent and that this agent executed it.
- **Commit** — stage files explicitly, one commit, house-style message, e.g.
  `Record and announce the monitor's intentional halts`. Stage only these paths:
  `MONITOR_HALT_NOTICE_NEXT_PROMPT.md`, `overseer/halt.py`, `overseer/__main__.py`,
  `overseer/scheduler.py`, `tests/test_halt.py`, `tests/test_monitor.py`,
  `tests/test_scheduler.py`, `docs/AUTONOMY_BLUEPRINT.md`, `docs/HARNESS_FRAMEWORK.md`,
  `README.md`, `WORK_LOG.md`.

## 9. Constraints

- **Stay inside increment 11.** Do not begin increment 12 or any other objective, and do not add
  features the objective does not name.
- **Do not change what the monitor sends.** `overseer/policy.py` is not modified. A stopped, held
  or paused pane must still receive no automated reply on any path.
- **Do not modify** `overseer/factory.py`, `overseer/strikes.py`, or anything in the sqlite ledger.
  The monitor's halt record and the factory's lineage freeze are separate stores.
- Do not weaken, skip, disable or delete any existing test. The 470 existing tests must all still
  pass.
- No placeholder stubs, no `TODO`, no dead code: production-ready code with complete logic.
- **The working tree has an unrelated modified `config.json`** — an operator's local operational
  change (the monitor's `target_paths`/`targets` now name
  `/home/kali/Programming/Projects/clubwpt-ocr`). **Leave it alone and never stage it**: the
  commit must not contain `config.json`. Also do not stage the untracked scratch files
  (`DESCRIPTION.txt`, `ESCALATION_ROUTE_NEXT_PROMPT.md`,
  `future_ideas_and_architecture_roadmap.md`) and do not delete them.
- The verification must actually be executed. Do not report a result you did not observe.

## 10. Done when

1. `overseer/halt.py` exists, is under 300 lines (target ≤ 200), and owns the vocabulary, the
   record, the notice and the rendering.
2. `overseer/__main__.py` and `overseer/scheduler.py` each changed by at most 15 lines; every
   other module is byte-identical to its committed state, `overseer/policy.py` included.
3. The 11 named tests exist in the three specified files and pass.
4. `python3 scripts/check` ends with `OK`, at least 480 tests, no failures and no errors.
5. `python3 scripts/check-doc-references` exits 0 for `docs/HARNESS_FRAMEWORK.md`,
   `docs/AUTONOMY_BLUEPRINT.md` and `README.md`, with every shifted citation re-mapped by content
   and every new citation verified against the line it names.
6. Each of the five mutations was confirmed to fail the named test and was reverted.
7. `python3 -m overseer status` prints a `HALTED` / `PAUSED` section with
   `Reason: <exact reason>` for a halted pane, including one whose tmux session is gone, and the
   monitor logged `[OVERSEER] Session <session_name> paused automatic turns: <reason>` exactly once
   per transition.
8. A stopped or held pane still receives no automated reply (proved by an assertion, not by
   inspection).
9. `docs/AUTONOMY_BLUEPRINT.md`, `docs/HARNESS_FRAMEWORK.md`, `README.md` and `WORK_LOG.md` carry
   the honest update, and the work is committed in one clean commit **without `config.json`**.

## 11. Stopping condition

Stop when increment 11 is implemented, verified, documented and committed, and the commit exists.
Then report: the line counts per file, the test counts before and after, which mutation failed
which named test, the citation remap count, and the honest limits. Do not begin increment 12 or any
other objective, and do not add work beyond this increment.

Finish with the handoff block required by `AGENTS.md`:

```yaml
STATUS: [SUCCESS | STUCK_NEEDS_ESCALATION]
TESTS_PASSED: [TRUE | FALSE]
FILES_MODIFIED: [<list of files>]
NEXT_AGENT_INSTRUCTION: "<clear self-contained prompt for next iteration>"
```

and, as the operator asked, an `OVERSEER_REPORT` line summarizing the changes and the test results
(a single visible line starting `OVERSEER_REPORT` followed by one JSON object with the keys
`status`, `objective`, `remaining`, `done` and `evidence`).
