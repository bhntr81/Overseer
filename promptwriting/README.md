# PROMPTWRITING

A project dedicated to writing the best and most efficient prompts: ones that get
the right work from another model session on the first try.

- `GUIDE.md` — the method: qualification, sizing, what goes in, investigations, evidence, delivery, checklist.
- `TEMPLATE.md` — skeletons for a task prompt and an investigation prompt.
- `prompts/` — every prompt written, `YYYY-MM-DD_project_topic.md`.
- `LESSONS.md` — one row per prompt: what it was for and how it performed.
- `AGENTS.md` — the working rules for an agent writing prompts here.
- `DESIGN.md` — the design, its evidence and the owner's decisions.

The list of prompts written, and how each one performed, is the table in
`LESSONS.md`.

## How this fits the shared workflow

`~/Programming/Projects/AGENTS.md` requires a dedicated prompt-writing role for
project work and says where the prompt goes. `coder_optimization/docs/PLAYBOOK.md`
covers the whole coding loop. This project is the method that role follows for the
prompt itself: whether to write one, how big, what goes in, and how it is judged
afterwards. Those two files take precedence over this one. `DESIGN.md` records why
the method is what it is, with the evidence.

## This copy

This directory is a snapshot written by `scripts/sync-promptwriting` from the
author's canonical project; edit that project, not this copy. Two parts are
kept there and not published here, because they quote other, private projects:
`DESIGN.md` (the design record, including the findings F1 to F11 that
`GUIDE.md` cites) and the `prompts/` archive. `LESSONS.md` is published
without its rows for the same reason.
