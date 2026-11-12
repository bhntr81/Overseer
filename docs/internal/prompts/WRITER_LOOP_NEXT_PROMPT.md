# Code the prompt-writer loop into the monitor

Status: **ready to execute**. This prompt was written by the dedicated
prompt-writing agent of the Overseer project. The primary agent executes it;
writing it is not completion. It takes priority over
`CONTEXT_WIDEN_SELECTION_NEXT_PROMPT.md`, which stays pending and runs after
this one.

The user's instruction: *"its not your fault but make sure this gets coded
into the program to do it this way."* "This way" is the standing loop of
`/home/kali/Programming/Projects/AGENTS.md`: after a step is executed, its
results go to the dedicated prompt-writing agent, which writes the next
bounded prompt, which the primary agent executes. **A single prompt's stopping
condition ends that prompt, not the objective.**

Its file and line references describe the repository at the starting commit
below. The review lessons carry forward and are part of the acceptance:

1. **Line citations drift.** Re-derive every citation by hand after the last
   edit, in every pillar row it touches, not copied from here.
2. **A test is evidence only if a plausible wrong implementation fails it.**
   Section 7 names mutations; apply each one at a time, show the suite
   failing, revert.
3. **Words describe what the code does.** No prompt, doc, or log may claim
   that Overseer verifies a separate writer agent ran; it instructs it.

This prompt files exactly one increment against the **CONTEXT** row of the
harness pillar map (`docs/HARNESS_FRAMEWORK.md:32`), the row that already owns
the continuation instruction (`config.json:1`), the restated report contract
(`overseer/policy.py:43`), the report-field splicing (`overseer/policy.py:111`)
and the prompt assembly (`overseer/policy.py:139`): what the next session is
handed. It does not plan work for the CONTRACT, TOOLS, STATE, PERMISSIONS, or
EVIDENCE rows; only their citations are re-derived where lines move.

## Outcome

When a pane finishes one step of a larger objective and reports that a next
step remains, Overseer does not stop. It sends a **writer-handoff prompt**:
give this step's results to the dedicated prompt-writing agent, have it write
the next bounded prompt for the named next step, then execute and verify that
prompt. Every prompt Overseer sends states the loop and the rule that a
prompt's stopping condition ends that prompt, not the objective. A report that
the objective is done, a request for input, and every existing safety stop
still stop. The loop stays bounded by idle, cooldown, the sent and held
fingerprints, and `max_per_day`.

## The observed failure

A pane finished one increment, printed a "Next: <named next increment>"
paragraph, then `OVERSEER_DONE`, and Overseer stopped. Today:

- `classify` (`overseer/policy.py:171`) stops on `STOP`
  (`overseer/policy.py:29`, either marker) before anything else;
- `scheduler.phase` (`overseer/scheduler.py:58`) returns `'stopped'` on the
  same `STOP`;
- `_report_state` (`overseer/policy.py:86`) maps status `done` and
  `needs_input` to `"stop"`, and only `continue` is composed;
- the prompts sent — `config.json` `reply`, `_REPORT_TAIL`
  (`overseer/policy.py:43`), `_compose` (`overseer/policy.py:111`) — never
  mention the writer handoff, so an agent has no status for "this step is
  done, the objective is not".

## Repository and starting commit

- Repository: `/home/kali/Programming/Projects/Overseer` (git root, branch
  `main`).
- Starting commit: `4a133d21f74ea702f83819acf10de1de180832c8`
  ("Attach the recalled memory records to the symbols they name").
- Python 3 standard library only. No new dependency.

## Relevant paths

