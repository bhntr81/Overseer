# PROMPTWRITING — agent entry point

This project exists to write the best and most efficient prompts: prompts that get
the right work from another model session on the first try, in the fewest words that
still carry everything the reader needs.

## When to use it

Use it whenever you are about to hand work to another agent or session: a task
prompt for a coding agent, an investigation, a brief for a subagent, the next
prompt after a finished step. Do not use it for work you can simply do: an answer
you can give now, a small exact change, about fifteen minutes of work. `GUIDE.md`
calls that outcome DO, and nothing is written for it.

Order of authority, highest first: the owner's current instruction; a shared
workflow file, if your setup has one; the target project's own instruction file;
`GUIDE.md` here. This project adds method only. It does not change who writes
prompts, where they go, or what is authorized.

## How to use it

When asked to write a prompt, here or for any other project:

1. Read `GUIDE.md` and follow it.
2. Qualify first: WRITE, DO or NOT READY. Trivial requests and Briefs resolve to
   DO at once and are not announced. Tell the owner a WRITE or NOT READY outcome
   in one line.
3. Gather the facts. Read the target project's instruction file and handoff file,
   and check the paths, commands and numbers the prompt will cite. A prompt with a
   wrong path costs more than a long one. Fill any open `LESSONS.md` rows for that
   project while you are there.
4. Start from `TEMPLATE.md`, delete what does not apply, and keep to the size
   guide for the prompt's class.
5. Run the checklist near the end of `GUIDE.md`. A Run prompt also gets one cold
   read.
6. Deliver into the target project's existing next-prompt file. Save a copy in
   `prompts/` as `YYYY-MM-DD_project_topic.md` (git-ignored here; it stays on your
   machine) and open a row in `LESSONS.md`.

The method is frozen as of 2026-11-12. Fix a real defect when you find one. Do not
add rules, templates or structure without the evidence `LESSONS.md` asks for.
