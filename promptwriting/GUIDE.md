# How to write a prompt that works

The reader is a capable model with none of your context. It has only the page. It
cannot ask what you meant, and it will act on what is written, including the
mistakes. Write for a skilled colleague who starts today.

## Where this guide fits

This is the method a prompt writer follows. It stands on its own: nothing outside
this directory is needed to use it. It covers the prompt itself: whether to write
one, how big, what goes in, and how it is judged afterwards.

It does not decide who writes the prompt, when, or where it goes. If your setup
has a workflow file that says so, that file stays in charge. (On the author's
machine there are two, outside this repository: a shared `Projects/AGENTS.md` and
a coding playbook.) If you have none, use these defaults: the prompt goes into the
target project's next-prompt file (`NEXT_PROMPT.md` if it has no other), and a
question that established convention settles is decided, not put to the owner.

Order of authority, highest first: the owner's current instruction, a shared
workflow file if there is one, the target project's own instruction file, this
guide. If this guide seems to conflict with one of those, follow the higher one
and say so. "The owner" is whoever the work is for.

## The five rules

| # | Rule | Standing |
|---|---|---|
| 1 | Qualify before writing: WRITE, DO or NOT READY. | Supported (F1, F2, F3) |
| 2 | Size the prompt to its class. | Supported; the numbers are provisional (F1, F10) |
| 3 | An investigation names what would settle it. | Provisional (F2 in part) |
| 4 | Evidence outranks belief; label only material premises. | Supported (F3, F4, F5) |
| 5 | Nothing is included by default except the outcome, the done test and the report shape. Every other block must change what the reader does. | Provisional (F8, F11) |

The F numbers are findings from the prompt history this method was drawn from,
summarised in "Evidence behind the rules" at the end. Provisional rules are
reviewed once `LESSONS.md` has ten rows with outcomes; `LESSONS.md` says where
that count stands. Until then they stay provisional and are not changed.

## Before writing: qualify

Every task passes through qualification. For a trivial request or a Brief that
means one glance: check 2 gives DO at once, with nothing announced and nothing
written. For anything that would become a Task or Run prompt, and for every
investigation, work through the checks; that takes a few minutes and uses the
project's handoff file plus cheap checks. Take the first outcome that fits. A
short form of this section, for an instruction file agents load at startup, is in
`README.md`; this guide is the authority.

1. **Outcome.** Can you say in one sentence what will exist or be decided when the
   work is done, and how the owner would recognise it? If not, and neither the
   project's files nor convention settles it: NOT READY, with one question.
2. **Direct work.** Is it a request for information you can give now? Would
   describing the work mean stating the exact change, edit by edit? Is it about
   fifteen minutes of work within this session's authority? Any yes: DO. If the
   owner's message is itself a complete prompt for the work, it is the written
   prompt: check it against NOT READY, then carry it out.
3. **Repeat.** Has this been attempted? Look in the handoff or next-prompt file and
   the reports it names. If so, state what is new: evidence, method, or a changed
   premise. Nothing new: NOT READY, naming the input that would justify another try.
4. **Premises.** List the few things (five at most) that would change the task if
   false. Check each cheap one now. Accept what convention settles. An unknown that
   only the owner or an outside source can supply: NOT READY for the part that
   depends on it. An unknown the executor can resolve becomes the prompt's first
   step, or a branch in it.
5. **Otherwise WRITE.**

| Outcome | What you return |
|---|---|
| WRITE | The prompt, with its class. |
| DO | The answer, or the work done. DO does not widen what is authorized and does not override project instructions. If you are acting only as the prompt writer, you do not edit implementation files: pass the item to the primary agent in one line. |
| NOT READY | The specific missing input, who can supply it, the smallest step that gets it, and what can go ahead meanwhile. |

Tell the owner a WRITE or NOT READY outcome in one line. DO is not announced.
No file is written for any outcome.

NOT READY is not a way to avoid writing. If part of the task is ready, write that
part. It covers one prompt; other authorized work continues. It is never used for
a question convention settles. If qualifying would itself take real research, that
research is the task: write it as an investigation, or do it.

## Classes and size

| Class | When | Typical length | Process |
|---|---|---|---|
| Brief | Subagent task, chat question, under about 15 minutes of work | Up to about 15 lines | Outcome, done test, what to return. Not archived. |
| Task | One session of work in a project; by default one independently verifiable behavior | About 30 to 80 lines | Qualify, write, deliver, record. |
| Run | Many hours, real money, hard to undo, or unattended | Up to about 150 lines | As Task, plus a budget, stop conditions, what to do when blocked, and a cold read. |

The lengths are provisional guides. They assume lines of about 80 columns: a prompt
in long unwrapped lines is longer than its line count says. Material pasted in because the reader cannot
fetch it does not count. Go past a guide when you can give the reason in one
sentence (several independent parts, an irreversible step, a reader with no file
access). No approval is needed.

Signs of an oversized prompt: it gives exact old and new text; it repeats rules the
reader's instruction file already carries; it narrates how the project got here; it
lists steps where only the result matters.

