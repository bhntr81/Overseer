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

| Date | Prompt | Project | Target | Class | Writer | Cold read | Achieved | Corrections | Waste | Cost | Cause | Lesson |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
