Focus exclusively on the Overseer project in this current workspace
(/home/kali/Programming/Projects/Overseer). Read AGENTS.md first and follow it;
file this increment against the CONTRACT pillar row of docs/HARNESS_FRAMEWORK.md
("monitor report contract `overseer/policy.py:82`").

Increment: read an OVERSEER_REPORT that the worker's terminal broke across lines,
and announce a report that still cannot be read instead of skipping it silently.

## The defect, observed 2026-10-22 on pane %7 (session clubwpt-claude, 157x31)

A Claude Code worker ended its turn with one logical line, about 700 characters:

    OVERSEER_REPORT {"status":"step_done","objective":"Streamed HL8689 hands read on Kali with the pot checked automatically, so review only covers exceptions","remaining":"Add 921-wide board rank templates: crop board cards from remote-results/stream-loop-HL8689-20261022/run chunk frames where the board reads unconfirmed, label each by eye, add them to rank_templates/board; confirm no new wrong cards on the 6 Oct corpus and HL8202 and that the test suite passes; re-read the 6 chunks and report the pot check before and after; commit, push, and update NOW.md","done":"Stream loop ran 6 chunks, 30 hands read, causes measured (d65b059)","evidence":"11 of 30 hands all pots add up; frame 1443 2s/9c unconfirmed with empty slots matched 0.997"}
    OVERSEER_STEP_DONE

Claude Code renders long lines with hard newlines: `tmux capture-pane -p` (and
`-p -J`, tested) returned it as six lines, each indented two spaces, broken at a
space that is dropped, e.g. line 1 ended `...so review only covers` and line 2
began `exceptions","remaining":...`. `overseer/policy.py:_report_state` (line 82)
takes only the text after OVERSEER_REPORT on the one line, `raw_decode` fails, it
returns ("invalid", None), and `next_prompt` (line ~255) returns
(None, "invalid output report"). That reason is not in `overseer/halt.py`
REASONS, so `classify_reason` treats it as transient: nothing is recorded or
announced. The state file showed only `"queue_reason": "no recognized routine
continuation question"`, and the pane sat idle. Short reports (under ~150
characters) work, but then `remaining`, which the next prompt is built from,
is too vague to be useful.

## Phase 1 — tests only (red). Modify nothing outside tests/.

Add tests to tests/test_monitor.py (or a new tests/test_report_wrap.py) that fail
on the current code:
1. Wrapped report: build the screen text by wrapping the report above at 155
   columns at spaces, dropping the space at each break, indenting each line two
   spaces, with OVERSEER_STEP_DONE on its own line after it and a `❯ ` prompt line
   before the answer. `_report_state(current_turn(screen))` must return
   ("handoff", fields) with `remaining` equal to the original text, and
   `next_prompt(screen, fallback)` must return a prompt with reason
   "writer handoff prompt".
2. A long token broken mid-word (no space at the break, e.g. a path split
   across lines): it must still decode; the value may differ only by the
   inserted joining space, and must not raise.
3. Bounded: a line starting `OVERSEER_REPORT {` followed by more than 12 lines
   that never form valid JSON stays ("invalid", None), and the search does not
   read past the next `❯ `/`› ` prompt line or another OVERSEER_REPORT line.
4. Unchanged behaviour: a valid one-line report, a report quoted earlier with
   prose after it (`_done_follows_step_report`), status done/needs_input, and
   OVERSEER_NEEDS_INPUT/OVERSEER_DONE stop rules all keep their current
   results (the existing tests cover most; add what is missing).
5. Announcement: when `next_prompt` gives "invalid output report" for a pane,
   `halt.note` records it once as a PAUSED halt with a resume action telling the
   worker to print the report again on one line, and a second identical poll
   does not announce it twice; a later valid report clears it (`halt.clear`
   after a successful send, as now).
Run `python3 scripts/check`; show the new tests failing for the right reason.

## Phase 2 — implementation (green). Do not modify tests/.

1. overseer/policy.py `_report_state`: when a line starts with OVERSEER_REPORT
   and `{` but does not decode, join it with up to 12 following lines, each
   stripped and joined with a single space, trying `raw_decode` after each; stop
   at a prompt line (`❯ `, `› `, `> `), another OVERSEER_REPORT, or the marker
   lines OVERSEER_STEP_DONE / OVERSEER_DONE / OVERSEER_NEEDS_INPUT. Keep "the
   latest report wins" and the existing rejection of trailing text after the
   JSON. No regex rewriting of the JSON, no eval.
2. overseer/halt.py: add "invalid output report" to REASONS as
   (PAUSED, "print the OVERSEER_REPORT again with its JSON on one line") so
   `note` records and announces it once through the existing path.
3. Keep the change lean (AGENTS.md locality limit); `_REPORT_TAIL` wording may
   add "the JSON may wrap; do not insert line breaks yourself".

## Verify and hand off

- `python -m py_compile overseer/policy.py overseer/halt.py`
- `python3 scripts/check` and `python3 scripts/check-doc-references`: all pass.
- Dry run on real text: save the screen above (wrapped as in Phase 1) to a temp
  file and show `next_prompt` producing the writer handoff prompt.
- Update the CONTRACT row of docs/HARNESS_FRAMEWORK.md (file:line and verdict,
  honestly) and add a WORK_LOG.md entry: who you are, what changed, what was
  measured. Commit clean. Do not restart the running overseer.service; say in
  the handoff that it must be restarted (`systemctl --user restart overseer`)
  for the change to take effect, and leave that to John.
- End with the AGENTS.md handoff block (STATUS, TESTS_PASSED, FILES_MODIFIED,
  NEXT_AGENT_INSTRUCTION).

Out of scope: clearing old halt records when a person types in a pane (separate
increment), any change to the clubwpt-ocr project.