## What "best" and "efficient" mean here

- **Best**: the reader does the right work, stops at the right place, and reports
  what happened truthfully, without a second round.
- **Efficient**: every sentence changes what the reader does. Efficiency is not
  shortness. Cutting the reason behind a rule saves ten words and costs a wrong
  guess. Cut what the reader would do correctly anyway; keep what they could not
  know.

## What goes in

1. **The goal and what it serves.** Not only the task, but why it exists and what
   the result is for. A reader who knows the purpose makes good calls on the cases
   you did not list.
2. **The state of things.** What is true now, with evidence the reader can check:
   file paths, commands, numbers, dates. Mark what you measured and what you
   estimated.
3. **What is already settled.** Things ruled out, decisions made, work done. This
   stops the reader re-doing it, which is the most common waste in a handoff.
4. **What makes it hard.** If there is an obvious approach that is wrong, name it
   and say why. Spend words here, not on things any competent reader does unasked.
5. **The work, in order, each piece with its reason.** Say what a correct result
   looks like, not every step to reach it. Give steps only where the order or the
   method matters.
6. **Limits, with reasons.** What must not be touched, what needs the owner's yes,
   what counts as too expensive. A limit with a reason is applied with judgment; a
   bare limit is applied either too widely or too narrowly.
7. **What done means.** Checks the reader can run, including the one that shows
   what worked before still works. Without this the reader stops early or never
   stops.
8. **What to send back.** The shape of the report: conclusion first, measured facts
   apart from guesses, what was skipped and why, open decisions as yes/no questions.

Items 1, 7 and 8 are in every prompt. A prompt for project work also always has
the relevant paths, the required behavior, the constraints and a stopping
condition. Items 2, 3 and 4 go in when they exist and
would change what the reader does (rule 5).

## Investigations

Build an investigation prompt from six things.

| Item | How to find it |
|---|---|
| The decision being informed | What will be done differently depending on the answer? If nothing, there is no investigation to run. |
| Competing explanations | Two or more statements that could each be true. Include "the measurement or tool is wrong" and "both are true" where possible. |
| Evidence that separates them | For each pair, the observation that would differ. |
| Evidence on hand | What is already measured, with method and uncertainty. |
| Missing evidence | The gap, and who can supply it: the executor, the owner, an outside source. |
| Stopping condition | One of the three below. |

