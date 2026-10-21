# Overseer

A local Python monitor for explicitly opted-in Codex and Claude terminal sessions.
It checks every 30 seconds. When a watched pane shows a structured output
report, Overseer builds the next one-line prompt from that report and submits
it. When no report is visible, it can send the configured continuation
instruction after a recognized question remains unchanged for three minutes.
No API key or Python dependencies are required. Requires Python 3 and tmux
on Linux.

The integration uses tmux panes, accessible from one QTerminal project hub. It
does not switch desktop focus during monitoring. The six original Codex clients
were migrated live using a locally installed `reptyr -T` bridge; they were not
restarted. Original QTerminal windows retain stale output and are hidden from
the desktop/taskbar while their processes stay alive. Use the project hub.
Migration metadata is recorded in
`~/.local/state/overseer/migration.json`. Bridge targets are checked against their
PID, process start time, foreground process group, and bridge executable before
any input is sent.

## One project window

Open **Overseer Terminals** on the desktop. It focuses the existing project
display; if that display was closed, it attaches a new window to the existing
solver session, or another surviving project if the solver session has ended.
Press **F12** for an alphabetically ordered project menu, then
choose a project with its number or the arrow keys and Enter. **Ctrl-b s** opens
tmux's complete session tree, including sessions added later. **Ctrl-b d** detaches
the display without stopping a project. The status bar shows the current project.

This switches between the original sessions; it neither copies nor restarts
them. Selecting an excluded project does not enroll it or change the FIFO queue.
The F12 menu is configured in `terminal-hub.tmux.conf` and loaded from
`~/.tmux.conf`. Its labels/targets describe the six migrated sessions; update
that file if those sessions are renamed or replaced. New sessions remain
accessible through Ctrl-b s. The launcher requires the existing tmux server.

Five redundant tmux displays were detached. Six legacy donor windows are hidden,
not terminated, because they remain ancestors of the migrated clients. To show
them again, run `scripts/terminal-hub --restore-hidden`. Do not close those legacy
windows while their migrated clients are in use. The current Overseer conversation
and unrelated terminals are left alone. Window IDs and restore information are
recorded in `~/.local/state/overseer/terminal-hub.json`.

## Software factory direction

Overseer is the software factory project. The current design is the
[Version 2 blueprint](docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt), moved verbatim from
Downloads. The [original blueprint](docs/SOFTWARE_FACTORY_BLUEPRINT.md) is retained
for history. [Selected third-party skills](docs/FACTORY_SKILLS.md) support prompt
writing, bounded loops, and skill authoring. [Execution record and commands](docs/FACTORY_EXECUTION.md)
distinguish the implemented local task runner from planned provider automation.
At the start of every attempt the factory reads and validates
`factory/skills-provenance.json`, checks each declared skill's installed files
against the recorded SHA-256 hashes, and writes the result to `skills.json` in
the run evidence. The worker receives `OVERSEER_SKILLS_PATH`,
`OVERSEER_SKILLS_PROVENANCE_SHA256`, `OVERSEER_SKILLS_DECLARED`, and
`OVERSEER_SKILLS_VERIFIED`, and the context manifest carries a `skills` block.
Three layers are recorded: declared by the file, installed with matching bytes,
and supplied to the attempt, which is always false because the factory runs
argument-vector commands and passes no skill to them. Whether a client loaded a
skill is not observed, and nothing records a skill as active. A missing or
malformed provenance file is recorded with its reason and does not block the
attempt.
Each command-mode attempt in a git workspace also leaves a patch receipt in its
run evidence: `diff.patch`, a git-style patch that `git apply` accepts, and
`diff.json`, its stats, per-file statuses, top-level path summary, and digest;
the context manifest carries the same block. The workspace is snapshotted
immediately before the implementation command and again after it returns,
whatever its exit, and only the paths whose state changed between the two are
in the patch, so edits present before the attempt are not attributed to it; a
file the checks change afterwards is listed apart. Git is only read. Secret,
binary, oversized, symlinked, and non-UTF-8 content is withheld with the
reason, the patch holds at most 1 MiB and is cut only at a file boundary, and
at most 200 files are listed. Ignored files are not seen and renames are not
detected. When the attempt moved HEAD, the new HEAD is recorded as the
candidate revision; otherwise it stays unmeasured. A workspace that is not a
git repository, the fixture, fake-provider, and isolation-probe modes, and a
capture that fails record why nothing was captured and run as before.
Each completed run also leaves a `handoff.json` in its run evidence directory:
the blueprint's handoff record for that attempt, carrying the objective, the
base and candidate revisions, the completed, failing, and not-run acceptance
identifiers, the environment state, the commands actually run, the unresolved
effects, the remaining budget, and the next eligible action. The base revision
is the commit observed at attempt start, before the implementation command, and
the candidate revision is the commit the attempt made; when the attempt did not
move HEAD there is no candidate revision and the field says so. The three
identifier lists are disjoint and cover the contract's identifiers: an
identifier whose command never ran, because the run stops at the first failing
command, is in neither the completed nor the failing list. The next eligible
action is one of three closed values, `product_review`, `bounded_repair`, or
`controller_decided`, and it says whether the factory or the successor decides
it. Every field the factory cannot observe is null with the reason that it
could not be observed: tokens and cost are never estimated, the environment
digest is never computed, and the unresolved effects and the remaining budget
are not derived from a declaration. The record is scoped to one attempt by its
run directory and names its job, run, and specification hash; a later run
leaves an earlier record byte-identical. It is context and never a verdict:
nothing judges an attempt by it, and the successor still has to check the
ledger and the workspace against it and reconcile a disagreement.

