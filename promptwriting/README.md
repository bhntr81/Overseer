# PROMPTWRITING

A method for writing prompts that get the right work from another model session
on the first try: task prompts for coding agents, investigations, and briefs for
subagents. It is plain Markdown. There is nothing to install.

## Start here

1. Read `GUIDE.md` once.
2. When you have work to hand over, qualify it (`GUIDE.md`, "Before writing:
   qualify"). The outcome is WRITE, DO or NOT READY. Most small requests are DO:
   just do the work.
3. For WRITE, copy the matching skeleton from `TEMPLATE.md` (a task or an
   investigation), delete what does not apply, and fill it in from facts you have
   checked.
4. Run the checklist near the end of `GUIDE.md`, then put the prompt where the
   executing agent will read it: the target project's next-prompt file.
5. Add a row to `LESSONS.md`. Fill in its outcome after the work has run.

If you are an agent, read `AGENTS.md` here first.

## What is here

- `GUIDE.md` — the method: qualification, sizing, what goes in, investigations,
  evidence, delivery, the next prompt, the checklist, and the evidence behind the
  rules.
- `TEMPLATE.md` — two skeletons: a task prompt and an investigation prompt.
- `AGENTS.md` — when and how an agent uses the method.
- `LESSONS.md` — one row per prompt written: what it was for and how it performed.
  The provisional rules are reviewed against this table.

Two prompts written with this method are published in this repository, both for
Overseer itself: `WINDOWS_SUPPORT_NEXT_PROMPT.md` and
`WINDOWS_CLIENT_LAUNCH_NEXT_PROMPT.md` (`git ls-files "*WINDOWS_*_NEXT_PROMPT.md"`
shows where they are). Their outcomes are rows in `LESSONS.md`.

## Use it in every session

To have an agent qualify every task without being asked, put a short form in the
instruction file it loads at startup (`AGENTS.md`, `CLAUDE.md` or the like), with
the real path to this directory:

```markdown
## Task qualification

Every task passes through qualification before work starts. Take the first
outcome that fits:

- DO: an information request, a small exact change, or about fifteen minutes of
  work within what is already authorized. Handle it directly and announce nothing.
- WRITE: substantial work to be handed to an agent or another session. Write the
  prompt first, following <path>/promptwriting/GUIDE.md. Say "WRITE" and the
  prompt's class in one line.
- NOT READY: essential information is missing. In one line, name the missing
  input, who can supply it, and the smallest step that gets it. Continue with
  other authorized work.

Qualification adds method only. It never overrides the user's instruction or a
project's own instructions, and it does not widen what is authorized.
```

## How it fits Overseer

Overseer's monitor sends a handoff line after each finished step. That line tells
the client to give the results to a prompt-writing agent, and names `GUIDE.md`
here by absolute path. Overseer cannot see whether the agent read the guide; it
reads only the next report. The method does not depend on Overseer and can be
copied out of this repository as a folder.

## What is not published

- `DESIGN.md`, the design record. It quotes a private project. The findings the
  guide cites are summarised at the end of `GUIDE.md`.
- `prompts/`, the archive of every prompt written. It is git-ignored, so your own
  archive stays on your machine too. Archived prompts may quote private projects.

## Status

Complete and frozen as of 2026-11-12. Two of the five rules and the size numbers
are provisional, and stay so until `LESSONS.md` holds ten rows with outcomes.