A stop does not have to be certainty. Any of these is valid: an evidence stop
("when the result is clearly above or below the threshold"), a budget stop ("after
four hours or three experiments, report what has been narrowed and what has not"),
or a missing-input stop ("if this needs something you cannot get, name it and
stop"). When the explanations are not known yet, write a short time-boxed prompt
whose result is the list of explanations and what would separate them.

## Facts, premises and disagreement

- **Label only what is material**: a premise that would change the scope, method
  or conclusion if false. Tag it in the sentence that uses it: "(measured:
  command)", "(reported in X, not rechecked)", "(the owner says)", "(assumed)". Five at
  most, no separate block. Unlabelled statements are ones you checked.
- **A measured result stays on the record until another measurement replaces it.**
  When someone, including the owner, believes otherwise about an empirical result,
  keep both as competing claims: state the measurement with its method and
  uncertainty, state the correction and what it rests on, list what could explain
  the gap (the measurement is wrong, the model behind it is wrong, the reference
  differs, both are true), and ask for the evidence or test that separates them.
  Do not tell the reader which conclusion to reach.
- **This applies to empirical claims only.** What the owner instructs, prefers or
  decides is not a hypothesis. Follow it, unless it conflicts with a
  higher-priority instruction or a safety requirement.
- **Measured is not the same as correct.** A figure that will steer later work and
  rests on one tool gets one check by a second method, or a sanity bound, before
  it is passed on.

## The reader's abilities

Settle four facts about the target. Write for the weaker case when one is unknown.

| Fact | If yes | If no |
|---|---|---|
| Can it read the project's files? | Point to paths | Paste the needed content |
| Can it run commands? | Give checks to run | Ask for output the owner can check by eye |
| Does it load the project's instruction file? | Do not repeat that file | Include the rules that matter |
| Can it ask a question mid-task? | Unknowns may be left as questions | Give a default and a stop rule for each |

State the reader's abilities in the prompt only when the task needs one it may
lack, or the target is unknown. A subagent sees only its brief, so give it the
purpose and the exact shape of what to return. Never make a step depend on one
particular model being available.

## How to write it

- Plain, calm sentences. No capitals for emphasis, no "CRITICAL", no "never ever".
  Loud wording makes a model apply the rule everywhere. If something matters, give
  the reason in one sentence.
- Say what to do, not only what to avoid. "Write to a temporary file, then rename"
  beats "do not corrupt the file".
- Say it once, in the place it applies. A rule repeated three times reads as three
  rules.
- Use the reader's real names for things: exact file paths, exact command lines,
  exact flag names. Check each one exists before you write it.
- Define any label you invented while working. The reader was not there.
- Give numbers with units and where they came from.
- Examples are copied closely. Give one only when the shape matters, give several
  that differ if you give any, and say what they have in common.
- Lists and headings for reference material; full sentences for reasoning. A
  trade-off squeezed into a bullet loses the "because".
- If the prompt branches on something unknown, write both branches and how to tell
  which applies. Also say what to do when neither can be told: usually stop and
  report.
- Tell the reader the truth about the task. If it is a test, a draft, or a one-off,
  say so.

## What to leave out

- Role play openers ("You are a world-class..."). Describe the situation instead.
- Instructions for things the reader does by default (be careful, write clean code).
- History of how you got here, unless a past dead end is one the reader would walk
  into again. Then give the dead end and the evidence in one line.
- Your own doubts as vague hedges. State the doubt once, where it applies, with what
  would settle it.
- Hashes, authorship lines and traceability blocks that nobody will act on.
  Who wrote the prompt is recorded in the project's handoff record, if it keeps
  one, and in the `LESSONS.md` row.

## Delivery and after

1. **Before drafting**, read the target project's instruction file and handoff
   file. The prompt must not contradict the instruction file. Fill any open
   `LESSONS.md` rows for that project from its latest report.
2. **Cold read, Run prompts only (on trial).** Give the finished prompt to a fresh
   reader with no context. Ask three things: what is ambiguous, what context is
   missing, what could go wrong in execution. Fix what it finds and note in the row
   whether it found anything. One pass; it is not a review board. A reader of the
   same model shares your blind spots, so it will miss wrong premises.
3. **Deliver** into the project's existing next-prompt file. Save a copy in
   `prompts/` as `YYYY-MM-DD_project_topic.md` and open a row in `LESSONS.md` with
   the outcome fields empty. In this repository `prompts/` is git-ignored, so the
   archive stays on your machine; `LESSONS.md` is published, so a row about a
   private project names it only in general terms.
4. **Corrections.** One may be appended. At the second, reissue the whole prompt
   as a new file and note in the old row what superseded it.
5. **Outcome.** The next session that writes a prompt for the same project fills
   the row (step 1). Write "not seen", "unknown" or "unavailable" for anything
   that cannot be found. Never estimate.
6. **The next prompt.** Write it from what the last one produced, not from what it
   asked for. Read the report and the handoff file, fill the row, then recheck
   the cheap facts the new prompt rests on: the commit it starts from, the
   baseline check and its counts. A result you did not rerun goes in as
   "(reported in X, not rechecked)". What the report shows done goes under
   settled work. What it skipped or left open becomes the new work, or a question
   for the owner. One bounded step per prompt.

## Checklist before handing over

- [ ] Could a smart stranger act on this page alone?
- [ ] Is the purpose stated, not only the task?
- [ ] Does every path, command and number check out against the real project?
- [ ] Is settled work listed so it is not repeated?
- [ ] Is the hard part named?
- [ ] Does each limit have its reason?
- [ ] Can "done" be tested by running something?
- [ ] Is the report shape given?
- [ ] Is there a stopping condition (for an investigation, one of the three kinds)?
- [ ] Is the length within the guide for its class, or is there a one-sentence reason?
- [ ] Read the Limits section against the rest: is each limit already stated where
      it applies, or already in the reader's instruction file? Keep it once, where
      the reader acts on it. A done check that tests a requirement is not a repeat,
      and a part that will be run on its own carries what it needs.
- [ ] Read it as the reader: which sentence could be taken two ways? Fix that one.
- [ ] Delete each sentence in turn in your head: would the reader act differently
      without it? If not, cut it.

## Evidence behind the rules

The rules were drawn from the prompts and reports of one private project, read
in November 2026. The full record stays with the author because it quotes that
project. These are the findings the rules table cites, without the private detail.

| ID | Finding | How strong |
|---|---|---|
| F1 | Two task prompts ran to 644 and 500 lines. The first led to a commit that changed 62 lines of code; the second dictated exact old and new text. | The sizes are exact. Nothing shows the length caused harm. |
| F2 | Eight reports in four days worked on one question and its cause was still unknown. The one prompt in that chain with a stop criterion returned a verdict. | The count is exact. Why the work repeated is known for two prompts only. |
| F3 | One prompt carried four addenda, because an outside input it rested on changed three times. | Conclusive. |
| F4 | A prompt withdrew a measured finding because the owner believed otherwise. The measurement was later reconfirmed; the owner's belief is still unresolved and may be right. | Conclusive that the measurement held. |
| F5 | A figure produced by a tool with a display bug was repeated in the next prompt and a later report before it was withdrawn. | Conclusive. |
| F8 | A process required a model that was not available, and sessions wrote disclaimers instead of doing the step. | Conclusive, one case. |
| F10 | Three prompts of 36 to 55 lines each stated one outcome, steps and checks, and each has a matching report. | The structure is exact; "one session each" is inferred. |
| F11 | Long prompts were written while advice against them was already in force. One named an earlier long prompt as its template. | The dates and the quote were read. That copying caused the length is inference. |

Not seen in what was read: removed functionality, half-finished code, false
claims of completion. Token cost was never recorded.