A successor asks for that check with
`python3 -m overseer.factory reconcile-handoff <id>`. It reads the job's
`handoff.json` back and compares it with four authorities: the ledger row
(the job's identity, state, detail, specification hash, and run id, and the
contract's acceptance identifiers), the digest the ledger recorded for the
record file, the exit codes recorded in the run's `context.json`, whose digest
the ledger sealed, and the workspace's current HEAD, read through the
read-only git snapshot. The completed, failing, and not-run lists must follow
from those exit codes by the same rule the record itself uses. A
disagreement is one of a closed list of ten kinds —
`job_id_mismatch`, `run_id_mismatch`, `spec_hash_mismatch`, `state_mismatch`,
`detail_mismatch`, `acceptance_ids_mismatch`, `acceptance_results_mismatch`,
`digest_mismatch`, `candidate_revision_mismatch`, and
`base_revision_unanchored` — and each one names what the record says and what
the authority says. The verdict is
`agree`, `disagree`, or `unverifiable`: a missing or malformed record, a
missing ledger digest, a missing, oversized, malformed, or re-digested context
manifest, or a workspace that cannot be read is unverifiable with its reason
and is never reported as agreement. No command is re-run: the exit codes are
the factory's own record of the attempt. The result goes into
`reconciliation.json` beside the record, a `reconciliation` key in
`summary.json`, and one `reconciliation` event in the ledger. It is a
read-only report: it records a disagreement and does not resolve one, it
never changes the job's state or rewrites `handoff.json`, and it does not
rewrite the context manifest, which it reads, because the manifest's digest is
already in the ledger. An unknown job id prints a JSON error and exits 1; a
finding is a report and exits 0.
The [harness framework](docs/HARNESS_FRAMEWORK.md) maps that design onto the six
harness pillars and the code that implements them.

Run `python3 -m overseer.factory --help` for the separate explicit-job runner.
Each completed run writes a `context.json` manifest into its run evidence
directory, recording what the controller supplied for that attempt and why,
and the ledger stores the four memory record kinds: a verified fact, a
decision, a hypothesis, and a historical attempt. Before a new attempt starts,
the runner recalls the relevant records: those of its own job and those of
earlier runs in the same project. A decision a later decision superseded, and a
verified fact whose bound revision is no longer the workspace's base commit,
are marked as unusable rather than handed over as settled. The recall is
written to `recall.json` in the run evidence and passed to the worker through
`OVERSEER_RECALL_PATH`, `OVERSEER_RECALL_COUNT`, `OVERSEER_RECALL_KINDS`, and
`OVERSEER_RECALL_SUMMARY`. The runner also assembles a codebase context from
the workspace file tree: it selects the files the task commands name or whose
path matches the task terms, extracts their structural symbols, and writes the
map to `codebase.json` in the run evidence, which the worker receives through
`OVERSEER_CODEBASE_PATH`, `OVERSEER_CODEBASE_FILES`,
`OVERSEER_CODEBASE_SELECTED`, `OVERSEER_CODEBASE_SUMMARY`,
`OVERSEER_CODEBASE_RELATIONS`, and `OVERSEER_CODEBASE_MEMORY`. The map names
the files and the symbols and carries a bounded excerpt of their code: at
most 8 KiB and 60 lines per file, and 32 KiB for the whole attempt. It also
relates each selected symbol to the code that calls it and to the test files
that cover it. That relation is a static reference and not a proven call:
Python is parsed, every other language is matched textually, and an attribute
reference does not name the object it belongs to. The search is capped at 400
files and 2 MiB, with 20 callers and 10 tests per symbol; the size of a file
is checked before it is opened, so the bytes read never pass the bound. A
symbol nothing references is recorded as such, with the number of files that
were searched, and a corpus the cap truncated is recorded as truncated, with
the reason that says so. A file
whose name marks it as a secret is never read for its content, and a file that
is binary, too large, or not text is left alone. The manifest records the
excerpt's line ranges and byte counts, and the relation counts and the
per-symbol entries. The map also attaches each recalled memory record to the
selected symbols and files it names, with the record's status. The match is
textual and on identifier boundaries, so it does not prove that a record is
about a symbol: every name is matched in the record's affected component, and
only an identifier-shaped name, such as `build_filter` or `WidgetFilter.apply`,
in its entry. A superseded decision, an invalidated fact, a hypothesis, and a
past attempt are attached but marked not usable, and the digest prints
`NOT USABLE` on their lines. At most 5 records are kept per symbol and per
file, 160 characters of each entry, and 6 memory lines per file in the digest;
a record that names nothing selected stays in the recall and is counted as
unattached. `OVERSEER_CODEBASE_MEMORY` carries the number of attached records.
An attached decision is supplied to the attempt; nothing enforces it. The
selection is then widened, one round only: a file whose path a current
decision names in its affected component or entry, and a file that holds a
caller of a symbol of the task's own selection, are added even when the task
terms do not match them. At most 4 files are added, never past the bound of
12 and never in place of a file the task selected, and the task's own files
spend the excerpt budget first. A test file is not added as a caller, a secret
is never added, and a verified fact, a superseded decision, a hypothesis, and
a past attempt never widen. Each added file says why it was added and by what,
the candidates the bounds left out are recorded with the reason, and
`OVERSEER_CODEBASE_WIDENED` carries the number of added files. The callers
come from the caller lists of the relation, which hold at most 20 per symbol,
so a file holding only callers past that cap is not considered, and the
selection says how many caller lists were cut. A widened file
was found by a static reference or a textual path match; that does not prove
it is relevant.
A command-mode task must carry a `contract` block that states the
role, risk tier, external effects, protected paths, approval requirements,
acceptance identifiers, required capabilities, project constraints, measured
evidence, provider availability, and budget limits. The block is validated and
stored with the task; it records those statements and enforces none of them.
A command-mode task may also carry an optional `envelope` block that names one
of the four capability modes, its declared scope, whether a fresh decision is
required, and the decider it names. The mode, the scope, and the decider
identity are recorded, not authorized. The one enforced part is the gate: a
task that declares it needs a decision waits in `awaiting_approval` and is not
dispatched until a decision is recorded in the ledger, and that record names
who decided. Give the decision with the runner's own command:

```sh
python3 -m overseer.factory decide <task-id> --decision granted --decider operator
```

A repair is submitted against the job it repairs, and the two share a lineage:

```sh
python3 -m overseer.factory submit repair.json --repair-of <failed-task-id>
```

The lineage counts its consecutive attempts that end in any terminal state
other than `passed`. When the count reaches its bound, `min(3, 1 +
repair_allowance)` — the blueprint's one attempt plus two repairs, lowered by a
smaller contract allowance — the lineage is frozen, and a further
`--repair-of` submission against it is refused, naming the lineage, its
strikes, and its bound; the refused job is not stored. A `passed` attempt
closes the lineage, and a `cancelled` or refused job is neither a strike nor a
reset. The strike is recorded in the same transaction as the job's final
transition, so the ledger cannot show a terminal state without its strike. The
freeze never changes any job's own state: the job that tripped it stays
`failed`, and only the lineage is frozen. The bound source is recorded, so a
lineage frozen after one attempt says plainly that its contract set
`repair_allowance: 0`. An operator reopens a frozen lineage, resetting the
count and granting a fresh bound, with a named, recorded note:

```sh
python3 -m overseer.factory release <lineage-id> --decider operator --note "investigated the flake"
```

The decider is recorded, not authorized, exactly as a decision is. Only
command-mode jobs carry a lineage; the fixture, fake-provider, and
isolation-probe modes do not. The lineage is context for deciding whether to
keep repairing, not a verdict: nothing consumes the contract's
`repair_allowance` beyond setting the bound, and the freeze caps cost, it does
not diagnose the failure. A lineage also freezes *before* its bound when two
consecutive failed attempts repeat the same failure unchanged: a byte-equal
fingerprint of the failing and not-run acceptance identifiers, the failing
command's exit code and timeout flag, and the patch digest (or `no patch`). The
comparison is byte-equal, never semantic, so a worker that changes its patch
each attempt still counts as new evidence and runs to the bound.

After the implementation command, a command-mode attempt also reads the last
64 KiB of that command's log and records a `worker_report.json` in the run
evidence: the parsed AGENTS.md status block (`STATUS`, `TESTS_PASSED`,
`FILES_MODIFIED`, `NEXT_AGENT_INSTRUCTION`), the digest of the bytes read, and
whether a `TESTS_PASSED: TRUE` claim disagrees with the exit-code outcome. The
report is evidence, never a verdict: exit codes decide the state, a disagreeing
claim is recorded and changes nothing, and a missing or invalid block is
recorded with its reason and is not a strike by itself. The block's
instruction is decoded as a plain string and never executed. When the block is
`STATUS: STUCK_NEEDS_ESCALATION`, the job's lineage is frozen with the reason
that the worker requested escalation, or an `escalation_requested` event is
recorded when there is no lineage. The report's digest is sealed with a
`worker_report` event, and the context manifest carries its pointer and digest.

An operator can pause factory dispatch with a recorded note:

```sh
python3 -m overseer.factory pause --note "holding while I investigate"
python3 -m overseer.factory unpause --note "resume"
```

While paused, `run_one` dispatches nothing and reports the pause instead,
exiting non-zero. The pause is read inside the dispatch transaction, so a
paused factory starts no new job, and it survives backup and restore. It pauses
*dispatch* only: a job already running is not interrupted.

A job can be driven by a real coding agent rather than a hand-written command.
`overseer/provider.py` builds an OpenCode headless invocation —
`opencode run --standalone --model <model> --auto <instruction>` — with the
instruction placed as one whole argument that is never passed through a shell.
OpenCode's `opencode/*-free` gateway models cost nothing and need no
credentials. The factory runs that command with the child's PWD set to the
workspace, so the model's file edits land in the workspace, and the acceptance
commands then verify them by exit code.

The adapter can also detect the active coding-agent session from the
environment and inherit its runner, so a job is driven by whatever CLI launched
Overseer (Claude Code, Codex, or OpenCode) instead of a hardcoded one:

```sh
python3 -m overseer.provider "implement add() in calc.py"        # reports the resolved invocation
python3 -m overseer.provider "..." --runner opencode --model opencode/glm-5.3-flash-free
```

The execution-safe default is the free OpenCode gateway: when no session is
detected, OpenCode free is used. An inherited **Claude or Codex** runner spends
that account's credits, so it is reported in the result rather than chosen
silently; pass `--runner opencode` (or a free `--model`) to stay free.
`overseer.provider.build_task` returns a submittable factory task whose
implementation is the resolved invocation. The adapter builds the command and
the task; nothing calls it automatically yet — the unattended feed loop that
would is not built.

To point the factory at a brand-new external repository, scaffold one:

```sh
python3 -m overseer.target init /abs/path/to/new-project [--spec SPEC.md]
```

It creates (or accepts an empty) directory, runs `git init`, copies an optional
`SPEC.md`, and makes one initial commit with a fixed local identity, so the
first attempt has a measurable base revision. It refuses a non-empty directory,
a path inside an existing git work tree, a relative path, and a symlink, and
prints one JSON object (the path, the head commit, whether a spec was copied) or
a JSON error with a non-zero exit. Its writing git runner is separate from the
read-only runner used for evidence.

At the start of every attempt the factory also reads the target's
`<workspace>/SPEC.md`, bounded to 64 KiB, and records its path and digest (or
its absence and the reason) in the context manifest, handing the attempt
`OVERSEER_SPEC_PATH` and `OVERSEER_SPEC_SHA256`. A `SPEC.md` symlink that
resolves outside the workspace is refused and recorded as absent, and a missing
`SPEC.md` is absent rather than an error. The spec is context only: nothing
checks the work against it.

An unattended feed loop can drive the factory from a loop spec:

```sh
python3 -m overseer.orchestrate --db DB --loop LOOP.json --target DIR [--once] [--dry-run]
```

Each iteration builds a command-mode job with the provider adapter, submits it
(as a repair of the previous job after a failure), runs it, reads the worker
report, and feeds that report's `NEXT_AGENT_INSTRUCTION` into the next
iteration. The first instruction is the loop spec's objective; every later one
comes only from a valid status block, and a missing or invalid block stops the
loop with `OVERSEER_NEEDS_INPUT` rather than inventing an instruction. The loop
stops when dispatch is paused, the lineage is frozen, the last job awaits
approval (it never decides), the worker asks for input, the daily cap (counted
from ledger events, so it holds across a restart) is reached, or the objective
reports `OVERSEER_DONE`. An `flock` allows one loop per ledger. For unattended
safety it drives the free OpenCode gateway by default and never silently
inherits a paid session; `--dry-run` builds the next job without submitting it.

Run `python3 scripts/check` for isolated local verification. The terminal
monitor continues to operate independently.

## Installed configuration

The user service is enabled and running with automatic replies. User lingering
is enabled, allowing it to run after logout. It checks every 30 seconds, waits
three minutes, and permits at most 12 replies per pane per rolling day, with a
15-minute cooldown. Kali labs and the setup conversation are excluded.

```sh
overseer status
overseer exclude labs
overseer exclude %2
overseer include %2
journalctl --user -u overseer.service -f
systemctl --user stop overseer.service
```

Exclusions match pane IDs exactly, or session names/window titles by
case-insensitive substring. Quoted globs are supported (`overseer exclude '*labs*'`).
`include` removes the exact exclusion rule supplied; other matching rules remain
in force. `watch` and `unwatch` independently control pane enrollment. Config is
reloaded every poll, so exclusions and setting changes apply within 30 seconds.
Do not use `include` as a substitute for checking `status` when several rules match.

## Project targeting

The monitor manages only the panes that are in scope. A pane is in scope when
it was explicitly enrolled with `overseer watch`, or when the configured
target scope names it. Every other tmux window is ignored: it is never
snapshotted, never queued, never sent to, and never typed into.

`config.json` carries the scope:

```json
"targets": ["overseer-projects-1174383"],
"target_paths": ["."]
```

- `targets` are patterns matched against the pane ID, the session name, and the
  window title, with the same rules as `exclude`: an exact pane ID, a
  case-insensitive substring, or a quoted glob. A matching pane is managed
  without being enrolled.
- `target_paths` are directories. A pane whose client runs inside one of them
  is managed. A relative path is resolved against the directory that holds
  `config.json`, so `"."` means this workspace. The directory is the client's
  own, not the bridge's, so a reptyr-bridged session is judged by the project
  its client actually works on.

The rules, in order: an excluded pane is never managed, even when it is
enrolled or targeted. Otherwise an enrolled pane is managed, then a targeted
one. `overseer status` shows the scope of every window: `WATCHED` for an
enrolled pane, `TARGETED` for a pane in scope by configuration, `EXCLUDED` for
an excluded one, and `OUT OF SCOPE` for a window the monitor ignores.

## Try it

```sh
cd /home/kali/Programming/Projects/Overseer
python3 -m unittest discover -s tests -v
python3 -m overseer start my-project codex
tmux attach-session -t my-project
```

Use `claude` in place of `codex` for Claude. Additional client arguments follow
the client name, for example `python3 -m overseer start resumed codex resume`.
Use the client's resume picker to choose an existing conversation. To keep the
client running after leaving a terminal, detach with `Ctrl-b`, then `d`.

To preview instead of sending, set `dry_run` to `true` in `config.json`. Eligible
replies are then logged but never sent. The installed background service already
runs the monitor; to run it manually, stop that service first:

```sh
cd /home/kali/Programming/Projects/Overseer
systemctl --user stop overseer.service
python3 -m overseer run
```

To enable sending, set `dry_run` to `false` in `config.json`.
`reply` is the single-line instruction used when a pane has not yet printed a
report. The included reply tells the client to follow
`/home/kali/Programming/Projects/AGENTS.md` and the coder optimization playbook, do the next
authorized step, and print one visible `OVERSEER_REPORT` line. That line starts
with `OVERSEER_REPORT` and a JSON object. The keys are `status`, `objective`,
`remaining`, `done`, and `evidence`. `status` is `continue`, `step_done`,
`done`, or `needs_input`. `continue` and `step_done` need a nonempty objective
and remaining step. `step_done` means that a step's own stopping condition was
met and that the objective still has the next step named in `remaining`: a
prompt's stopping condition ends that prompt, not the objective. The reply and
every prompt Overseer composes say so, and they tell the client to give each
executed step's results to the dedicated prompt-writing agent, which writes the
next bounded prompt that the client then executes.
Overseer reads the latest report on the visible screen, copies those fields
into the next one-line prompt, and submits that prompt. It does not ask another
model to invent the prompt, and it does not execute terminal text. A
`step_done` report gets a writer-handoff prompt: give this step's results to
the dedicated prompt-writing agent, have it write one bounded next prompt for
the named step, then execute and verify that prompt, or report `needs_input`
if no separate writer can be used. Overseer instructs that handoff; it cannot
see or verify that a separate writer ran or that its prompt was executed, and
it reads only the next report. A `done` report means the objective is
finished and stops further automatic prompts for that screen, even when its
`remaining` is not empty; a `needs_input` report always stops. An invalid
report, or a continue report with no objective or remaining step, also stops
that screen instead of falling back to `reply`. Project-specific agent and model
requirements still apply. Draft-only requests do not grant execution authority.

Manage existing tmux panes:

```sh
tmux list-panes -a
python3 -m overseer watch %0
python3 -m overseer status
python3 -m overseer unwatch %0
```

Only enroll panes whose LLM sessions you want to continue automatically.
Do not type in a watched pane while the bot is responding; desktop input and
tmux writes cannot be made atomic together. Unwatch the pane first when taking
over manually.

## The escalation hold

The monitor holds a pane and sends it nothing at all in two cases:

- the current turn of the pane carries a valid status block with
  `STATUS: STUCK_NEEDS_ESCALATION`
- three consecutive step reports of that pane show `TESTS_PASSED: FALSE` or an
  unchanged remaining fingerprint

A held pane receives no routine continuation, no report prompt, no writer
handoff, no capacity retry, and no routed-session resume. The hold is recorded
in the monitor's own state file, so it survives a restart, and it is not the
same store as the factory's repair-lineage freeze: the two never see each other.
A new turn, a changed screen, and a restart do not clear a hold.

Only the operator releases a pane, and only that pane:

```sh
python3 -m overseer unfreeze %0
```

The command writes a release record beside the state file and the running
monitor applies it at its next poll. Two limits are worth knowing: a pane whose
process is replaced is a new entry and is not frozen, and the release reaches a
running monitor one poll late.

## Model decisions

When a client reports that its model, its account, or its credits cannot be
used, the monitor does not retry and does not substitute a model. The affected
pane is paused, its FIFO reservation is released so the other watched panes
keep running, and the decision is recorded. The journal names the command:

```text
%3 model decision pending: unsupported_model (gpt-6-astra); choose with: python3 -m overseer model-select %3
```

`python3 -m overseer status` lists every pending decision. `python3 -m overseer
model-select %3` asks which permitted provider and model to use; the
non-interactive form is `python3 -m overseer model-select %3 --provider openai
--model gpt-5.6-terra`. A choice is applied through the client's own model picker
and confirmed from the pane's composer footer, so a pane that cannot serve the
chosen model is reported instead of being forced. When the chosen provider uses
a different client, the work is routed: a new session is started for that client
in the same working directory and the pane it came from stays paused.

The Codex picker has two steps. The first lists the models and the second asks
for the reasoning level, where the scope key `s` applies the change to the
session only and leaves the global default alone. The monitor uses the session
scope, so a change made through it does not edit the client's configuration.

### Credit fallback hierarchy

`config.json` carries a `fallback_policy`:

- **Primary, the paid tier.** `primary` names the providers that carry normal
  coding work.
- **Fallback 1, zero paid credits.** When a client reports exhausted credits,
  `zero_credit` names the provider that takes over. The monitor routes the work
  automatically: it starts that client in the pane's working directory, enrolls
  it, and sends the configured continuation so the work resumes. The pane that
  failed stays paused.
- **Fallback 2, every credit maxed out.** When the zero-credit tier reports the
  same failure, the pane is paused with the status `CREDITS_EXHAUSTED_WAITING`.
  Nothing is retried, no lower tier is used, and no model is substituted. The
  pause ends by itself when the client stops showing the error, which is what
  waiting for the credits to reset means here.

```text
%3 CREDITS_EXHAUSTED_WAITING: insufficient credit (credit_exhausted); waiting for the credits to reset
```

`excluded_models` names model ids that are offered nowhere: they are absent
from the provider lists, from the interactive picker, and from every automatic
choice. The current exclusion is `gpt-6-luna`, on the operator's stated
judgment that it is not a coding model. That is the operator's reason, not a
measured result.

The permitted providers and their model identifiers live in `config.json` under
`model_providers` and `allowed_providers`. They were verified locally with
`codex debug models`, `claude --help`, `opencode models`, and
`~/.grok/models_cache.json`, and they can go stale. No model name may be
invented; a model outside the configured list is refused. Codex, Claude, and
OpenCode sessions can be watched and driven; a Grok session cannot, because the
monitor does not recognize its composer, and it is reported instead of being
forced.

This feature does not substitute a model automatically, does not retry a
blocked pane, and does not drive a client that the account or provider cannot
serve. A route creates a new session; it never restarts or replaces an existing
one, and it never sends text to a pane other than the one it just created.

## Background service

```sh
mkdir -p ~/.config/systemd/user
cp overseer.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now overseer.service
journalctl --user -u overseer.service -f
```

Stop: `systemctl --user stop overseer.service`. Disable automatic startup:
`systemctl --user disable --now overseer.service`. Restart after code changes:
`systemctl --user restart overseer.service`.

For service operation after logout and startup without a desktop login, enable
user lingering with `loginctl enable-linger "$USER"` (the system may require
administrator authorization). The computer must remain powered on and awake.
The service restarts the monitor after failure; it does not recreate LLM
sessions after reboot. Reopen/resume and enroll those sessions after reboot.

## Detection and limits

With `serial_queue: true`, automatic sends use a persisted FIFO queue. Only one
Overseer-dispatched turn owns the slot. Other eligible panes wait until that turn
visibly finishes, stops, or reports a model-capacity error. Already running watched
panes also prevent new dispatches; they are never interrupted. New follow-ups go
behind existing waiters. Queue order and the active reservation survive restart
and appear in `overseer status`.

An explicit `Selected model is at capacity` terminal error enters the queue with
`capacity_retry_seconds` of waiting (default 120). It retries the same model at
most `capacity_max_retries` times (default 3) per failure episode, still subject
to the rolling daily reply limit. Retry delay replaces the ordinary idle/cooldown
timers for these errors. The FIFO head waits its retry delay; after its budget is
exhausted it is skipped so other work can run. A completed turn resets the retry
budget. Capacity errors do not establish that local concurrency caused them.

An ambiguous delivery or unrecognized completion holds the slot and logs a
warning after two minutes. Inspect that pane rather than blindly resending; an
identical capacity screen without an observed intervening run remains ambiguous
and is held rather than automatically retried. Changed footer tips do not count
as evidence of a new answer. A new routine continuation question can also end a
turn for clients that do not display Codex's completed-turn footer. An
operator can explicitly unwatch it to release its reservation. Exclusions,
unwatching, and leaving the target scope remove panes from queue control. The
scheduler serializes Overseer's
automatic terminal dispatches only: manual input, excluded sessions, and agents
delegated inside a session can still overlap. Terminal-state detection remains
heuristic, so this is not a provider-wide concurrency lock.

The monitor recognizes explicit routine questions such as “Would you like me to
continue?” and “Shall I proceed?”. With `continue_on_completion: true` (enabled),
it also recognizes Codex's completed-turn footer, `Worked for … • …`, when the
composer is empty. Eligible screens that contain an `OVERSEER_REPORT` line
receive a prompt built from that report. Eligible screens without one receive
`reply`. `OVERSEER_NEEDS_INPUT` always stops further automatic continuation of
that screen, as does a report whose status is `done` or `needs_input`.
`OVERSEER_NEEDS_INPUT` anywhere in the current answer stops it, not only in
the last lines. `OVERSEER_DONE` stops it too, unless the line directly above
the marker, blank lines aside, is a `step_done` report of the current answer:
then the marker ends the step, not the objective, and the screen gets the
writer-handoff prompt. `OVERSEER_STEP_DONE` under a `step_done` report of the
current answer does the same; on its own it is neither a stop nor a reason to
send. A report of an earlier turn, above the last submitted prompt, never
counts, so a stale step report cannot override a newer stop, and a step report
quoted with prose after it does not override `OVERSEER_DONE`. The prompts
quote the marker names, so a wrapped echo of a sent prompt cannot start a line
with one. A handoff
goes through the same idle threshold, permission and generation checks,
already-sent and held screens, cooldown, and daily limit as any other prompt,
and a step report with no remaining step stops it. The report has to stay on one visible line because the
monitor captures the current pane, not scrollback. Permission wording, generation
markers, and the other skip rules still apply to the whole visible screen,
including text inside a report. Idle alone without a recognized
question/completion marker does not trigger a reply.

If a client appears to ignore a continuation, inspect its response in the pane.
`sent routine continuation` means the configured instruction was typed.
`sent writer handoff prompt` means the typed line handed a finished step to
the prompt writer. `sent report-based prompt` means the typed line was built from the visible
report. Neither journal line includes the prompt or the report, and neither
proves that the client submitted, executed, or finished the work. `skipped:
invalid output report`, `skipped: report has no remaining work`, and `skipped:
output report requested no further continuation` mean that screen was withheld
and will not be answered again until its visible text changes. A visible client
response of `OVERSEER_DONE` means the client declared its work complete; it can
still have interpreted the task too narrowly. Changing `reply` applies to future
eligible sends that have no report; it does not clear existing stop markers or
resend old messages. Code changes apply after the user service is restarted.
Config changes apply on the next poll.

The foreground command must be `codex`, `claude`, or `opencode`, with an empty
composer line (`>`, `›`, `❯`, or `»`, including the verified empty Codex
placeholder and the OpenCode composer box). A shell,
typed draft, copy mode, exited pane, unrecognized
question, visible generation marker, or sensitive/permission wording causes a
skip. UI versions, wrappers, placeholders, and different languages can cause
missed prompts. These checks are heuristics, not proof of an agent's state;
validate against your clients in dry-run mode first. A Grok session is not
recognized, so the monitor reports it instead of driving it.

An OpenCode session is understood in both of its turn states. While a turn
runs, the running footer (`esc interrupt`) and the background-work hint mark
the pane as active, and it is never answered. When the turn ends, that marker
is gone and the composer is an empty box, so the pane counts as finished, the
queue reservation is released, and the next continuation is sent. A fresh
session shows an `Ask anything…` placeholder in the same box. OpenCode draws
no user-message boundary, so the tail of its screen is treated as the current
answer.

Replies have a 15-minute cooldown and a limit of 12 per pane per rolling day.
The monitor persists fingerprints in `~/.local/state/overseer/state.json` so
the same screen is not answered again after restart. It saves a send reservation
before delivery; an ambiguous or failed delivery is not automatically retried.
A file lock prevents two monitors sharing that state from sending duplicates.
Logs contain pane IDs and action reasons, not conversation contents. State
contains hashes and timestamps, not captured terminal text.

The monitor does not click permission dialogs, change LLM approval settings,
answer substantive questions, or submit shell commands. The terminal content
is never executed as code. A final recheck narrows—but cannot eliminate—the
race between observing the pane and sending input.