| Path and line | What it is now |
| --- | --- |
| `overseer/policy.py:12` | `DEFAULT_REPLY` |
| `overseer/policy.py:19` | `BLOCKED`: permission, sensitive-action, and generation words |
| `overseer/policy.py:29` | `STOP`: `OVERSEER_DONE` or `OVERSEER_NEEDS_INPUT` at a line start |
| `overseer/policy.py:42` | `MAX_PROMPT = 1000`; `_REPORT_TAIL` at 43 (344 characters) |
| `overseer/policy.py:60` | `_report_state(text)`: the latest report wins; kinds absent / invalid / stop / empty / ready |
| `overseer/policy.py:111` | `_compose(fields)`: the shrink loop that keeps a prompt within `MAX_PROMPT` |
| `overseer/policy.py:139` | `next_prompt(text, fallback, capacity)`: returns `(prompt, kind)`; kind is a fixed phrase |
| `overseer/policy.py:171` | `classify(text, continue_on_completion, completed)` |
| `overseer/policy.py:191` | `Policy.consider`: idle, sent/held fingerprints, cooldown, daily limit |
| `overseer/scheduler.py:52` | `phase(snapshot)`: `'stopped'` on `STOP` at 58 |
| `overseer/scheduler.py:76` | `outcome(snapshot)`: fingerprints through the last `CAPACITY/COMPLETED/STOP/CONTINUE` match |
| `overseer/scheduler.py:292` | the queue's `consider` then `next_prompt`; dry-run log at 326, send at 344 |
| `overseer/__main__.py:58` | the `reply` validation in config loading |
| `overseer/__main__.py:211` | `tick`: `consider`, `next_prompt` at 235, dry-run log by kind, send |
| `config.json:1` | `reply` (710 characters) |
| `tests/test_policy.py:66` | `ReportPromptTests`; `test_stop_empty_and_invalid_do_not_fall_back` at 86; `test_report_outside_classification_tail_is_still_read` at 134 |
| `tests/test_scheduler.py:19` | `SchedulerTests` (`run_tick`, `change`); `OVERSEER_DONE` screens at 76, 155, 212, 238; `test_done_report_does_not_send` at 230 |
| `tests/test_exclusions.py:31` | the two marker stops on a completed screen |
| `tests/test_monitor.py:70` | `test_report_prompt_is_sent_once`, the `tick` example |
| `README.md:197` | the `reply` and report paragraph (to 212) |
| `README.md:343` | the recognition and stop paragraph (to 356) |
| `docs/HARNESS_FRAMEWORK.md:32` | the CONTEXT row |
| `docs/HARNESS_FRAMEWORK.md:72` | System A's "prompt decision `overseer/policy.py:139`" |
| `docs/HARNESS_FRAMEWORK.md:82` | "What this framework does not claim" |
| `WORK_LOG.md:2336` | the end of the log; the new entry goes after it |

## Required behavior

### 1. The report gains `step_done`

The status set becomes `continue`, `step_done`, `done`, `needs_input`.

- `step_done`: this step's own stopping condition was met, and the objective
  has a named next step. `objective` and `remaining` are required and nonempty
  after whitespace collapse, exactly as for `continue`; `done` and `evidence`
  are optional. `_report_state` returns a new kind `"handoff"` with the fields.
  A `step_done` report with a missing or blank `objective` or `remaining`
  returns `"empty"` — **no handoff is ever sent with an empty remaining**, and
  the reason stays `report has no remaining work`.
- `done` keeps its meaning: the **objective** is finished. A legacy `done`
  report still stops, **even when its `remaining` is nonempty**, with the
  existing reason `output report requested no further continuation`. A report
  that says the objective is done is taken at its word; the program does not
  guess that `remaining` meant a next step. (The existing assertions at
  `tests/test_policy.py:86` and `:134` stay unchanged and hold this.)
- `needs_input` always stops. Nothing overrides it.
- The latest report on the screen still wins, as now.

### 2. The markers

Split `STOP` into `DONE_MARK` (`OVERSEER_DONE`) and `NEEDS_INPUT_MARK`
(`OVERSEER_NEEDS_INPUT`), and add `STEP_DONE_MARK` (`OVERSEER_STEP_DONE`), all
with the existing line-start form. Keep the name `STOP` exported, matching the
two old markers, for compatibility. Note `OVERSEER_STEP_DONE` does not match
the old pattern, because the old pattern requires `DONE` or `NEEDS_INPUT`
right after `OVERSEER_`; a test asserts this.

