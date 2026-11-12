# Outcomes and lessons

One row per Task or Run prompt. The writer opens the row when the prompt is
delivered, with the outcome fields empty. The next session that writes a prompt
for the same project fills them from that project's report and handoff file.
Briefs get no row. See `GUIDE.md`, "Delivery and after".

How to fill a row:

- **Achieved:** yes, partly, no, or not seen, judged against the prompt's own
  "done" section.
- **Corrections:** how many times the owner had to redirect the work, counted from
  addenda and the handoff file; "unknown" if not recorded.
- **Waste:** one line on work that was repeated or not needed, or "none seen".
- **Cost:** wall time, and tokens only if the runtime reported them; otherwise
  "unavailable". Never estimated.
- **Cause:** prompt, agent, the task itself, or unknown. Only for a row that is
  not a clean yes.
- **Lesson:** when the cause is the prompt, the one sentence that would have
  prevented the problem. A lesson becomes a rule in `GUIDE.md` after it appears
  in two rows, or once at a cost above half a day.

If three prompts in a row get no outcome, the log is not working: tell the owner.

This table is published. A row about a private project names it only in general
terms and gives no path into the unpublished archive. In the Prompt column, a
file name is a prompt published in this repository.

## Rule review

The provisional rules in `GUIDE.md` (rules 3 and 5, and the size numbers of
rule 2) are reviewed when this table has ten rows with outcomes. On 2026-11-12 it
has three, so no review has been done and the rules stand as written. One lesson
is recorded, in one row, at a cost well under half a day, so it has not become a
rule. Rows are added only for prompts that were really written and run.

## Rows

| Date | Prompt | Project | Target | Class | Writer | Cold read | Achieved | Corrections | Waste | Cost | Cause | Lesson |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-11 | not published (private project) | a private project | Coding agent with a shell | Task, 152 lines, written before the size guide | The model, in the session the owner asked directly | none | yes, per the executor's report and handoff (all three parts done, the project's check passed, stopped where told); not re-run by the writer | unknown | none seen | unavailable | | |
| 2026-11-11 | `WINDOWS_SUPPORT_NEXT_PROMPT.md` | Overseer | Coding agent with a shell (the primary agent) | Task, 61 lines (long lines, about 1,500 words) | A subagent, briefed by the primary agent | none | yes, per the executor's report and CI run 43170875858 (both increments on `main`, `19e7bbe` and `3c21beb`, ubuntu and windows-latest green); not re-run by the writer | 0 redirections; the owner sent one "keep going until both are on main and ci is green" | four Windows CI rounds, the first with 51 failures, as the prompt predicted; the copy script of increment 2 was removed the same day when the project moved into `promptwriting/` | wall time not recorded; tokens unavailable | | |
| 2026-11-12 | `WINDOWS_CLIENT_LAUNCH_NEXT_PROMPT.md` | Overseer | Coding agent with a shell (the primary agent) | Task, 100 lines | Supplied by the owner as pasted text; its author is not recorded | none | yes, with one done check not met as written. Commit `e07a224` on `main`; CI run 43176353770 green on both jobs (ubuntu 675 run, 3 skipped; windows-latest 667 run, 16 skipped, within the limit of 18; the new tests ran on Windows); the three premises were confirmed on CI and `.cmd` clients are refused, with the reason given (`WORK_LOG.md`, 2026-11-12). Not met: `git log 3c21beb..origin/main` was to show one commit and shows two, because `main` had moved to `da72c72` before the work began. Checked from the CI records and the work log on 2026-11-12; not re-run by the writer | unknown | none seen; three pull-request CI runs (one red by design, two green), under the limit of five | wall time not recorded; tokens unavailable | prompt, for the unmet check only: its starting commit was one commit out of date when the work began | Recheck the starting commit when the prompt is delivered, and count a done check from the commit the work really starts at. |
