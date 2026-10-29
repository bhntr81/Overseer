# Next prompt: Overseer decides convention-settled questions itself

> **Superseded 2026-10-29** by the stop agent (`overseer/stopgate.py`, README
> "The stop agent"), at John's request: a model judges each stop against fixed
> criteria instead of the rules-only plan below. Still open from this plan:
> (A) asking workers to name a `blocker` in `needs_input` reports (the gate
> already honours one), and (D) listing verdicts in `overseer status`.

Written 2026-10-29 by Claude (Opus 5.5, Claude Code) on Kali, from John's request:
"how we can stop this behaviour of stopping and asking me for decisions when
these decisions should be made by overseer itself".

## What happened (the evidence)

On 2026-10-29 a clubwpt-ocr worker under Overseer (pane `%2`, session
`overseer-clubwpt-ocr-1029`) was told to stop and ask John: "should the
tracker price a call at the amount it matched?" Poker trackers have answered
that since the 2000s (PokerTracker, Hold'em Manager, Hand2Note: a call is the
amount to match, capped at the caller's stack). John: "all it has to ask
itself is how do poker trackers normally behave; we are not inventing a new
kind of software." The decision is now D21/D22 in
`/home/kali/Programming/Projects/CWPTGToolkit/BLUEPRINT.md` §8.1.

## Why Overseer cannot prevent it today (verified in code, commit 2d1e55f)

1. `overseer/policy.py` `_report_state` (line ~139): any report with
   `status` `needs_input` returns `"stop"`, so the pane halts whatever the
   reason. Overseer cannot tell "I need a password" from "should calls be
   priced?". There is no step where Overseer resolves a question itself.
2. `_REPORT_TAIL` (policy.py ~66) and `_compose_handoff` (~242) tell the worker
   when to report `needs_input` but never to settle product questions by
   convention first. Every composed prompt carries that tail, so the gap is in
   every prompt Overseer sends.
3. The report schema has no field saying *why* input is needed, so no policy
   can be applied to the reason.
4. Done already, 2026-10-29: a "Decide by established convention" section in
   `/home/kali/Programming/Projects/AGENTS.md`, which the `reply` tells every
   worker to read. Adding the sentence to `config.json`'s `reply` itself was
   tried and REVERTED: the reply was 943 characters, the addition took it past
   the 1000-character cap, and every monitor cycle failed from 02:19:09 to
   ~02:21:45 ("reply must be one nonempty line, at most 1000 characters").
   Lesson for (C): measure every composed prompt against `MAX_PROMPT` in a
   test. `reply` is also only used before a report exists, so (1)-(3) stand.

## Required behaviour

A. **Report schema.** `needs_input` must carry `blocker`, one of:
   `money`, `account_or_credentials`, `site_terms`, `safety_or_authorization`,
   `delete_data`, `conventions_conflict`, `external_action` (a person must do
   something physical or interactive, e.g. log in, plug in, play a hand), and
   `question` (one line). Document it in `_REPORT_TAIL` and README "Try it".

B. **Overseer decides once before stopping.** In `_report_state`/scheduler:
   - `needs_input` with a listed `blocker` → `"stop"`, as today.
   - `needs_input` with no `blocker`, an unknown one, or `product_decision` →
     do not stop. Compose a **convention prompt**: "You asked: <question>.
     Decide it the way established software of this kind behaves (name the
     products and their behaviour), record the decision with that citation in
     the project's decision log, then continue the objective. Report
     needs_input again only with a blocker from <list>." Keep it within
     `MAX_PROMPT` and `_sendable`.
   - At most one convention prompt per question (key: fingerprint of
     `question`, kept in the pane's state entry). A second `needs_input` on the
     same question stops, so there is no loop. It still counts against
     `max_per_day`/cooldown like any send.
   - Log `"%s decided by convention: %s"` so `journalctl` shows each one.

C. **Every composed prompt carries the rule.** Add one sentence to
   `_REPORT_TAIL`: settle product-behaviour questions by established
   convention, record them, and continue; `needs_input` needs a `blocker`.

D. **`overseer status`** lists convention decisions sent in the last day
   per pane (question and time), so John can audit them without being asked.

## Acceptance checks (run them; show the output)

- New tests in `tests/test_policy.py`:
  1. `needs_input` + `blocker: money` → stop.
  2. `needs_input` with no blocker → a convention prompt containing the
     question, under `MAX_PROMPT`, passing `_sendable`.
  3. The same question a second time → stop.
  4. `_REPORT_TAIL` names the blocker list.
- `python3 -m unittest discover -s tests -v` passes in full (no new failures).
- Dry run: set `dry_run: true`, put a fake pane screen with a blockerless
  `needs_input` report through the scheduler test helpers, and show the
  "would send" log line. Restore `dry_run: false`.

## Constraints

- Work from commit 2d1e55f plus the working tree. Do not overwrite or revert
  the existing uncommitted `overseer/__main__.py`, `overseer/local.py`,
  `overseer/terminal.py`, `WORK_LOG.md` changes; they belong to other work.
- Do not let Overseer answer the exempt categories. Money, accounts, site terms,
  the read-only/no-automation poker rules, and deleting data always stop.
- Overseer stays a rule engine: it does not call a model to make the decision.
  The worker decides, and Overseer only refuses to let a convention-settled
  question halt the loop.
- File the increment against one pillar row in `docs/HARNESS_FRAMEWORK.md`, and
  add a WORK_LOG.md entry.

## Stopping condition

Tests pass and the dry run shows a convention prompt for a blockerless
`needs_input` and a stop for a `blocker: money` one. Report with
OVERSEER_REPORT.