Add one function, used by both `classify` and `scheduler.phase`, so the two
cannot disagree:

```python
def stop_requested(text, tail_only=True):
    """Return the fixed reason the screen asks Overseer to stop, or None. ..."""
```

Its rule, in order:

1. `OVERSEER_NEEDS_INPUT` present → stop. Always.
2. `OVERSEER_DONE` present → stop, **unless** the latest valid report on the
   screen is `"handoff"` (status `step_done` with nonempty objective and
   remaining). Then the marker ends the step, not the objective, and the
   function returns `None`. The structured report names the next step; the bare
   marker does not, so the more specific statement decides. A `done` report, an
   invalid report, or no report keeps the stop.
3. Otherwise → `None`.

`classify` uses `stop_requested(tail)` where it used `STOP.search(tail)`, and
keeps the order: stop check, then `BLOCKED`, then the new handoff rule, then
completion and the routine question. The new handoff rule: when the latest
report is `"handoff"` and the tail shows `OVERSEER_STEP_DONE` or
`OVERSEER_DONE`, the screen is eligible with the fixed reason
`finished step; writer handoff due`. `OVERSEER_STEP_DONE` without a valid
`step_done` report is neither a stop nor eligibility by itself; the existing
rules decide.

`scheduler.phase` uses `stop_requested(text, tail_only=False)` where it used
`STOP.search(text)`. `outcome` adds `STEP_DONE_MARK` to its patterns so a
handoff screen has an outcome fingerprint.

`BLOCKED` is checked before the handoff rule and still wins: a permission
prompt, generation marker, or sensitive word in the tail blocks a handoff
exactly as it blocks any other prompt. `BLOCKED` itself is unchanged.

### 3. The writer-handoff prompt

`next_prompt` returns, for a `"handoff"` report, a prompt built by a new
`_compose_handoff(fields)` with the kind `writer handoff prompt`. It uses the
same shrink loop as `_compose` and returns `None` (kind `invalid output
report`) when it cannot fit. Its fixed text, in this order:

```text
Automatic continuation. The last step is finished; its stopping condition ended
that prompt, not the objective. Objective: {objective}. Step done: {done}.
Evidence: {evidence}. Give these results to the dedicated prompt-writing agent
and have it write one bounded next prompt for: {remaining}. Then execute that
prompt, verify it, and report. If no separate writer can be used, report
needs_input. {_REPORT_TAIL}
```

(Shown wrapped; it is sent as one line.) The fixed part without fields is 360
characters as drafted; you may tighten the wording, but keep every clause:
the stopping-condition rule, the dedicated prompt-writing agent, "one bounded
next prompt", "execute that prompt, verify it", and the needs_input fallback
when no separate writer can be used. The handoff prompt and every other
prompt Overseer composes must contain no `BLOCKED` match (a prompt that
matched would block its own echo on the screen).

### 4. Every prompt states the loop

`_REPORT_TAIL` becomes, or a tighter wording with the same clauses (443
characters as drafted, no `BLOCKED` match):

```text
When that step is finished, print one visible line starting OVERSEER_REPORT
and a JSON object with status, objective, remaining, done, and evidence. status
is continue, step_done, done, or needs_input. A prompt's stopping condition
ends that prompt, not the objective: if a next step remains, use step_done, put
it in remaining, and end with OVERSEER_STEP_DONE. Use done only when the
objective has no actionable next step; do not invent work.
```

`config.json` `reply` becomes, or a tighter wording with the same clauses
(937 characters as drafted, ≤ `MAX_PROMPT`, no `BLOCKED` match, and it must
still pass the loader's checks at `overseer/__main__.py:58`):

```text
Automatic continuation: read /home/kali/Programming/Projects/AGENTS.md and this
project's instructions. Apply
/home/kali/Programming/Projects/coder_optimization/docs/PLAYBOOK.md. Do the
next authorized step only, and do not invent work. Preserve scope, pauses,
required consent, and draft-only limits. After each executed step, give its
results to the dedicated prompt-writing agent, which writes the next bounded
prompt that you then execute; a prompt's stopping condition ends that prompt,
not the objective. On the visible screen, print one line that starts with
OVERSEER_REPORT followed by a JSON object with keys status, objective,
remaining, done, and evidence. status is continue, step_done, done, or
needs_input. Use step_done with the next step in remaining and end with
OVERSEER_STEP_DONE; use done only when the objective has no actionable next
step, ending with OVERSEER_DONE, or needs_input ending with
OVERSEER_NEEDS_INPUT.
```

Change only the `reply` value of `config.json`; no other key.
`DEFAULT_REPLY` is unchanged (it is the bare fallback when no `reply` is
configured).

With every report field at 5000 characters, both `_compose` and
`_compose_handoff` must still return a prompt of at most 1000 characters that
keeps the stopping-condition rule and at least the first 40 characters of
`remaining`. If the drafted texts do not fit that, tighten the fixed wording,
not the shrink floors.

### 5. What stays exactly as it is

- `needs_input` and `OVERSEER_NEEDS_INPUT` always stop.
- `BLOCKED`, the idle threshold, `sent_fingerprint`, `held_fingerprint`,
  cooldown, and `max_per_day` apply to a handoff exactly as to any prompt; the
  handoff goes through `Policy.consider` in both `tick` and the queue, never
  around it.
- A `done` report stops; a `continue` report is composed as now (its tail now
  carries the loop).
- The capacity retry and the routed-session resume keep sending the
  configured `reply`.
- Terminal text is never executed; report fields are copied as data.
- The dry-run logs in `tick` (`overseer/__main__.py:211`) and the queue
  (`overseer/scheduler.py:326`) name a handoff as `writer handoff prompt`
  instead of folding it into `routine continuation`; that is the only change
  allowed in `__main__.py`.
- `/home/kali/Programming/Projects/AGENTS.md` is **not** edited. Its step 5
  ("When the objective's acceptance criteria are met … end an Overseer response
  with `OVERSEER_DONE`") already speaks of the objective, which agrees with
  `done` here; the step-level marker comes from the prompts Overseer sends.

### 6. Honest limits, stated in code and docs

Overseer instructs the handoff; it cannot see or verify that a separate
prompt-writing agent ran, wrote the prompt, or that the prompt was executed.
It reads only the next report. Say so in the `_compose_handoff` docstring, the
README, and a new bullet under "What this framework does not claim".

### 7. Tests, and the mutations they must kill

New tests only; do not weaken, delete, or rewrite existing tests. Put policy
tests in `tests/test_policy.py`, queue tests in `tests/test_scheduler.py`, a
`tick` test in `tests/test_monitor.py`.

1. **A step_done report yields the handoff.** `next_prompt` returns kind
   `writer handoff prompt`; the prompt contains the remaining text,
   `prompt-writing agent`, `ended that prompt, not the objective`, and
   `step_done`; ≤1000, one line, no control character, `BLOCKED.search` is
   `None`; it does not equal the fallback.
2. **No handoff with empty remaining.** `step_done` with blank, missing, or
   whitespace `remaining`, and with missing `objective`: `(None, 'report has
   no remaining work')`.
3. **needs_input is never overridden.** (a) status `needs_input` with a
   nonempty remaining stops; (b) a `step_done` report followed by
   `OVERSEER_NEEDS_INPUT`: `classify` is `False`, `phase` is `'stopped'`, the
   queue sends nothing to that pane.
4. **A legacy done still stops.** `done` with nonempty remaining: stop, the
   existing reason, also when followed by `OVERSEER_DONE`.
5. **OVERSEER_DONE after a step_done report continues.** `classify` is
   eligible with `finished step; writer handoff due`; `phase` is `'finished'`;
   `OVERSEER_DONE` after a `done` report, an invalid report, or no report still
   stops (the existing screens at `tests/test_scheduler.py:76`, `:155`, `:212`,
   `:238` and `tests/test_exclusions.py:31` keep passing unchanged).
6. **OVERSEER_STEP_DONE.** With a `step_done` report: eligible. Without a
   valid report: not a stop, and not eligible on its own. `STOP` does not match
   `OVERSEER_STEP_DONE`.
7. **BLOCKED still wins.** A `step_done` report with `Permission required:
   approve?` or `esc to interrupt` in the tail: not eligible.
8. **Latest report wins.** An older `step_done` then a newer `done`: stop. An
   older `done` then a newer `step_done`: handoff.
9. **The loop is bounded.** With `Policy(idle_seconds=0, cooldown_seconds=0,
   max_per_day=2)` and a fresh `step_done` screen per tick: two handoffs are
   sent, the third is refused with `daily reply limit`; the same screen is
   never sent twice (`already replied to this screen`); with a nonzero
   cooldown the second handoff waits (`cooldown`).
10. **End to end.** The queue (`tests/test_scheduler.py`) and `tick`
    (`tests/test_monitor.py`) send the handoff text for a `step_done` +
    `OVERSEER_DONE` screen, once.
11. **The texts.** `config.json`'s `reply` loads through the config loader, is
    ≤1000, has no `BLOCKED` match, and contains `prompt-writing agent`,
    `step_done`, `OVERSEER_STEP_DONE`, and `ends that prompt, not the
    objective`; `_REPORT_TAIL` contains `step_done`, `OVERSEER_STEP_DONE`, and
    the stopping-condition rule; a `continue` report's prompt carries the rule.
12. **Long fields.** Every field at 5000 characters: both composers return
    ≤1000 characters with the rule and the first 40 characters of `remaining`.

Mutations — apply one at a time, show the suite failing (name the failing
test), revert:

- M1 `step_done` treated as stop;
- M2 `needs_input` (status or marker) overridden by a `step_done` report;
- M3 a handoff sent with empty `remaining`;
- M4 the handoff path bypasses `Policy.consider` (daily limit, cooldown, or
  sent fingerprint skipped);
- M5 legacy `done` with nonempty `remaining` treated as a handoff;
- M6 `scheduler.phase` still uses the raw `STOP` (a `step_done` +
  `OVERSEER_DONE` screen stays `'stopped'`);
- M7 the handoff rule checked before `BLOCKED`;
- M8 a `step_done` report composed with the `continue` template (no writer
  instruction);
- M9 the handoff taken from an older report when the latest is `done`;
- M10 `_REPORT_TAIL` or `reply` left with the old status list;
- M11 a `step_done` report answered with the fallback `reply`;
- M12 `OVERSEER_DONE` ignored even without a `step_done` report.

### 8. Documentation

Re-derive every `path:line` after the last edit; the reference checker only
proves the line exists.

- `docs/HARNESS_FRAMEWORK.md:32` — the CONTEXT row: add citations for
  `stop_requested`, `_compose_handoff`, the handoff branch of `next_prompt`,
  and the `step_done` branch of `_report_state`; re-derive `config.json:1`,
  `overseer/policy.py:43`, `:111`, `:139`. Add to the verdict: the monitor's
  prompts now carry the writer loop and the rule that a prompt's stopping
  condition ends that prompt, not the objective; a `step_done` report with a
  named next step gets a writer-handoff prompt instead of a stop; `done` and
  `needs_input` still stop; the handoff is instructed and not verified. Keep
  "partial". **Do not change the "Next increment" cell**: the widen increment
  it names is still pending.
- Every other row and passage citing `overseer/policy.py`,
  `overseer/scheduler.py`, or `overseer/__main__.py` (the CONTRACT row's
  `overseer/policy.py:60` and `:42`, PERMISSIONS' `:19`, `:171`, `:191`, TOOLS'
  `overseer/scheduler.py:52`, System A at line 72, the process paragraph's
  `overseer/scheduler.py:215`): re-derive; verdicts unchanged.
- "What this framework does not claim" — add: the monitor instructs a
  writer handoff after a finished step; it cannot verify that a separate
  prompt-writing agent wrote the next prompt or that the prompt was executed.
- `README.md:197`–`212` and `:343`–`356` — the four statuses, the three
  markers, the handoff, what still stops, the bounds, the honest limit.
- `WORK_LOG.md` — a new `###` section after line 2336: the user's instruction
  quoted, the observed failure, the decisions (section 1–5), the commands and
  results, the new test count, the mutation results M1–M12 with the failing
  test of each, that every citation was re-derived, and that the prompt was
  written by the dedicated prompt-writing agent and executed by the primary
  agent.

## Acceptance criteria (observable)

1. `python3 scripts/check` passes: the 250 existing tests unchanged, new tests
   pass (expected at least 262). The new count is reported.
2. `python3 scripts/check-doc-references` reports every reference resolving,
   at least 138.
3. A `step_done` report with a named next step, followed by `OVERSEER_DONE` or
   `OVERSEER_STEP_DONE`, is answered once with a writer-handoff prompt in both
   `tick` and the queue.
4. `needs_input`, `OVERSEER_NEEDS_INPUT`, a `done` report, `BLOCKED` text, a
   held or already-sent screen, cooldown, and the daily limit each prevent the
   handoff.
5. No handoff is composed with an empty `remaining`.
6. `config.json` `reply`, `_REPORT_TAIL`, and every composed prompt are ≤1000
   characters, one line, `BLOCKED`-free, and state the loop and the rule.
7. M1–M12 each fail the suite, recorded in the WORK_LOG.
8. The docs carry the increment against the CONTEXT row only, with the honest
   limit, and every touched citation re-derived after the last edit.
9. `git diff --stat` shows no change to `overseer/factory.py`,
   `overseer/codemap.py`, or `/home/kali/Programming/Projects/AGENTS.md`.

## Constraints

- Python 3 standard library only.
- One primary editor: the primary agent edits. No new objective, no change to
  the factory, the codemap, the model-choice or capacity logic, `BLOCKED`, the
  bounds of `Policy`, or any `config.json` key other than `reply`.
- File this increment against exactly the CONTEXT row.
- Do not invent benchmark results, token counts, costs, or savings.

## Baseline

Reported to the writer by the primary agent at the starting commit (not rerun
by the writer): `python3 scripts/check` — 250 tests OK;
`python3 scripts/check-doc-references` — 138 references resolve. The writer
measured the drafted texts against the current `BLOCKED`: no match; `reply`
937 characters as drafted (current 710), `_REPORT_TAIL` 443 as drafted
(current 344), handoff fixed text 360.

## Verification commands

```text
python3 scripts/check
python3 scripts/check-doc-references
git diff --stat
```

## Allowed work and stopping condition

Allowed: `overseer/policy.py`; `overseer/scheduler.py` (`phase`, `outcome`,
the dry-run log kind, the import block at line 11); `overseer/__main__.py` (the dry-run
log kind only); `config.json` (`reply` only); `tests/test_policy.py`,
`tests/test_scheduler.py`, `tests/test_monitor.py`, `tests/test_exclusions.py`
(new tests only); `docs/HARNESS_FRAMEWORK.md` (the CONTEXT row, the new
does-not-claim bullet, and re-derived citations elsewhere); `README.md`;
`WORK_LOG.md`.

Stop after this one increment: the monitor turns a finished step with a named
next step into a writer-handoff prompt, every stop that must stop still stops,
the loop is bounded, the prompts teach the loop, M1–M12 each fail the suite,
the docs are current with re-derived citations, and the verification commands
pass. Report the diff summary, the command outputs, the new test and reference
counts, the mutation results, and the limits that remain. This stopping
condition ends this prompt, not the user's objective: report `step_done` with
the next step (the pending widen increment) in `remaining`. If the same
failure recurs twice with no new evidence, stop and report it instead of
retrying.
