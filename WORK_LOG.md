# Overseer Work Log

Chronological record of this authorized work, intended to preserve enough task
context, decisions, commands, outputs, and review results for a later agent to
continue or improve it. Do not store credentials or secrets here.

## 2026-10-19 — Start and baseline

### User objective and order

The user authorized all three previously identified items in order:

1. Add a trusted fixture path with acceptance bound to the exact candidate and
   verifier identity; candidate tampering after verification must invalidate
   acceptance.
2. Validate the three installed instruction skills using realistic and near-miss
   examples.
3. Work through the next Grok support item, subject to the project's M1/M2
   prerequisites and the installation report's unresolved authentication and
   keyring limits.

The user requested that all work be recorded in this separate file. Keep the
three phases distinct and update this log as work proceeds.

### Initial repository state

- Project: `/home/kali/Projects/Overseer`.
- Git root: `/home/kali/Projects/Overseer`.
- Starting `HEAD`: `e2b4351bbe0a703d975b11abe7f98c90bb332d76` on `main`.
- Existing tracked modifications: `README.md`, `docs/FACTORY_EXECUTION.md`,
  `docs/SOFTWARE_FACTORY_BLUEPRINT.md`.
- Existing untracked files: `DEVTOOLS_INSTALL_RESULT.md`,
  `GROK_INSTALL_NEXT_PROMPT.md`, `docs/FACTORY_SKILLS.md`,
  `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt`, and
  `factory/skills-provenance.json`.
- These pre-existing files are user/project work and must be preserved. This log
  is a new file created for the user's logging request.

### Applicable project guidance

- Follow `/home/kali/Projects/AGENTS.md`, the
  `/home/kali/Projects/coder_optimization/docs/PLAYBOOK.md`, and its `TASK.md`
  and `REVIEW.md` templates.
- Use a dedicated prompt-writing agent for the bounded prompt; the writer does
  not edit implementation files. The primary agent executes the authorized
  prompt and verifies it.
- Use one primary implementation editor. Preserve unrelated work. Use a fresh
  reviewer for consequential changes.
- Do not claim sandboxing: the existing runner executes trusted local commands
  with the user's privileges.

### Initial findings relevant to item 1

- `overseer/factory.py` supports existing explicit command tasks. It stores the
  task specification hash and command results, but the current acceptance record
  does not bind verification to a candidate digest and verifier identity.
- The Version 2 blueprint requires trusted built-in fixture modes, a limited
  candidate-file API, candidate-bound verification, and failure drills. Real
  provider adapters are a later milestone.
- `tests/test_factory.py` is the focused existing factory test file;
  `python3 scripts/check` is the project's isolated local check command.
- No tests or application code have been changed for this request yet.

### Worklog maintenance

Append each phase's prompt, files changed, substantive decisions, exact commands
and results, review feedback, and unresolved limitations below. Never copy
credentials or private authentication data into this log.

### Baseline checks — item 1

The following commands ran before application edits:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
```

Result: exit 0; all 12 existing factory tests passed in 1.982 seconds.

```text
python3 scripts/check
```

Result: exit 0; all 49 existing project tests passed in 3.834 seconds. This
project script isolates the test run from the live tmux server. The expected
queue warning lines appeared in scheduler tests; the suite passed.

The dedicated prompt writer was asked to produce the bounded implementation
prompt for item 1. Its prompt is pending and will be recorded here before
implementation begins.

### Phase 1 prompt and exact pre-edit state

Dedicated prompt writer: `/root/overseer_prompt_writer`. It read current
repository guidance, implementation, tests, and blueprint, then authored the
following bounded prompt. The primary agent is executing it; the writer did not
edit implementation files.

> Implement **Phase 1 only: trusted fixture execution and candidate-bound acceptance** for `/home/kali/Projects/Overseer`.
>
> Read the current `AGENTS.md`, `docs/FACTORY_EXECUTION.md`, `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt`, `overseer/factory.py`, and `tests/test_factory.py`. The M1/F05 contract is a trusted built-in fixture path with a limited candidate-file API: known-good fixtures pass, while known-bad fixtures and attempts to tamper with fixture acceptance fail. This does not establish an OS sandbox.
>
> **Preserve the existing worktree.** At handoff, `main` is at `e2b4351`. Modified files are `README.md`, `docs/FACTORY_EXECUTION.md`, and `docs/SOFTWARE_FACTORY_BLUEPRINT.md`; untracked files are `DEVTOOLS_INSTALL_RESULT.md`, `GROK_INSTALL_NEXT_PROMPT.md`, `docs/FACTORY_SKILLS.md`, `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt`, and `factory/skills-provenance.json`. Do not reset, stash, clean, overwrite, or discard them. Limit implementation edits to `overseer/factory.py` and `tests/test_factory.py`; use `WORK_LOG.md` as the separate record for all three authorized phases. It did not exist at the time of inspection: create it if still absent, record Phase 1 and leave Phases 2 and 3 pending.
>
> Add a fixture mode that is **separate from the existing generic argv command path**. Use a closed set of controller-defined fixture behaviors and a controller-owned verifier. Fixture specifications must reject arbitrary commands, `implementation`/`checks` argv, callbacks, plugins, or caller-supplied verifier rules. Fixture execution must not invoke subprocesses or run task-supplied code. Restrict candidate writes to the fixture’s explicitly allowed relative file paths; reject traversal, absolute paths, and paths that escape through symlinks. Keep verifier rules outside the candidate-write interface. Preserve the existing command runner’s behavior and do not describe it as sandboxed.
>
> Bind each verification result to both:
>
> - The exact candidate bytes, using SHA-256 of the raw bytes or a deterministic digest of a sorted manifest of allowed paths and their raw-byte hashes.
> - A controller-owned, versioned verifier identity, tied to the built-in verifier and fixture manifest; it must not come from task input.
>
> Persist both identifiers with the verification evidence. Recheck the candidate after verification and before recording success. A built-in post-check tamper case must fail closed. If a candidate is changed after a successful run, inspecting that run must no longer report its acceptance as valid; preserve the original evidence and expose the invalidation clearly.
>
> Add bounded tests proving: valid fixtures pass; invalid fixtures fail; fixture specs cannot supply executable checks or alter verifier rules; candidate paths cannot escape the allowlist; persisted evidence includes candidate digest and verifier identity; post-check tampering cannot become or remain accepted; and existing generic command-runner behavior still passes its relevant tests. Use temporary databases and workspaces, not the default runtime database.
>
> Before editing, record the current status and run the targeted factory tests as a baseline. Afterward, run the targeted factory tests and `python3 scripts/check`. Record actual changed paths, commands, outcomes, and unresolved issues in `WORK_LOG.md`; do not claim sandboxing or complete later phases.
>
> Stop when the fixture acceptance contract is implemented, the bounded checks pass (or a specific blocker is recorded), and the Phase 1 work-log entry is complete. Do not start skill validation or Grok support work in this phase.
>
> The existing runner executes task-supplied argv and is explicitly trusted local execution, not containment. The prompt keeps that route separate from the new fixture mode. It also makes post-run tampering fail closed at inspection, in addition to checking for mutation between verification and success recording.

Exact pre-edit status command:

```text
git status --short --branch && git rev-parse HEAD
```

Output: `## main`; modified `README.md`, `docs/FACTORY_EXECUTION.md`,
`docs/SOFTWARE_FACTORY_BLUEPRINT.md`; untracked
`DEVTOOLS_INSTALL_RESULT.md`, `GROK_INSTALL_NEXT_PROMPT.md`, `WORK_LOG.md`,
`docs/FACTORY_SKILLS.md`, `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt`, and
`factory/skills-provenance.json`; `HEAD` is
`e2b4351bbe0a703d975b11abe7f98c90bb332d76`.

Writer risk note: keep arbitrary argv execution isolated to the legacy trusted
command mode. Post-run tampering should invalidate at inspection, and the
fixture path must not be presented as an OS sandbox.

### Phase 1 test-first check

Added bounded cases to `tests/test_factory.py` for a passing fixture with
candidate/verifier receipt, a rejected known-bad fixture, rejection of task
commands/verifier overrides, path escape/symlink rejection, a built-in
post-verification tamper case, and invalidation after post-run candidate edits.
The passing fixture test also asserts that fixture execution does not launch a
subprocess. Existing generic command-runner tests remain in the same file.

Command:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
```

Expected red result before implementation: test-module import failed because
`fixture_candidate_path` has not yet been implemented. Exit 1. This is the
planned test-first failure, not a pre-existing baseline failure.

### Phase 1 implementation

Implementation is limited to `overseer/factory.py` and `tests/test_factory.py`.

- Added a fixture task mode with exactly four permitted fields: ID, objective,
  mode, and a controller-defined scenario (`known_good`, `known_bad`, or
  `tamper_after_check`). It does not accept workspace paths, argv commands,
  callbacks, plugins, or verifier rules.
- Fixture execution is controller code and does not spawn a subprocess. It
  writes one fixed candidate file, `candidate.json`, under the run evidence
  directory. The path helper rejects unapproved names, traversal, absolute
  paths, and symlinks; creation uses exclusive, no-follow flags where supported.
- Added a controller-owned JSON verifier for `answer == 42`. Its versioned
  identity includes a SHA-256 digest of the verifier/fixture manifest.
- Persisted the inspected candidate hash and verifier identity in both
  `verification.json` and a `fixture_verifications` SQLite table. The candidate
  is rehashed after verification and before acceptance is recorded.
- The built-in `tamper_after_check` case changes the candidate between checking
  and acceptance and fails closed. `inspect` revalidates accepted fixture
  evidence; post-run candidate edits transition the task to `invalidated`, add
  an event, and preserve the original evidence/receipt.
- Existing argv command tasks retain their existing path.

Targeted post-change command:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
```

Result: exit 0; all 18 tests passed in 2.033 seconds, including the 12 existing
generic factory tests and 6 new fixture acceptance cases. Full project check and
independent review are still pending.

Intermediate full-suite command:

```text
python3 scripts/check
```

Result at that implementation checkpoint: exit 0; all 55 tests passed in 3.945
seconds. After that run, the receipt gained the explicit verifier outcome, and
the tests gained direct verification-file tamper coverage; the final checks
below were rerun against those refinements.

Intermediate focused command after the verifier-outcome refinement:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
```

Result: exit 0; all 18 tests passed in 1.970 seconds.

Final Phase 1 verification commands:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
```

Results: focused suite exit 0, 19 tests passed in 1.888 seconds; isolated full
suite exit 0, 56 tests passed in 3.631 seconds. The full suite again emitted
only the expected scheduler warning lines and passed.

An independent reviewer has been assigned against the Phase 1 prompt and diff.
Review findings are pending; do not mark Phase 1 complete until they are handled.

### Phase 1 independent review and corrective prompt

Fresh reviewer finding: `_fixture_evidence_valid()` coerced receipt flags with
`bool()`. JSON strings such as `"false"` are truthy and could be accepted as
matching SQLite's true flags; a valid JSON array could raise `AttributeError`
instead of invalidating evidence. The reviewer requested strict JSON type and
shape validation plus regression checks.

The dedicated prompt writer authored the following bounded correction prompt
after reading the reviewer finding and the current Phase 1 state:

> Fix the confirmed fail-open/malformed-receipt defect in the Phase 1 fixture
> acceptance code only. The reviewer found that `_fixture_evidence_valid()`
> applies `bool()` to `verification.json` values. A string such as `"false"` is
> truthy, so it can match a stored true flag. If the JSON top level is an array,
> `saved.get(...)` raises `AttributeError` during `inspect()` instead of failing
> closed. Require a JSON object with exactly the expected receipt keys; reject
> missing or extra keys. Require exact JSON types: strings for text/hash fields
> and actual booleans for `accepted` and `verifier_passed`. Do not coerce JSON
> values with `bool()`. Validate digest formatting and the expected candidate-
> path shape. On invalid JSON, a non-object value, or any schema/type mismatch,
> return an invalid-evidence result. `inspect()` must not raise; a previously
> passed fixture must become `invalidated` with `evidence_valid` false. Keep the
> SQLite receipt schema and its existing integer flag encoding unchanged.
> Preserve the stored DB receipt and tampered evidence as audit records; do not
> repair or rewrite malformed evidence. Add regressions for string `"false"` in
> each flag and a JSON array. Confirm the DB receipt remains intact and existing
> receipt behavior still passes. Limit changes to Phase 1 receipt validation,
> tests, and this log. Preserve unrelated changes. After the fix, run the focused
> factory suite and `python3 scripts/check`, append actual outputs, and stop
> when checks pass or report a concrete blocker.

Execution is limited to `overseer/factory.py`, `tests/test_factory.py`, and
this log. Receipt validation now checks exact DB and JSON types, required keys,
lowercase SHA-256 formatting, and the fixed allowlisted candidate path before
comparing values. Invalid structures return a failure reason so `inspect()` can
invalidate a passed fixture without throwing. Regression cases cover both
string-valued flags, a top-level JSON array, preserved SQLite receipt flags, and
preservation of the original receipt in the inspection result. Verification
results for this correction are recorded below after execution.

First focused rerun after the strict validation edit:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
```

Result: exit 1, 21 tests run with 7 failures. Inspection rejected all fixture
receipts because the SQLite row includes its `job_id` primary key while the
persisted JSON evidence intentionally omits that database-only field. Corrected
the validation to check the exact DB schema (including `job_id`) separately
from the exact evidence schema. No production behavior outside receipt
validation was changed. The DB flag preservation assertion now compares the
two SQLite integer values directly.

The fail-closed path also catches invalid UTF-8 while reading evidence; a
regression case was added because decoding can fail before JSON parsing starts.

Final corrective verification after separating the database and JSON schemas
and adding the UTF-8 regression:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
```

Result: exit 0; all 22 factory tests passed in 1.935 seconds.

```text
python3 scripts/check
```

Result: exit 0; all 59 project tests passed in 3.747 seconds. The scheduler
tests printed their expected queue uncertainty and observation warning lines.
`git diff --check` also exited 0. A fresh reviewer has been assigned to review
the corrected Phase 1 diff; Phase 1 remains open until that review returns.

The fresh reviewer reproduced one additional malformed-evidence edge case:
deeply nested JSON can raise `RecursionError` in `json.loads`, leaving an
already passed run in `passed` state. The reviewer verified this using a
temporary database and requested that parsing fail closed and retain the DB
receipt. This finding is being handled before Phase 1 closes.

The dedicated prompt writer also completed a bounded `ideas.txt` prompt for
the user's new swarm/verification/Obsidian idea. It is deferred until Phase 1
is complete to preserve the requested #1-first ordering.

The dedicated prompt writer authored the following final Phase 1 correction
prompt after reading the fresh review finding:

> Fix the Phase 1 receipt-validation edge case only. The fresh reviewer
> reproduced that deeply nested JSON in `verification.json` can make
> `json.loads()` raise `RecursionError`, which currently escapes inspection and
> leaves a passed fixture passed. Handle `RecursionError` alongside the
> existing parse/read errors and return invalid evidence so `inspect()` marks
> the prior pass `invalidated` with `evidence_valid` false. Do not use a broad
> exception handler. Add a regression that runs a known-good fixture, stores
> its SQLite receipt, replaces `verification.json` with nested arrays beyond
> the parser recursion limit, confirms inspection returns without raising and
> invalidates the run, and confirms the database receipt is unchanged. Rerun
> the focused factory suite and `python3 scripts/check`; record actual results
> in this log. Keep changes limited to Phase 1 code, tests, and log. Preserve
> unrelated changes and leave Phase 1 open for fresh review.

The parser now treats `RecursionError` as malformed evidence. A regression
creates nested JSON past the parser limit and verifies invalidation plus exact
preservation of the returned and stored SQLite receipt.

Corrective verification results:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
```

Result: exit 0; all 23 factory tests passed in 1.999 seconds.

```text
python3 scripts/check
```

Result: exit 0; all 60 project tests passed in 3.778 seconds. Scheduler
uncertainty/observation warnings were expected test output. Final independent
review of the parser correction is pending.

`git diff --check` after this correction exited 0.

Fresh final review: no actionable issue found in the Phase 1 receipt correction.
The reviewer confirmed fail-closed behavior for invalid UTF-8, non-object JSON,
wrong flag types, and deeply nested JSON; the regression checks preserve the
SQLite receipt. The reviewer independently reran the focused suite (23 passed)
and `python3 scripts/check` (60 passed). Review limits: adversarial edits to
the SQLite database and concurrent filesystem races were not assessed.

Phase 1 is complete against its acceptance criteria. Fixture mode now uses
controller-owned, closed scenarios and verification; persisted evidence is
bound to a candidate digest and verifier identity; malformed or tampered
post-run evidence invalidates rather than preserves a pass. The generic argv
runner's existing tests remain green. No OS-sandbox claim is made.

### User idea: parallel research, verification, and Obsidian

After Phase 1 closed, the user asked whether the pasted 300-agent research
workflow could fit Overseer and requested a text file named `ideas`. The
dedicated prompt writer produced a bounded documentation prompt. I reviewed
`README.md`, `overseer/__main__.py`, `overseer/tmux.py`, `overseer/factory.py`,
`factory/routing-policy.json`, `docs/FACTORY_EXECUTION.md`, and
`docs/FACTORY_SKILLS.md`, then created `ideas.txt` at the project root. The note
separates implemented monitor/factory behavior from proposed architecture,
labels the post's speed/quality/cost figures unverified, and suggests a small
measurable prototype with source checks and an Obsidian export. No code, provider
integration, or external service was run for this idea.

### Phase 2: installed-skill validation

The dedicated prompt writer authored the Phase 2 task prompt. I read the skill
inventory, provenance, all three installed `SKILL.md` files, shared project
instructions, and the coder_optimization playbook/task/review templates. Before
evaluation, all three installed `SKILL.md` hashes and all three MIT `LICENSE`
hashes matched `factory/skills-provenance.json`.

Each completed case used a separate fresh agent context (`fork_turns: none`).
The exact prompts and observed outputs were:

1. **better-prompt, realistic:** “`/better-prompt Add a CSV export option to
   our Python CLI report command. Keep the existing JSON output unchanged by
   default and use only the Python standard library.`” The output identified
   relevant source files and tools, preserved scope, and produced a concrete
   task prompt. It did not explicitly ask for a test, independent reviewer, or
   other correctness evidence, so it missed the skill's fourth required step.
2. **better-prompt, near-miss:** “I have this task prompt: ‘Add CSV export to
   the report command; preserve JSON by default.’ What is the main ambiguity I
   should clarify before giving it to a developer?” The agent directly named
   schema and row granularity and did not rewrite the prompt. This met the
   near-miss contract. Neither output proves runtime skill activation.
3. **goal-loop, setup miss:** “Draft a `/goal` contract only (do not create or
   start any goal) for adding a `--json` output option to a small Python command-
   line tool. Read `AGENTS.md`, the CLI implementation, and its tests. Preserve
   the current plain-text output and add no dependencies. Validate with
   `python3 -m unittest discover -s tests`. Stop when the tests pass and default
   output remains compatible, or when behavior needs product input. Include
   checkpoints and a brief progress log.” The agent correctly asked which
   repository, since the prompt did not identify one. It then began read-only
   exploration in coder_optimization; I interrupted it before further work.
   It reported the existing scorecard suite passed 9 tests. No files changed.
   This attempt exposed an evaluation-prompt ambiguity and is not counted as a
   successful skill output.
4. **goal-loop, realistic retry:** “Draft a `/goal` contract only for this
   hypothetical task; do not inspect or modify any real repository and do not
   create or start a goal. Add a `--json` output option to a small Python CLI in
   a hypothetical repo. Assume the files are `AGENTS.md`, `src/cli.py`, and
   `tests/test_cli.py`. Preserve existing plain-text output by default and add
   no dependencies. The exact validation command is
   `python3 -m unittest discover -s tests`. The stop condition is passing tests
   plus unchanged default output, or encountering behavior that needs product
   input. Include checkpoints and a brief progress log. Return only the contract
   body as the skill requires.” The returned block included Objective, Read
   first, Constraints, Validate, Checkpoints, and Stop when; it respected the
   hypothetical scope and did not create a goal. This met the task contract.
5. **goal-loop, near-miss:** “What is a Python context manager? Explain briefly
   with a tiny example.” The agent answered directly with a short `with open`
   example; it did not draft or start a goal. This met the near-miss contract.
6. **effective-agent-skills, realistic:** “Review this inline agent skill and
   give recommendations only; do not rewrite it or create files.” The provided
   sample had a `CSV` name in folder `csv-export/`, an indented vague
   description, and a one-line generic body. The agent identified the name and
   frontmatter problems, vague triggering, missing scope/workflow, and absent
   validation/output contract. It gave recommendations without editing. This
   met the task contract.
7. **effective-agent-skills, near-miss:** “Review this README excerpt for
   clarity and outdated user instructions. Give a short review and suggested
   edits; do not turn it into an agent skill.” The agent reviewed the actual
   README content and suggested clarifying overwrite behavior and current CLI
   syntax. It did not switch to skill authoring. This met the near-miss contract.

The six planned cases completed across the three skills; the goal-loop setup
miss is also retained above as a failed attempt. Runtime activation is still
unverified because this interface provides no skill-load telemetry. Agent
self-reports and catalog visibility were not treated as proof. This is a small
same-runtime usefulness sample, not evidence of general quality, efficiency, or
cost gains.

After evaluation, all three installed `SKILL.md` hashes and all three license
hashes still matched the provenance manifest; no installed skill file changed.
`docs/FACTORY_SKILLS.md` now records the six case outcomes and the activation
telemetry limitation. `git diff --check` exited 0. No code tests were run for
this documentation-only evaluation. Phase 2 is complete as a bounded usefulness
sample; runtime activation remains unverified.

The `ideas.txt` file was read back after creation. It contains the requested
idea summary, current capability assessment, proposed design, measurable small
prototype, and constraints/risks sections; it labels the pasted metrics as
unverified.

### Phase 3: Grok support readiness

The dedicated prompt writer supplied a documentation-only prompt for this
phase. I inspected the existing install result, saved CLI output, project
readiness docs, process monitor, factory runner, routing proposal, and blueprint
gates. The local record identifies Grok Build 1.0.62 and saves successful
version/help/login-help checks. The help output shows single-turn mode, JSON
output, tool and turn-limit flags, sandbox option, and an `agent` command; it
does not prove support for the current docs' exact `grok agent stdio` form.
Authentication and model access remain untested. The Cursor keyring observation
in the install record is explicitly kept separate from Grok.

I checked these official upstream sources on 2026-10-19 and linked them in
`docs/GROK_SUPPORT_READINESS.md`:

- https://docs.x.ai/build/overview
- https://docs.x.ai/build/cli/headless-scripting
- https://docs.x.ai/build/features/sandbox
- https://docs.x.ai/build/modes-and-commands
- https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-shell/README.md

The readiness note distinguishes interactive terminal monitoring from a
structured headless factory adapter. It recommends finishing the outstanding
M1 fake-worker reliability, isolation, and ledger recovery gates before an M2
provider pilot. It records that the fake-provider milestone needs no Grok
authentication or inference, while an actual provider pilot does. It also lists
acceptance checks, authorization boundaries, and actions not taken. The saved
`GROK_INSTALL_NEXT_PROMPT.md` and `DEVTOOLS_INSTALL_RESULT.md` were left intact.

Final review commands for this phase:

- Read `docs/GROK_SUPPORT_READINESS.md` and the end of this log with `sed` and
  `tail` to inspect the saved artifacts.
- `git diff --check` exited 0.
- `git status --short` confirmed the existing workspace changes plus this
  phase's new readiness note; no cleanup or reset was performed.

No tests, provider configuration, code changes, Grok login, API request,
inference, or pane launch were performed for Phase 3. The document was read
back; the M1 and live-provider acceptance checks are proposals and remain
unrun. Phase 3 is complete as a readiness plan, not as Grok integration.

### Follow-up: Bober_smart links and idea images

The user supplied two X links and asked that both be checked for ideas and that
their images be saved under an `ideas/` directory. The browser page renderer
returned internal errors for the X URLs, so I also fetched the public X HTML
directly with Python `urllib` and inspected its metadata and image tags. The
first link resolves to “Claude Second Brain & Folder Workflow: The Complete
Guide.” The indexed article text and the downloaded images provided additional
ideas: a short index/router; semantic folders; one topic per file; source-only
answering with citations; an explicit “not found” behavior; append/update rather
than duplicate; and a troubleshooting map from retrieval failures to fixes.
Those were added to `ideas.txt`, with the vendor-specific `CLAUDE.md` loading
claim qualified for other runtimes.

The second link resolves to “10 folders with the best skills for Claude.” Its
listed skill areas were recorded as candidate workflow ideas, with a note to
evaluate provenance, license, runtime compatibility, permissions, and behavior
before adoption. Reported iteration-speed and revenue improvements remain
unverified; no skills were installed. The second linked X page exposed one
article image (its cover) in the public HTML.

Downloaded five original-size JPEGs to `ideas/`: four from the first linked
article (cover, folder layout, index/protocol, troubleshooting table) and one
cover from the second. The local `file` command identified each as JPEG; the
download script checked non-empty `image/jpeg` responses. I viewed all five to
confirm content and added `ideas/SOURCES.md` with source URLs, media IDs, image
descriptions, retrieval scope, and the limitation that the second page exposed
only its cover. No profile avatars or reply images were included.

Relevant checks and file changes:

- Read the prior `ideas.txt`; appended the two article-derived idea sections.
- Created `ideas/` and saved `01-second-brain-cover.jpg`,
  `02-second-brain-folder-structure.jpg`,
  `03-second-brain-index-protocol.jpg`,
  `04-second-brain-troubleshooting.jpg`, and
  `05-claude-skills-cover.jpg`.
- Created `ideas/SOURCES.md` and recorded the downloaded source media IDs and
  original X URLs.
- The final read-back and `git diff --check` are recorded after the edits.
- This was documentation and asset work only; no tests, installation, code, or
  provider calls were made.

### Follow-up: LLM Wiki / second-brain research pilot

The user asked what the Claude second-brain pattern is and whether it could fit
Overseer. The dedicated prompt writer authored the bounded documentation-only
pilot prompt. The primary agent researched Karpathy's LLM Wiki proposal, the
official Claude Code memory and Obsidian Markdown guidance, and the previously
reviewed Bober_smart folder workflow. The research is recorded as F21–F25 in
`research/sources.json`; the note distinguishes source claims from
recommendations and treats the viral performance claims as unverified.

Created `research/llm_wiki/` with a schema and manual ingest/query/lint
workflows, navigation index, raw-source intake policy, one source-backed
concept note, and append-only activity log. The pilot reuses the existing
source registry and remains documentation-only; it does not add automation,
provider calls, plugins, personal data, or runtime changes. Existing `ideas/`
artifacts and unrelated worktree changes were preserved.

Task acceptance: the five requested wiki documents are present; claims in the
concept note link to F21–F25 and identify source locators; unknown/conflict and
independent-review handling are defined; the existing registry format is
reused; no external article was copied. Read-back confirmed all five wiki
Markdown files, the source additions, and this work-log entry. A link check
confirmed all local Markdown targets resolve; Python parsed the JSON registry
and confirmed unique IDs with F21–F25 present; `git diff --check` exited 0.
No tests are in scope or were run.

### LLM Wiki manual trial: unattended provider dispatch

The user approved the suggested one-question manual trial. The dedicated prompt
writer specified a docs-only task asking what must be done before unattended
provider dispatch. The primary agent inspected the current factory execution
record, Grok readiness note, routing-policy JSON, and blueprint proposal.

Added `research/llm_wiki/concepts/unattended-provider-dispatch.md`, linked it
from the wiki index, and narrowly updated the schema so local project records
can be cited by note-local IDs and repository-relative links without adding
them to the external source registry. The recommendation is to finish M1 with
a fake provider before considering one separately authorized M2 adapter trial.
The note separates current implementation facts from proposed gates, flags
authentication/entitlement and approved budget as unknown, and records a manual
traceability/usefulness assessment. Verification is pending. No tests, code,
provider calls, authentication, or inference were performed.

The changed wiki schema, index, answer note, and logs were read back. The
P01–P04 IDs are defined and cited, all local wiki/project-source links resolve,
and `research/sources.json` parses as JSON; no source entries were added for
this trial. `git diff --check` exited 0. No tests were run.

### M1 slice: deterministic fake provider, leases, and ledger restore

The next safe engineering step in the readiness note and the unattended-dispatch
wiki answer was M1 reliability work that does not call a provider. A dedicated
prompt-writing subagent authored the bounded prompt. It did not edit files. The
primary agent implemented that prompt only.

The slice adds a closed `fake_provider` task mode with scenarios `success`,
`incorrect`, `timeout`, and `interrupted`. It does not spawn a subprocess.
Acceptance is a `publish` gate that requires the current controller epoch, the
same attempt id and lease generation, and a still-reserved attempt while the
job is running or checking. An incorrect candidate can log
`fake-provider worker marker: SUCCESS` and still finish failed. An interruption
stays running, blocks another dispatch, and a mismatched publish changes
nothing. `replace_lease` supersedes the old generation. `backup` uses the
SQLite backup API. `restore` advances the epoch, keeps the lease high-water
from moving backward, supersedes reserved attempts, and invalidates a passed
fixture or fake-provider job whose candidate is missing or changed without
deleting the receipt. A pre-restore lease cannot publish.

This does not claim an OS sandbox, and it does not finish M1. F07 isolation
and any real provider adapter remain unstarted. The live factory database was
not opened or migrated by hand. New tables are created with
`CREATE TABLE IF NOT EXISTS` on the next ordinary open. The `jobs` table was
not altered. No login, network call, tmux change, or service restart was made.

Files edited for this slice: `overseer/factory.py`, `tests/test_factory.py`,
the next-work wording in `docs/FACTORY_EXECUTION.md`, and this log. Other dirty
worktree files were left as they were.

Final verification, after the restore test was tightened to read job state from
SQLite before `inspect`:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
```

Result: exit 0; 31 factory tests passed in 2.412 seconds.

```text
python3 scripts/check
```

Result: exit 0; 68 project tests passed in 4.405 seconds. Scheduler tests
printed their expected queue uncertainty and observation warning lines.
`git diff --check` exited 0. Independent review of this slice was requested
after these commands.

### Review correction: restore fencing must not rewind the live ledger

The fresh reviewer reproduced a fail-open restore. `backup()` copied into the
live database immediately, and the epoch bump, lease high-water, and attempt
supersede ran in a later transaction. A `passed` row whose spec was `NOTJSON`
made that later transaction raise `JSONDecodeError`. Rollback undid only the
fence, leaving the backup's epoch and lease counter in place. A pre-restore
reserved attempt could then `publish` a good candidate and become `passed`.
The existing restore test did not catch it because the fence committed and the
rejected publish had no candidate file.

Restore now copies the backup into a staging database, commits the fence there,
and only then installs that fenced snapshot into the live database with the
SQLite backup API. If fencing raises, the live epoch and lease counter stay as
they were. A prior snapshot is copied back if installing the staged ledger
fails. An unreadable passed specification invalidates that job instead of
aborting the fence. Receipts are still not deleted.

Corrective commands:

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
```

Both commands were run with `python3 -W error::ResourceWarning` so an unclosed
SQLite connection fails the run. Results: factory suite exit 0, 33 tests passed
in 2.185 seconds; full suite exit 0, 70 tests passed in 4.053 seconds.
Scheduler tests printed their expected queue warnings. `git diff --check`
exited 0. The two new cases are
`test_restore_fence_failure_keeps_the_live_lease_counter` and
`test_restore_invalid_spec_still_fences_the_previous_lease`. An injected
fencing failure keeps epoch 5 and high-water 9, and publish does not accept.
A planted `NOTJSON` passed row restores to epoch 6 with high-water at least 9,
invalidates that row, and does not accept the previous lease. No sandbox or
completed-M1 claim is added.

### F07 slice: bubblewrap boundary probe

The previous step stopped because its acceptance checks had passed. The user
asked why the work stopped, so the next blueprint item was started: F07
harmless boundary probes. This step was implemented directly from the blueprint
and a local bubblewrap measurement. A separate prompt writer was not used.

`isolation_probe` is a closed factory mode. It runs a controller-owned probe
under bubblewrap with a new user, mount, pid, and network namespace. The
disposable workspace is writable. Ledger, credential, and other-workspace files
are read-only. The host evidence directory is not mounted. The address-space
hard limit is 128 MiB. A second probe runs `sleep 30` and the controller kills
that process group after 3 seconds. Missing bubblewrap or prlimit fails closed.
The trusted argv command runner is unchanged and is still not a sandbox.

A local measurement before the implementation showed ledger, other-workspace,
and credential writes denied with errno 30, a connect to 192.0.2.1 denied with
errno 101, a 128 MiB address-space limit that could not be raised, and a 160 MiB
allocation denied. A CPU-time rlimit did not stop `sleep`, so the wall-clock
kill is the time control that is recorded. Disk quotas and process-count limits
were not demonstrated.

```text
python3 -m unittest tests.test_isolation -v
python3 scripts/check
```

Results: isolation tests exit 0, 4 tests passed in 3.092 seconds. Full suite
exit 0, 74 tests passed in 6.723 seconds. Scheduler tests printed their
expected queue warnings. `git diff --check` exited 0. The live probe checked
the protected host bytes after the run. No provider login, network service, or
tmux change was made.

### Report-driven continuation loop

The user defined the monitor's purpose: read each LLM output report, build the
next prompt from that report, submit it, and repeat. This step was implemented
directly from that request. A separate prompt-writing agent was not used.

The visible pane is scanned for the latest line that starts with
`OVERSEER_REPORT` and a JSON object. `status` `continue` with a nonempty
`objective` and `remaining` becomes one typed line of at most 1000 characters.
`done` and `needs_input`, a blank objective or remaining step, and an invalid
report withhold the send. A screen with no report still receives the configured
`reply`. Extra JSON keys are ignored. Report text is not written to the log or
the state file; a withheld screen stores only a fingerprint and a fixed reason.
Capacity retries still send the configured reply. Idle, cooldown, daily limit,
stop markers, and the sensitive-word guard are unchanged.

`config.json` `reply` now tells the client to print that report line. The
running user service re-reads config on each poll, so that instruction can be
sent by the process that is already running. The new parser is in the Python
modules and is not loaded by that process until `overseer.service` is
restarted. The service was left running: it was active as PID 1445361, started
Sun 2026-10-18 21:45:52 CDT. No restart was performed.

```text
python3 scripts/check
git diff --check
```

Results: full suite exit 0, 90 tests passed in 7.292 seconds. Scheduler tests
printed their expected queue warnings. `git diff --check` exited 0. No factory
database, provider login, or tmux session was changed.

### Standing rule: a finished step is reported, then work continues

Recorded for later sessions. After the fake-provider slice met its checks, work
stopped. The explanation of that stop was:

> I stopped because that fake-provider slice had met its checks, and the project
> rule is to end a finished step instead of starting the next milestone. The next
> open item is F07 isolation. I'll pick that up now.

The user wants that reason kept. It explains what happened. It is not the rule
for what happens next.

When a step is finished or a milestone is reached, report that result, including
what was checked and what is still open. The Overseer program then reads that
report and decides how to proceed. Meeting the checks for one slice does not end
the session. Work continues into the next authorized step.

### Harness framework document

The user added `agents.jpeg` to the project and chose to use it as the process
framework. The dedicated prompt-writing agent authored the bounded prompt for
this step; the primary agent executed it. No behavior changed.

Created `docs/HARNESS_FRAMEWORK.md`, the pillar map for the six harness pillars
(contract, context, state, tools, permissions, evidence) with the blueprint
section, the current `file:line`, an honest verdict, and the next increment for
each. It also records the process-order gap, the two unbridged systems, and
what the framework does not claim. Created `scripts/check-doc-references`, a
read-only reference checker for that file. Added one pointer each to
`AGENTS.md`, `README.md`, and `docs/FACTORY_EXECUTION.md`.

```text
python3 scripts/check
python3 scripts/check-doc-references
git diff --check
```

Results: full suite exit 0, 92 tests passed in 7.231 seconds. Reference
checker exit 0, 73 references checked. `git diff --check` exited 0. Baseline
sha256 over `overseer/*.py config.json overseer.service scripts/check
scripts/terminal-hub` is byte-identical before and after. The live tmux
server, the running service, `config.json`, and the private factory ledger
were not touched. Token usage and monetary cost were not supplied by the
runtime and remain unavailable.

### Live monitor restore: unwatch %0 and restart the service

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. The user authorized exactly two live mutations and rejected
code changes and any enrollment change. The service had been running
pre-fix code since 16:15:42, while `overseer/scheduler.py` was written at
16:18:18, so a dead reptyr target on pane %0 (PID 1174383 absent) failed the
whole FIFO tick on every poll and blocked every other pane.

```text
python3 -m overseer unwatch %0
systemctl --user restart overseer.service
```

Before: PID 2729896, started 16:15:42, 2808 total `queue observation failed`
lines, 765 since that start. After: PID 3266756, started 22:39:10, fresh
`monitor started; dry_run=False; poll=30s`, and 0 failures since the restart;
the total did not grow. `overseer status` now shows %0 OFF and %2, %3, %4
WATCHED. No `sent` or `queue enqueued` line appeared, so no pane received a
prompt: %2 and %4 are held by their stop markers and %3 by the `»` placeholder
check. Every tmux session, pane, reptyr bridge, and target PID is unchanged
apart from %0's `@overseer` value. `python3 scripts/check` still reports 92
tests passed and `git diff --check` is clean; `git status --porcelain` is
unchanged. No code, config, or documentation file was modified. Remaining
open work: the `»` composer placeholder is still unaccepted by
`Snapshot.ready`, and the stale-process fix is still uncommitted.

### Codex composer placeholder, committed working tree, service verification

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. `Snapshot.ready` now accepts the Codex `»` composer marker
alongside `>`, `❯`, and `›`, in both the bare-marker and the
`Ask Codex to do anything` placeholder forms, keeping the `cursor_x == 2`
guard. The working tree was committed as five ordered commits, and each commit
was verified green by running that commit's own snapshot through
`scripts/check`: 67, 92, 92, 92, and 93 tests. The `»` fix and its test
landed in the last commit.

```text
python3 scripts/check
systemctl --user restart overseer.service
```

Results: 93 tests passed in 7.457 seconds, `git diff --check` clean, `git
status --porcelain` clean after the commits, and the service restarted to PID
3274976 at 22:50:20 with 0 `queue observation failed` lines afterwards. The
`»` fix took effect: at 22:53:21 the monitor logged `queue enqueued %3 at
position 1` and at 22:53:22 `%3 dispatched from FIFO queue`, 181 seconds after
the restart, which is the configured idle threshold. The prompt was typed and
submitted; the transcript shows it as a submitted user message prefixed with
`›`, so the turn-boundary detection in `scheduler.response` is unaffected by
the `»` composer glyph. The `%3` client then returned
`The 'gpt-6-astra' model is not supported when using Codex with a ChatGPT
account.`, so that session cannot run its configured model, and the monitor
holds the FIFO reservation on `%3` and logged `queue holds %3: delivery or
completion remains unconfirmed; inspect this pane` at 22:55:22. Operator
action is required to release that reservation. No pane was enrolled,
unwatched, or messaged by hand.

### Release the held FIFO reservation on pane %3

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. The monitor had dispatched to `%3` after the `»` composer
fix, but that Codex client answered with a provider error, so no completion
marker appeared and the FIFO slot stayed held. One operator action released
it; no state file was edited.

```text
python3 -m overseer unwatch %3
```

Before: `Active reservation: %3:1236021:6100232` and a journal warning
`queue holds %3: delivery or completion remains unconfirmed; inspect this
pane`. After: the monitor's own poll cycle logged `queue releases vanished,
replaced, or excluded client %3:1236021:6100232` at 23:00:23, and
`python3 -m overseer status` shows `Active reservation: none`, `%3 OFF`, `%2`
and `%4` still WATCHED. No new `queue holds` or `queue observation failed`
lines appeared and the service was not restarted, so the same PID 3274976
kept polling. Every tmux session, pane PID, reptyr bridge, and target PID is
unchanged apart from %3's `@overseer` value. `python3 scripts/check` still
reports 93 tests passed.

Model finding, investigated read-only and not changed: the live `%3` session
is pinned to the older `gpt-6-astra` family (footer `GPT-6-Astra ultra`)
while `~/.codex/config.toml` now sets `model = "gpt-6-luna"` with
`model_reasoning_effort = "max"`, and `~/.codex/auth.json` has
`auth_mode: chatgpt`. The client rejected the turn with
`The 'gpt-6-astra' model is not supported when using Codex with a ChatGPT
account.`. Re-enabling `%3` needs the operator to switch that session to a
supported model or start a fresh session that inherits the current config,
then run `python3 -m overseer watch %3`. No Codex configuration, auth file,
client session, or pane content was changed. Remaining open work: `%0`'s
bridged client is still dead and unwatched, and the factory still has no real
provider adapter.

### Pause a pane on a model failure and add an operator model choice

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. A client that reports an unsupported model, exhausted
credits, or a failed login now pauses its pane instead of being retried or
given a substituted model, and the operator chooses a provider and model.

```text
python3 scripts/check
python3 scripts/check-doc-references
```

Added `overseer/modelchoice.py` (failure detection, the provider allowlist
read from `config.json`, and the pure picker-matching helpers), a
`model_blocked` phase in `overseer/scheduler.py` that releases the FIFO
reservation so one broken pane cannot starve the others, an `model-select`
command and a `status` section in `overseer/__main__.py`, a client model
picker driver in `overseer/tmux.py`, the `model_providers` and
`allowed_providers` keys in `config.json`, and `tests/test_model_choice.py`.
The suite grew from 93 to 105 tests, all passing, and the document reference
checker still resolves every citation. The permitted providers and their model
ids were verified locally with `codex debug models`, `claude --help`,
`opencode models`, and `~/.grok/models_cache.json`. The feature does not
substitute a model, does not retry a blocked pane, and cannot drive an
`opencode` or `grok` session because the monitor only watches `codex` and
`claude` clients.

### Credit fallback policy, OpenCode as a driven client, and the %3 route

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. `config.json` gained a `fallback_policy`: `primary` is the
paid tier, `zero_credit` is the tier that takes over when the paid credits are
gone, `excluded_models` names model ids that are offered nowhere, and
`exhausted_status` is the literal `CREDITS_EXHAUSTED_WAITING`. `gpt-6-luna` is
excluded, on the operator's stated judgment that it is not a coding model; that
is the operator's reason, not a measured result.

```text
python3 scripts/check
python3 scripts/check-doc-references
```

OpenCode is now a driven client. Its composer was measured directly from a
throwaway session that was started and killed again: the client is a bordered
box whose cursor row is `┃  <text>`, empty when the text is the `Ask anything`
placeholder, and its model row reads `┃  <agent> · <model>`. Added
`overseer/route.py` for moving work between clients, an OpenCode branch in
`Snapshot.ready`, the credit branch in `overseer/scheduler.py` that routes a
credit failure to the zero-credit tier once and pauses the failed pane, and the
`CREDITS_EXHAUSTED_WAITING` state for when that tier is exhausted too. A
routed pane stays paused and the new session receives the configured
continuation. The suite grew from 105 to 110 tests, all passing, and the
document reference checker resolves all 83 citations. The six migrated
sessions and their clients were not touched.

The operator's answer for `%3` was applied: `python3 -m overseer model-select %3
--provider opencode` created the session
`overseer-crypto-cooking-1236021-opencode` (pane `%7`) in
`/home/kali/Projects/Crypto-Cooking`, enrolled it, and left `%3` watched,
paused, and otherwise untouched. The monitor sent the new session the
configured continuation 181 seconds after the route, and the OpenCode session
began the work on its own default model, `MiniMax M3.1 Flash Free OpenCode`.

### Repair the model picker driver, switch %4, and clear the Codex default

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. The Codex picker has two steps: a model list and then a
reasoning level with a scope choice, where `s` applies the change to the
session only. The driver in `overseer/tmux.py` typed the command but never
opened the picker, and it matched entries over the whole screen, so a
conversation line could be taken for the highlighted entry.

```text
python3 scripts/check
python3 scripts/check-doc-references
```

The driver now opens the picker, searches only the block between the picker's
own header and footer, navigates in either direction, applies the change to
the session, and verifies the composer footer. It escapes and clears the
composer when the model is not offered, and it never selects a different
model. The pure helpers for the picker block, the reasoning screen, and the
navigation count are in `overseer/modelchoice.py` with tests. The suite grew
from 110 to 115 tests, all passing, and the document reference checker
resolves all 83 citations.

Pane `%2` was switched to `gpt-5.6-terra medium` for the session only. Pane
`%4` was switched the same way through the repaired driver: its footer changed
from `GPT-6-Astra medium` to `GPT-5.6-Terra medium`, its `OVERSEER_NEEDS_INPUT`
marker and its conversation are intact, and no work was restarted. Neither
pane was routed, because a route would have discarded the conversation.

The Codex default was cleared as well. `~/.codex/config.toml` was backed up to
`~/.codex/config.toml.backup-20261020T052519Z`, byte-identical to the
original, and only the `model` value changed, from `gpt-6-luna` to
`gpt-5.6-terra`; `codex doctor` now reports `model gpt-5.6-terra · openai`.
Running sessions keep their own model until they are switched, so this
changes the default for new sessions only.

### OpenCode turn completion and phase detection

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. The monitor's phase detection was written for the Codex
terminal, so an OpenCode turn was never recognized: the running footer says
`esc interrupt`, not `esc to interrupt`, and OpenCode has no `Worked for`
footer to mark a finished turn. A running OpenCode turn therefore read as
idle, and a finished one would never have released the queue reservation.

The two OpenCode turn states were measured from the live session. While a
turn runs, the footer shows `esc interrupt` and the hint about moving running
work to the background, and the composer box is blank with the cursor on a
border row. When the turn ends, the composer shows its idle
`Ask anything…` placeholder again. A blank border row is a turn using the
box, not an empty composer, so the readiness check now accepts only the
placeholder.

```text
python3 scripts/check
python3 scripts/check-doc-references
```

The running marker makes a running OpenCode pane active, the idle placeholder
makes a finished turn finished, and OpenCode draws no user-message boundary,
so the tail of its screen is its current answer. A pane that was observed
running is eligible for the next continuation once it finishes, and the queue
reservation is released. The suite grew from 115 to 119 tests, all passing,
and the document reference checker resolves all 87 citations. The live OpenCode
session was still running its turn throughout this change.

The live check confirmed the fix, and corrected it. The first pass assumed
that a finished OpenCode turn restores the `Ask anything…` placeholder; the
live session showed that it does not. A finished turn leaves the composer box
blank, and the placeholder only appears in a fresh session, so the readiness
rule accepts a blank box as an empty composer and the running marker is what
separates a running turn from a finished one.

The routed session `%7` then released its reservation on the first poll after
the service restart:

```text
Oct 20 01:11:48 INFO queue releases %7: stopped
```

The OpenCode turn ended with `OVERSEER_NEEDS_INPUT`, so the pane is now held
by the stop marker and waits for the operator. The turn itself ran 50m 41s
with about 110 tool calls and four delegated agents.

### The contract block: the missing REQUEST inputs become spec fields

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. The increment is filed against exactly one pillar row, the
CONTRACT row of `docs/HARNESS_FRAMEWORK.md`. The previous step had closed the
OpenCode client gap in the monitor and named what was still open: a Grok
session remains undrivable, the factory still has no real provider adapter,
and `%7` waits on the operator. The Grok client gap needs a live Grok turn to
measure and the account reports `Weekly limit left: 0%`, and a provider
adapter is a separate, externally gated milestone, so this step took the
factory's CONTRACT row, whose next increment was already named in the project.

The increment adds an optional `contract` block to the command-mode task
spec. It is closed: exactly eleven keys, `role`, `risk_tier`,
`external_effects`, `protected_paths`, `approval_requirements`,
`acceptance_ids`, `required_capabilities`, `project_constraints`,
`measured_evidence`, `provider_availability`, and `budget`. A missing key, an
unknown key, a wrong type, an out-of-range value, a protected path that leaves
the workspace, and acceptance identifiers that do not match the submitted
acceptance commands are all rejected with a message that names the field.
`acceptance_ids` are labels for the commands that were already submitted; they
add, remove, reorder, and alter nothing, and the controller-owned verifier
identities and the acceptance path are untouched. The three controller-owned
modes (`fixture`, `fake_provider`, `isolation_probe`) keep their exact closed
field sets and still reject a `contract` key.

The block is recorded, never enforced. Nothing acts on a declared risk tier,
protected path, approval requirement, or budget. The protected-path check is a
lexical shape check on a declaration, not a write guard, and the runner still
executes trusted local commands with the user's own privileges.

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
python3 scripts/check-doc-references
git diff --check
```

Results, copied from the run: the factory suite ran 46 tests in 2.914 seconds,
OK; the full suite ran 132 tests in 13.666 seconds, OK; the document reference
checker reported `91 references checked in HARNESS_FRAMEWORK.md`; `git diff
--check` exited 0. The factory suite grew from 33 to 46 tests. Token usage and
monetary cost were not supplied by the runtime and remain unavailable.

Files changed: `overseer/factory.py` (the contract constants, the validation
helpers, the contract validation, the command-mode allowed key set, the
`REQUEST_INPUT_FIELDS` map, and the contract in the inspect result),
`tests/test_factory.py` (a new `ContractTests` class), `factory/routing-policy.json`
(the `status` string only), `docs/HARNESS_FRAMEWORK.md` (the CONTRACT row, the
REQUEST paragraph, the PERMISSIONS clause, and the claims list), `README.md`
(one paragraph on the optional block), and this log.

The optional-versus-mandatory decision was the writer's, and it was kept:
`docs/FACTORY_EXECUTION.md` documents the repository example task as
idempotently re-submittable, and neither that file nor the example task is in
this increment's scope, so a mandatory block would falsify a documented
statement. A command-mode spec without a contract is still valid, still
submittable, and still runs; `inspect` reports `contract` as `None` for it.
Making the block mandatory is the recorded next increment for the row.

Disagreements between the blueprint, the routing policy, and the code, kept
visible rather than smoothed over:

- The policy's nine `required_inputs` are inputs to a routing decision, not
  all authored task fields. `task_id` and `spec_hash` are facts of the stored
  task, and `spec_hash` is derived, not submitted. `measured_evidence` and
  `provider_availability` are environment observations; the contract can only
  hold submitter declarations of them, and no code reads them. The mapping is
  in code as `REQUEST_INPUT_FIELDS` `overseer/factory.py:80`, and the test
  suite reads the real policy file to prove the two agree.
- The policy's `required_decision_fields` have no code counterpart. Provider,
  model, reasoning effort, rationale, evidence IDs, fallback, and stop
  condition are the router's fields, and no router exists. That is named as
  remaining work.
- The blueprint's minimum task fields are not covered by one increment. This
  step covers the Risk and Budget groups and the policy's input names. The
  Dependency group, the Execution group's provider, model, and adapter
  identity, and the Result group's candidate revision and acceptance decision
  are out of scope.
- The routing policy file's `status` is now
  `required_inputs_have_validated_code_counterparts_no_runtime_router`. It is
  still a proposal: the test suite reads the file, no runtime code reads it,
  and no router enforces its decisions. `docs/HARNESS_FRAMEWORK.md` says
  exactly that, and the former sentence that no code reads either that file
  or `factory/skills-provenance.json` was corrected: the provenance file is
  read by no code at all.

The CONTRACT verdict now records that the factory contract carries the missing
REQUEST inputs as a validated optional block, that those statements are
recorded and not enforced, and that the monitor's request contract is still
one free-text string. That monitor-side gap is unchanged and is recorded as a
separate open item rather than dropped. Every line citation in the pillar map
was re-read by content after the edit, because the reference checker proves
only that a path exists and a line is in range. The PERMISSIONS row was
corrected for factual accuracy only; its verdict and next increment are
unchanged.

Not touched: the live tmux server and every pane, the running monitor service
(still PID 3550026, not restarted), the live factory ledger at
`~/.local/state/overseer/factory` (its `jobs.sqlite3` still carries its
2026-10-19 22:34:24 timestamp), `config.json`, and the monitor's own modules.

### Review correction: three contract rejections raised TypeError, not ValueError

The review of the contract increment found one real defect, and the dedicated
prompt-writing agent authored the corrective prompt while the primary agent
executed it. The contract schema, its bounds, the `REQUEST_INPUT_FIELDS` map,
the routing-policy `status` string, and the pillar verdicts are unchanged.

The defect was in the rejection path, not the accepted values. Three checks
tested membership or uniqueness before they tested the type, so an unhashable
value escaped as a `TypeError` instead of the `ValueError` the increment
promised. `overseer/factory.py:213` and `overseer/factory.py:215` tested
`contract['role']` and `contract['risk_tier']` against their closed sets, and
`overseer/factory.py:228` built a `set()` of the acceptance identifiers before
checking that they were strings. Reproduced against a temporary database:

```text
role -> TypeError : cannot use 'list' as a set element (unhashable type: 'list')
risk_tier -> TypeError : cannot use 'dict' as a set element (unhashable type: 'dict')
acceptance_ids -> TypeError : cannot use 'list' as a set element (unhashable type: 'list')
```

It mattered because `main()` catches only `(ValueError, OSError, RuntimeError,
sqlite3.Error)`, so an invalid task printed a Python traceback instead of the
runner's `{"error": ...}` object. The role and risk tier checks now test the
type before the membership test, and the acceptance identifiers are checked
for the identifier pattern before the uniqueness check. The accepted values,
the count rule, the uniqueness rule, and the eleven-key closed set are exactly
as they were.

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
python3 scripts/check-doc-references
git diff --check
```

Results, copied from the final run: the factory suite ran 48 tests in 2.738
seconds, OK; the full suite ran 134 tests in 13.721 seconds, OK; the document
reference checker reported `91 references checked in HARNESS_FRAMEWORK.md`;
`git diff --check` exited 0. The factory suite grew from 46 to 48 tests: one
case for the unhashable values, and one that runs the runner's own command
line against a temporary database and asserts the JSON error object, the exit
code 1, and no traceback on stderr. Token usage and monetary cost were not
supplied by the runtime and remain unavailable.

Files changed: `overseer/factory.py` (three rejection paths), `tests/test_factory.py`
(two tests), `README.md` (the field enumeration now names all eleven keys),
and this log. `docs/HARNESS_FRAMEWORK.md` needed no re-citation: the fix
changed the conditions in place and moved no line, and every cited line was
re-read by content afterwards. The live tmux server, every pane, the running
monitor service, the live factory ledger, `config.json`,
`docs/FACTORY_EXECUTION.md`, and `factory/tasks/overseer-checks.json` were not
touched.

A few citations in the pillar map point at blank lines
(`overseer/__main__.py:17`, `overseer/__main__.py:21`, `overseer/__main__.py:270`,
`overseer/modelchoice.py:292`, `docs/FACTORY_EXECUTION.md:97`). They predate
this increment, they were not touched here, and they remain as a separate
housekeeping item.

### The capability envelope, the awaiting-approval state, and the decision record

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. The increment is filed against exactly one pillar row, the
PERMISSIONS row of `docs/HARNESS_FRAMEWORK.md`, whose next increment named
exactly this step: carry an envelope mode on the task spec with an
awaiting-approval state and an approval record in the ledger.

A command-mode task may now carry an optional `envelope` block with exactly
four keys: `mode`, one of the blueprint's four capability modes
(`investigation`, `draft_change`, `bounded_maintenance`, `release`);
`scope`, one to sixteen entries of text; `requires_decision`, a real boolean;
and `decider`, the name the submitter says may decide. Every rejection is a
`ValueError` whose message names the offending field, unhashable values
included, so the runner's command line keeps its `{"error": ...}` contract
instead of printing a traceback.

The mode, the scope, and the decider identity are recorded, never enforced.
There is no roster check, no scope check, and no policy engine: the code does
not compare what the commands do with the declared scope, and the recorded
decider is free text compared with nothing. The one enforced part is the gate.
A task whose envelope declares that a fresh decision is required is submitted
into the new durable state `awaiting_approval` and is not dispatched. It does
not create an evidence directory, does not start a child process, and does
not touch the workspace. A grant moves it to `queued`; a refusal moves it to
the terminal state `refused`. The decision is written to a new `approvals`
ledger table and to the event log, and the grant is written in the same
transaction as the state change, so a crash cannot leave a task queued
without a recorded decision. `run_one` re-checks the gate before dispatch and
puts a task back to `awaiting_approval` if a grant is missing, so the gate
holds under a crash as well.

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
python3 scripts/check-doc-references
git diff --check
```

Results, copied from the final run: the factory suite ran 64 tests in 4.014
seconds, OK; the full suite ran 150 tests in 15.059 seconds, OK; the document
reference checker reported `97 references checked in HARNESS_FRAMEWORK.md`;
`git diff --check` exited 0. The factory suite grew from 48 to 64 tests.
Token usage and monetary cost were not supplied by the runtime and remain
unavailable.

Files changed: `overseer/factory.py` (the envelope constants, the envelope
validation, the envelope in the command-mode key set, the `approvals` table in
both schema scripts, the awaiting-approval submission, the `decide` method, the
decision in the inspect result, the cancel path for a waiting task, the
dispatch gate in `run_one`, the `decide` subcommand, and the decision column
in `status`), `tests/test_factory.py` (a new `EnvelopeTests` class),
`docs/HARNESS_FRAMEWORK.md` (the PERMISSIONS row, the process-order prose,
two claims bullets, and every re-cited line), `README.md` (the envelope, the
state, and the `decide` command), and this log.

Acceptance checks and the test that proves each one:

1. a valid envelope is accepted, recorded, and written into the run evidence
   — `test_valid_envelope_is_accepted_and_recorded`
2. strict field validation, including the missing and unknown key cases —
   `test_envelope_field_validation_is_strict`
3. unhashable values are `ValueError`, never `TypeError` —
   `test_unhashable_envelope_values_are_validation_errors`
4. `requires_decision` accepts only real booleans —
   `test_requires_decision_accepts_only_real_booleans`
5. the three controller-owned modes still reject the block and keep their
   exact key sets — `test_controller_modes_reject_an_envelope_and_keep_their_key_sets`
6. the envelope is covered by the frozen spec hash —
   `test_envelope_is_covered_by_the_frozen_spec_hash`
7. a waiting task is not dispatched and creates no evidence —
   `test_a_waiting_task_is_not_dispatched`
8. a waiting task does not starve queued work —
   `test_a_waiting_task_does_not_starve_queued_work`
9. a grant queues the task and records the decider, the decision, the time,
   the note, and the spec hash —
   `test_a_grant_queues_the_task_and_records_the_decider`
10. a refusal is terminal and records no run —
    `test_a_refusal_is_terminal_and_records_no_run`
11. the fail-closed cases: unknown task, invalid decision word, empty decider,
    a second decision, and a decision on a live task —
    `test_decisions_fail_closed`
12. a decider that differs from the envelope's decider is accepted and both
    names are visible — `test_the_decider_identity_is_recorded_not_authorized`
13. the decision survives a backup and restore round trip —
    `test_the_decision_survives_a_backup_and_restore`
14. cancelling a waiting task records that nothing ran and records no approval
    — `test_cancelling_a_waiting_task_records_that_nothing_ran`
15. dispatch is refused without a recorded grant, even if the state was forced
    — `test_dispatch_is_refused_without_a_recorded_grant`
16. the `decide` command line prints JSON, exits 1 with `{"error": ...}` and
    no traceback for an unknown task, and the `status` rows carry the
    decision — `test_the_decide_command_reports_errors_as_json`
17. `inspect` carries the envelope and the approval record —
    `test_valid_envelope_is_accepted_and_recorded` and
    `test_the_decider_identity_is_recorded_not_authorized`

Disagreements between the blueprint, the routing policy, and the code, kept
visible rather than smoothed over:

- The blueprint's envelope table gives each mode an authority boundary. The
  code records the mode name and the scope text and enforces neither. The
  gate is the only enforced part.
- The blueprint asks for a fresh decision only when the action exceeds the
  envelope, materially changes the product, or needs a delegation that was
  not granted. That is a comparison between the action and the envelope, and
  the code cannot make it, so the submitter's `requires_decision` flag is the
  only trigger.
- `factory/routing-policy.json` names
  `approval_owner: factory_director_within_ceo_delegation`. No runtime code
  reads that file and the recorded decider is free text, so no delegation is
  checked.
- The blueprint asks for pause-dispatch, inspect, cancel, reconcile,
  retry-with-reason, and rollback controls. The factory now has a
  pre-dispatch wait, inspect, cancel, reconcile, and the backup and restore
  pair. It has no operator pause of running work and no retry-with-reason
  path.
- `docs/FACTORY_EXECUTION.md` documents the runner's command surface and does
  not mention `decide`. That file is outside this increment's scope, so the
  drift is recorded here as work for a later increment.

Four prose edits in `docs/HARNESS_FRAMEWORK.md` were needed once the gate
existed, and each is recorded here with its before and after:

1. The process-order paragraph said "There is still no general permission
   envelope, so the stage that decides what the model sees is missing and the
   stage that decides what it may do covers one failure class only." It now
   says that the factory carries a recorded capability envelope, that a task
   which declares it needs a fresh decision waits in `awaiting_approval` until
   a decision naming the decider is recorded, that the envelope's scope and
   decider identity are recorded and not authorized, that the stage that
   decides what the model sees is still missing, and that there is no operator
   pause of running work.
2. The contract-block claims bullet ended with "and there is no approver
   identity and no approval gate." That clause was removed, because the
   factory now has one approval gate, and the bullet keeps the contract
   block's own honest limit: the block records declared risk, protected paths,
   approval requirements, and budget limits and enforces none of them.
3. A new claims bullet was added for the envelope: "The envelope block
   records a capability mode, a declared scope, and a decider name; it
   authorizes none of them. The only enforced part is the gate: a task that
   declares it needs a decision is not dispatched until a decision is
   recorded, and the recorded decider is compared with no roster."
4. The claims bullet "There is no approval gate and no approver identity" was
   replaced by "The factory has one pre-dispatch approval gate and one
   operator approval gate in the monitor. There is no approver identity
   check, no enforced scope, no policy engine, no operator pause of running
   work, and no retry-with-reason path."

Every other pillar row, including the CONTRACT row and its sentence that the
monitor's request contract is still one free-text string, kept its verdict and
its next-increment text; only their citations were re-pointed. Every
`path:line` citation in the file was re-cited to the line that now holds the
claimed content and re-read by content, because the reference checker proves
only that a path exists and a line is in range.

Not touched: the live tmux server and every pane, the running monitor service
(still PID 3550026, not restarted), the live factory ledger at
`~/.local/state/overseer/factory`, `config.json`, the monitor's own modules,
`docs/FACTORY_EXECUTION.md`, `factory/tasks/overseer-checks.json`, and
`factory/routing-policy.json`.

### Review correction: five defects in the envelope increment

The review of the envelope increment found five defects, the dedicated
prompt-writing agent authored the corrective prompt, and the primary agent
executed it. The envelope schema, the four modes, the bounds, the `approvals`
table shape, the `decide` method's fail-closed set, the `decide` command line,
the `status` shape, the state vocabulary, and the dispatch re-check are all
unchanged.

The first defect was a safety regression in `cancel()`. The method read the
job's state and then wrote `state='cancelled'` without a guard, so a task that
started running between the read and the write was silently overwritten with
`cancelled` while its child process might still be alive. It was reproduced
deterministically with a competing writer:

```text
cancel returned; state is now: cancelled (DEFECT: the guard was lost)
```

The state change is now one statement guarded by the state that was observed,
`UPDATE jobs SET state='cancelled' WHERE id=? AND state=?`, and a row count of
zero raises the same refusal. A test now installs a trace callback that
competes the write at the moment the cancel's update runs, and asserts that
the cancel is refused, that the state is still `running`, and that no
`cancelled` event was written.

The second defect was a stale job detail. `decide()` changed the state but
left the row's detail saying the task was waiting for a decision, and the
refusal's "dispatched no command, recorded no external effect" wording lived
only in the event log, so the operator-facing `status` output contradicted the
state. The decision now writes the state and its detail in the same
transaction: a grant says the decision was granted, names the decider and the
envelope mode, and says the task is queued for dispatch; a refusal says the
decision was refused, names the decider and the envelope mode, and says that
the runner dispatched no command, started no child process, and recorded no
external effect for that task.

The third defect was an untested branch. A task whose envelope declares
`requires_decision: false` was accepted but nothing proved it behaves as
before. A test now submits one, asserts the state is `queued` rather than
`awaiting_approval`, runs it, and asserts it passes with the marker file
written and no approval record.

The fourth defect was an incomplete inventory of the prose edits, which is
corrected in the entry above with the before and after of each of the four
edits.

The fifth defect was a citation that did not hold what its cell claimed: the
PERMISSIONS row cited `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:541` for the
envelope modes, and that line holds the capability-envelope sentence, while
the mode table starts at line 543. The citation now points at the table.

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
python3 scripts/check-doc-references
git diff --check
```

Results, copied from the run: the factory suite ran 68 tests in 10.014
seconds, OK; the full suite ran 154 tests in 22.400 seconds, OK; the document
reference checker reported `97 references checked in HARNESS_FRAMEWORK.md`;
`git diff --check` exited 0. The factory suite grew from 64 to 68 tests.
Token usage and monetary cost were not supplied by the runtime and remain
unavailable.

### The operator moved the project tree, and the monitor was repaired

Mid-increment the operator moved `/home/kali/Projects` to
`/home/kali/Programming/Projects`. The move was not announced, and it broke
the running monitor: the user service's working directory still pointed at
the old path, so every cycle failed.

```text
Oct 20 02:06:01 kali python3[3550026]: WARNING monitor cycle: [Errno 2] No such file or directory: '/home/kali/Projects/Overseer/config.json'
Oct 20 02:06:31 kali python3[3550026]: WARNING monitor cycle: [Errno 2] No such file or directory: '/home/kali/Projects/Overseer/config.json'
```

The repair was done immediately, because a monitor that fails every cycle
sends no continuations at all. The unit's working directory is now
`%h/Programming/Projects/Overseer` in both `overseer.service` and the
installed `~/.config/systemd/user/overseer.service`, the unit was reloaded,
and the service was restarted. It came back as PID 3709508 at 02:08:49 with a
fresh `monitor started; dry_run=False; poll=30s` line and no further cycle
failures, and `python3 -m overseer status` again lists the watched panes.

The path references the move broke were repaired in the same pass:

- `config.json` `reply` pointed the sessions at
  `/home/kali/Projects/AGENTS.md` and
  `/home/kali/Projects/coder_optimization/docs/PLAYBOOK.md`. Both now name
  the new location, so an automatic continuation tells a session to read files
  that exist.
- `AGENTS.md` pointed at the shared workflow file, and
  `docs/FACTORY_EXECUTION.md` told the reader to `cd` into the old path.
  Both were updated.
- `factory/tasks/overseer-checks.json` named the old workspace, which no
  longer exists, so the example task could not be submitted again. Its
  workspace was updated and its ID was changed to
  `overseer-foundation-checks-002`: the earlier `overseer-foundation-checks-001`
  record keeps its original specification and its acceptance in the live
  ledger, and a new ID keeps the documented idempotent re-submission working.
  `docs/FACTORY_EXECUTION.md` was updated to match.
- The shared workflow file `/home/kali/Programming/Projects/AGENTS.md` and the
  nine other `AGENTS.md` files under the moved tree still named
  `/home/kali/Projects/AGENTS.md`. Each reference was changed to the new
  location. These files are outside this repository; only the path changed,
  no instruction text was altered, and each file's change is visible in its
  own repository's status.

The historical records were left alone: `WORK_LOG.md`, `DEVTOOLS_INSTALL_RESULT.md`,
`GROK_INSTALL_NEXT_PROMPT.md`, `MODEL_DECISION_NEXT_PROMPT.md`, and the
`artifacts/` directory describe what happened at the old path and are not
rewritten.

The live tmux panes were not touched. Their clients keep running: the moved
directories travelled with the running processes, and the panes now report
`/home/kali/Programming/Projects/...` as their current path. The live factory
ledger was not opened: it was copied to a temporary directory and queried
there, and its `jobs.sqlite3` still carries its 2026-10-19 22:34:24 timestamp.

### Review correction: the last two documentation gaps

The review of the correction commit found the five corrections complete and two
documentation gaps left by the move repair. The dedicated prompt-writing agent
authored this corrective prompt and the primary agent executed it. No code,
test, schema, service, ledger, or pane was touched.

The first gap was `README.md`, which still named the old path in three places
after the move: the `cd` line in the "Try it" block at line 103, the `cd` line
in the "run it manually" block at line 119, and the sentence at line 127 that
says the included reply tells the client to follow
`/home/kali/Projects/AGENTS.md`. The last one contradicted the repaired
`config.json`, whose reply now names the new path. All three now name
`/home/kali/Programming/Projects/...`, each path was checked to exist with
`ls -d`, and `grep -n "/home/kali/Projects" README.md` now returns nothing.
Only the paths changed; the surrounding sentences and code fences are
byte-identical.

The second gap was eight citations in `docs/HARNESS_FRAMEWORK.md` that did not
hold the content they claimed. Three pointed into `docs/FACTORY_EXECUTION.md`,
which grew by three lines when the example task moved, and four pointed at
blank lines, which the log had already recorded as a separate housekeeping
item. All eight now point at the line that holds the claim, and each was
re-read by content:

- the provider-adapter claim now cites `docs/FACTORY_EXECUTION.md:141`,
  "sandbox, and it does not by itself finish M1. No real provider adapter,"
- the bubblewrap-is-not-a-sandbox claim now cites
  `docs/FACTORY_EXECUTION.md:140`, "command. Passing that probe does not make
  the trusted argv command runner a"
- the no-agent-traces claim now cites `docs/FACTORY_EXECUTION.md:116`,
  "separate from this local runner; no provider-wide concurrency claim is
  made."
- the monitor state file now cites `overseer/__main__.py:19`,
  `STATE = Path.home() / ".local/state/overseer/state.json"`
- the atomic save now cites `overseer/__main__.py:23`, `def save(path, state):`,
  which writes a temporary file, fsyncs it, and replaces the target
- the single-writer lock now cites `overseer/__main__.py:256`,
  `fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)`
- the monitor command surface now cites `overseer/__main__.py:291`,
  `def main():`
- the OpenCode running marker now cites `overseer/modelchoice.py:293`,
  `def running_marker(text):`

No pillar row's verdict, next increment, or surrounding prose changed; the
diff on that file is citation strings only.

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
python3 scripts/check-doc-references
git diff --check
```

Results, copied from the run: the factory suite ran 68 tests, OK; the full
suite ran 154 tests, OK; the document reference checker reported `97
references checked in HARNESS_FRAMEWORK.md`; `git diff --check` exited 0. No
test was added or changed, because the change is documentation only. Token
usage and monetary cost were not supplied by the runtime and remain
unavailable.

### The context manifest and the four memory record kinds

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. The increment is filed against exactly one pillar row, the
CONTEXT row of `docs/HARNESS_FRAMEWORK.md`, whose next increment named
exactly this step: write a context manifest per attempt into the run evidence
directory and introduce the blueprint's memory record kinds beside it.

Every completed attempt now writes a `context.json` manifest into its run
evidence directory, next to `task.json`, `results.json`, and `summary.json`.
The manifest has a closed field set: the version, the job, run, and attempt
identity, the spec hash, the mode, the objective, the workspace, the
repository identity, the acceptance identifiers and where they came from, the
commands that were actually launched with their exit codes and timeouts, the
environment facts the runner already holds, the supplied list, the memory
summary, and the unmeasured list. The manifest records what the controller
supplied and why. It holds no terminal history, no conversation text, no
command output, no source excerpt, and no number the controller did not
measure: tokens and cost stay null and are named as unmeasured.

The repository identity is observed read-only, with argument vectors and a
short timeout, and any failure falls to an honest marker that names the real
cause: the workspace is not inside a Git working tree, git is not available,
or git failed. No commit, root, or branch is ever invented.

The four memory kinds are stored in a new `memory_records` ledger table,
created in both places the other tables are created so a ledger from before
this increment still opens and still restores. A verified fact must bind to a
revision and an environment and reads back as verified and current; a decision
must name an owner and a reason, may name a superseding decision, and reads
back with the reverse link and with `current` false once it is superseded; a
hypothesis is stored unverified and cannot be marked verified; a historical
attempt is preserved as a result and never as current state. Every record
carries a source, a timestamp, an affected component, and an invalidation
condition.

These records are stored and queryable, and nothing reads them. No code path
consults a memory record when it prepares an attempt, dispatches a task, or
accepts a result, and the manifest says so in its own memory summary. The
increment adds the record, not the intelligence.

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
python3 scripts/check-doc-references
git diff --check
```

Results, copied from the run: the factory suite ran 86 tests in 12.123
seconds, OK; the full suite ran 172 tests in 23.691 seconds, OK; the document
reference checker reported `109 references checked in HARNESS_FRAMEWORK.md`;
`git diff --check` exited 0. The factory suite grew from 68 to 86 tests. The
only lines removed from `tests/test_factory.py` are the two lines of the
import block, which was extended with the new names; no existing test was
weakened, skipped, deleted, or renamed. Token usage and monetary cost were
not supplied by the runtime and remain unavailable.

Files changed: `overseer/factory.py` (the memory kinds constant, the
`memory_records` table in both schema scripts, the `record_memory` and
`memory` methods, the memory key in the inspect result, the read-only git
probe, the context manifest builder, and the manifest write with its ledger
event and digest), `tests/test_factory.py` (a new `ContextTests` class),
`docs/HARNESS_FRAMEWORK.md` (the CONTEXT row, the two STATE clauses that
became false, one claims bullet, one process-order clause, and every
re-cited line), `README.md` (one paragraph), and this log.

Acceptance checks and the test that proves each one:

1. a manifest is written into the run evidence directory —
   `test_a_context_manifest_is_written_into_the_run_evidence_directory`
2. the manifest names the objective, the spec hash, the job, the run, and the
   mode — `test_the_context_manifest_names_the_objective_and_the_spec_hash`
3. the manifest lists the commands actually run, and for a failing run only
   the commands up to the failure —
   `test_the_context_manifest_lists_the_commands_actually_run`
4. a workspace that is not a repository is marked honestly, with the real
   cause and no root and no commit, and the git-not-available cause is
   covered — `test_the_context_manifest_marks_a_non_repository_workspace_honestly`
5. a workspace inside a Git repository names the root and the base commit —
   `test_the_context_manifest_names_the_repository_root_and_base_commit`
6. the acceptance identifiers come from the contract block, or are absent —
   `test_the_context_manifest_records_the_contract_acceptance_ids`
7. the supplied list holds the six blueprint context items in order, and says
   why an item was not available —
   `test_the_context_manifest_records_what_it_supplied_and_why`
8. unmeasured values stay unmeasured and no output is carried —
   `test_the_context_manifest_marks_unmeasured_values_as_unmeasured`
9. all four kinds are stored and read back per job and per kind —
   `test_memory_records_of_the_four_kinds_are_stored_and_queryable`
10. a hypothesis reads back unverified and uncurrent —
    `test_a_hypothesis_is_stored_and_read_back_as_unverified`
11. a decision names its superseding decision and is superseded in return —
    `test_a_decision_can_name_a_superseding_decision`
12. every record carries its source, timestamp, component, and invalidation
    condition — `test_every_memory_record_carries_its_source_timestamp_component_and_invalidation`
13. a verified fact must bind to a revision and an environment —
    `test_a_verified_fact_must_bind_to_a_revision_and_an_environment`
14. unknown kinds, unknown jobs, empty text, and a bad supersedes are
    rejected — `test_memory_record_validation_rejects_bad_input`
15. the ledger records the manifest path and digest, and the summary carries
    the same pair — `test_the_ledger_records_the_manifest_path_and_digest`
16. the manifest and the memory records survive a backup and restore —
    `test_the_manifest_and_memory_records_survive_a_backup_and_restore`
17. the acceptance path, the lease rules, the restore fence, and the approval
    gate still pass —
    `test_the_existing_acceptance_lease_restore_and_approval_paths_still_pass`
18. a ledger without the memory table opens and restores —
    `test_a_ledger_without_the_memory_table_opens_and_restores`

Disagreements and limits, kept visible:

- The blueprint's section 13 describes a context builder and a handoff list
  that includes recent verified failures, applicable decisions, and remaining
  budget. This controller can observe only part of that. The manifest records
  the objective, the repository identity, the acceptance identifiers, the
  commands actually run, and the environment facts the runner already holds;
  the rest is named as unmeasured, and the supplied list says plainly that no
  context builder exists.
- The blueprint binds a verified fact to a revision and an environment. The
  ledger enforces that binding, and the record names both, but the runner
  still measures no environment digest and no cost.
- The blueprint's handoff list expects a candidate revision and an acceptance
  decision. The factory's candidate revision is not observable in this
  increment, so it is named as unmeasured.
- Restore replaces the ledger with the backup wholesale, so a memory record
  written after a backup is lost. That is the existing restore semantics, not
  a defect of this increment, and the durability test asserts the state that
  existed before the backup.

The STATE row needed two corrections, because the increment made them false:
its verdict said "recall and memory are absent", and memory records now exist
in the ledger although recall is still absent because nothing reads them, and
its next-increment cell named the CONTEXT increment that this step completes.
Both clauses were corrected to the minimum truthful wording and the rest of
the row is unchanged. The CONTRACT, TOOLS, PERMISSIONS, and EVIDENCE rows kept
their verdicts and next-increment text; only their citations moved. Every
`path:line` citation in the file was re-cited and re-read by content, and the
reference checker reports 109 references checked.

Not touched: the live tmux server and every pane, the running monitor service,
the live factory ledger, `config.json`, the monitor's own modules,
`docs/FACTORY_EXECUTION.md`, `factory/tasks/overseer-checks.json`, and
`factory/routing-policy.json`.

### Review correction: one citation that did not hold its claim

The review of the context increment found one defect and several minor
observations. The dedicated prompt-writing agent authored the corrective
prompt and the primary agent executed it.

The defect was in the STATE row of `docs/HARNESS_FRAMEWORK.md`: it cited
`overseer/factory.py:425` for the memory records table, and that line is the
approvals table. The memory records table is created at
`overseer/factory.py:429` and at `overseer/factory.py:1467`, which is what the
CONTEXT row already cited. The STATE row now cites `429`. The PERMISSIONS
row's citation of `425` for the approvals table is unchanged and still
resolves to that table. The reference checker did not catch this because it
proves only that a path exists and a line is in range, never that the line
says what the document claims.

Three minor observations were also closed, all inside this increment's own
files. The test file imported `ENVELOPE_FIELDS` and never used it; the import
was dropped. `memory()` ordered records by `(at, record_id)`, and the record
id is a random uuid, so two records written within the same clock tick could
come back out of insertion order; it now orders by `(at, rowid)`. The
reviewer also noted that `record_memory` ignores unknown keyword arguments
and stores kind-irrelevant columns; that is left as it is, because the
verified flag is derived from the kind rather than from input, so a caller
still cannot mark a hypothesis verified, and the recorded columns are
harmless for a record of another kind.

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
python3 scripts/check-doc-references
git diff --check
```

Results, copied from the run: the factory suite ran 86 tests, OK; the full
suite ran 172 tests, OK; the document reference checker reported `109
references checked in HARNESS_FRAMEWORK.md`; `git diff --check` exited 0. Token
usage and monetary cost were not supplied by the runtime and remain
unavailable.

### The required contract block

The dedicated prompt-writing agent authored the bounded prompt; the primary
agent executed it. The increment is filed against exactly one pillar row, the
CONTRACT row of `docs/HARNESS_FRAMEWORK.md`, and it completes the first two
parts of that row's next increment. The monitor-side request contract is
untouched and remains recorded as a separate open gap.

A command-mode task must now carry a contract block. A submission without one
is refused at submit time with a `ValueError` that names the contract, and no
row is written. The block's eleven keys, every bound, the acceptance
identifier count rule, the uniqueness rule, and the lexical protected-path rule
are unchanged, and the block is still recorded and never enforced: no budget
limit, protected path, approval requirement, or risk tier is acted on. The
three controller-owned modes return earlier in the validation, so they keep
their exact closed key sets and still run with no contract.

The requirement is checked at submit, not at run. A job stored before the
requirement is never re-validated, is not rewritten, and is still dispatched
and still inspected with its stored specification and its recorded results
unchanged. The shipped behaviour of re-submitting such a stored specification
is the honest consequence of the minimal change: `submit()` validates before
it compares the stored hash, so re-submitting an already-stored
pre-requirement specification now raises the contract error instead of
returning the idempotent `False`. The rule was not reordered to hide that,
because the earlier increment fixed `submit()`'s ordering on purpose.

The repository's example task now carries a valid contract with one
acceptance identifier for its one acceptance command, so the documented submit
command still works. The private runtime ledger was neither opened in place,
nor written, nor migrated by hand: everything established about it was
established by copying the file to a temporary directory and querying the
copy read-only. That copy holds three stored jobs, all command-mode and all
without a contract, and none of them is the example's ID.

```text
python3 -m unittest discover -s tests -p 'test_factory.py' -v
python3 scripts/check
python3 scripts/check-doc-references
git diff --check
```

Results, copied from the run: the factory suite ran 92 tests, OK; the full
suite ran 178 tests, OK; the document reference checker reported `109
references checked in HARNESS_FRAMEWORK.md`; `git diff --check` exited 0. The
factory suite grew from 86 to 92 tests. Token usage and monetary cost were
not supplied by the runtime and remain unavailable.

Files changed: `overseer/factory.py` (the required contract check in the
command-mode branch), `tests/test_factory.py` (the shared contract helper, the
updated spec builders, and a new `RequiredContractTests` class),
`factory/tasks/overseer-checks.json` (the contract block),
`docs/FACTORY_EXECUTION.md` (the example, the legacy-job rule, and the
current counts), `docs/HARNESS_FRAMEWORK.md` (the CONTRACT row, the
process-order sentence, the contract claims bullet, three citations that did
not hold their claim, and every re-cited line), `README.md` (the requirement),
and this log.

Acceptance checks and the test that proves each one:

1. a command-mode task without a contract is refused with a message naming the
   contract, and no row is written —
   `test_a_command_mode_task_without_a_contract_is_rejected`
2. a command-mode task with a contract is accepted —
   `test_a_command_mode_task_with_a_contract_is_accepted`
3. the three controller-owned modes still run with no contract —
   `test_the_controller_modes_still_run_without_a_contract` proves that all
   three submit without a contract and that the fixture mode runs; the
   fake-provider mode's run is proved by
   `test_fake_provider_success_receipt_is_bound_to_its_verifier`, and the
   isolation probe's run by `test_live_probe_blocks_protected_paths_network_and_memory`
   in `tests/test_isolation.py`
4. a stored legacy job still runs, still inspects with `contract` as `None`,
   and keeps its stored hash and specification —
   `test_a_stored_legacy_job_still_runs_and_is_not_rewritten`, and the same
   rule inside `ContractTests.test_a_spec_without_a_contract_still_runs`
5. the repository example task carries a valid contract, validates, and
   submits — `test_the_repository_example_task_carries_a_valid_contract`
6. the runner reports the missing contract as a JSON error with exit status 1
   and no traceback — `test_the_runner_reports_the_missing_contract_as_a_json_error`

Three existing tests changed how they reach their subject without being
weakened: `ContractTests.test_a_spec_without_a_contract_still_runs` and the
absent half of `ContextTests.test_the_context_manifest_records_the_contract_acceptance_ids`
now write their job row the way the ledger held it before the rule, and the
spec builders attach a contract whose acceptance identifiers match the final
number of acceptance commands.

Three pillar-map citations that did not hold their claim were corrected while
the file was re-cited: the product-acceptance claim pointed at a sentence
about duplicate task IDs and now points at the line that says a passed run is
explicitly not product or release acceptance, the continuous-integration claim
now points at the line that says the check is not yet running on a remote
repository, and the agent-traces claim now says that the execution record does
not mention traces and points at the line that carries the concurrency claim.
The reference checker passes all of them either way: it proves only that a
path exists and a line is in range.

Disagreements and limits, kept visible:

- The blueprint makes the Risk group and the Budget group required task
  fields and freezes the task contract at dispatch. The block now covers those
  two groups for command-mode tasks, and the freeze is met by the existing
  specification hash rather than by a separate freeze mechanism. The
  blueprint's Identity, Dependency, Execution, Verification, and Result groups
  remain uncovered by this code.
- The earlier increment kept the block optional on the record that a mandatory
  block would falsify a documented statement about the example task. This
  increment reverses that decision because the example task and the execution
  record are now in scope, and the document now says the opposite of what it
  said before.
- The stored `overseer-foundation-checks-001` record names the pre-move
  workspace path, which the operator moved. The contract rule does not touch
  that record, and whether it could run today is decided by its own recorded
  workspace: the runner does not refuse it, does not rewrite it, and still
  inspects it, but its recorded workspace path no longer exists.
- The monitor's request contract is still one free-text string. That gap is
  unchanged and separately filed; this increment does not close it.

Not touched: the live tmux server and every pane, the running monitor service,
the live factory ledger, `config.json`, the monitor's own modules,
`factory/routing-policy.json`, and the routing policy's status string.

A review of this increment then found five statements that did not match
reality, the dedicated prompt-writing agent authored the corrective prompt,
and the primary agent executed it. No behaviour changed and no test was added,
removed, renamed, or weakened. The execution record's total-suite figure was
wrong, it said 172 where the check command reports 178. The pillar map's
`tests/test_factory.py` coverage citation pointed at a helper line instead of
the test it named. The implementation's own docstring and the `ContractTests`
class docstring still called the contract block optional. The CONTRACT row's
verdict still opened with permission wording, "may now carry", one clause
before the same sentence said the block is required. The execution record's
ledger sentence said "Everything above" where it meant the ledger facts
above. The five files corrected were `overseer/factory.py`,
`tests/test_factory.py`, `docs/FACTORY_EXECUTION.md`,
`docs/HARNESS_FRAMEWORK.md`, and this log.

### Explicit project targeting

The user asked that Overseer manage only the tmux windows and projects that
are explicitly targeted, instead of sweeping every active pane, and that the
work stay inside the Overseer workspace. This increment was written and
executed by the primary agent without a separate prompt-writing agent, because
the workspace had just moved and another agent was committing to the same
repository, so one writer held the tree. That is a deviation from the standing
workflow and is recorded here rather than papered over.

The transport already required an explicit enrollment to be managed, but it
had no way to name a project. `config.json` now carries the scope:

```json
"targets": ["overseer-projects-1174383"],
"target_paths": ["."]
```

`targets` are patterns matched against the pane ID, the session name, and the
window title, with the same rules as `exclude`. `target_paths` are
directories; a relative path resolves against the directory that holds
`config.json`, so `"."` is this workspace. The directory that is compared is
the client's own, read from the bridged process, because a reptyr-bridged
pane reports the bridge's directory instead.

The rules, in order: an excluded pane is never managed, an enrolled pane is
managed, a targeted pane is managed, and every other window is ignored. The
transport refuses to type into a pane that is not in scope, so the scope
holds at the last moment before a send. `overseer status` now shows `WATCHED`,
`TARGETED`, `EXCLUDED`, or `OUT OF SCOPE` for every window.

Targeting the Overseer session brought a dead client back into the monitor's
view, and a dead client used to be reported on every poll. The stale notice
is now reported once per episode instead of once per poll.

The first version of the scope check was wrong, and the live run showed it. A
targeted pane that was never enrolled failed the raw opt-in test, and the
monitor treated that as a failed observation, which aborts the whole poll and
starves every other pane. The opt-in test is now scope-aware: a pane is
readable when it is enrolled or inside the target scope, and the transport
still refuses to type into a pane that is not in scope. The live journal now
shows the dead Overseer client reported once, and the queue polls cleanly.

The suite grew from 178 to 192 tests, all passing, and the document reference
checker resolves all 112 citations. The live tmux server, every pane, and the
running sessions of other projects were not touched; no work was routed
anywhere.

Another writer was active in this repository while this increment was being
finished. It was editing `config.json`, `overseer/__main__.py`,
`overseer/scheduler.py`, `overseer/tmux.py`, and `tests/test_exclusions.py`,
and it added `tests/test_scope.py`, for work of its own on scoped pane
targeting. None of those files were touched, staged, or committed here, and
the tree was left exactly as found. The full suite passed at 192 tests while
that work was in the tree, which is higher than the 178 this increment
measured, because the other writer's new tests are counted there too.

### Memory recall and consumption in the factory

The user asked for the recall side of the CONTEXT and STATE pillars: a new
attempt must be able to query and consume the relevant historical memory
records before it starts, and the runner must pass that past context into the
execution environment or the manifest. This increment was written and
executed by the primary agent without a separate prompt-writing agent, because
another agent was committing to the same repository and one writer held the
tree. That is a deviation from the standing workflow and is recorded here
rather than papered over.

The four memory record kinds could already be stored and queried, and the
manifest said so: "the memory kinds are stored and queryable, but nothing
assembles context from a codebase and no record is consulted by any decision".
That is now false, and the change makes it true.

```text
python3 scripts/check
python3 scripts/check-doc-references
```

`Factory.recall` answers the query. A new attempt recalls the records of its
own job and the records of earlier jobs in the same project, where the
project is the repository root when the workspace is a repository and the
workspace directory when it is not. The records are ordered most recent first
and bounded. A decision that a later decision superseded, and a verified fact
whose bound revision is no longer the workspace's base commit, are marked
unusable rather than handed over as settled, and a hypothesis stays
unverified. The recall is written to `recall.json` in the run evidence
directory, and the execution environment of the worker carries it through
`OVERSEER_RECALL_PATH`, `OVERSEER_RECALL_COUNT`, `OVERSEER_RECALL_KINDS`, and
a bounded `OVERSEER_RECALL_SUMMARY`. The context manifest records the
consumption, the record identifiers, the digest of the recall file, and the
supplied sources for the applicable decisions and the earlier attempts. The
recall changes what the attempt is informed by, not what it is judged by.

The suite grew from 193 to 205 tests, all passing, and the document reference
checker resolves all 116 citations. The CONTEXT row of the pillar map carries
this increment, and the STATE row's now-false claim that recall was absent was
corrected.

A live run confirmed it outside the test suite. Two tasks were submitted to a
temporary ledger in a temporary workspace: the first job recorded a decision
and a verified fact, and the second attempt recalled both. Its `recall.json`
named the scope, the counts, and each record with its status, the worker
received the digest through the environment, and the manifest recorded the
consumption, the record identifiers, and the digest of the recall file:

```text
[verified_fact/current] the package: the package passed the checks
[decision/current] the filter: keep the filter semantics
```

The private factory ledger and the repository were not touched by that run.

### Codebase context assembly for the CONTEXT pillar

The user asked for the context side of the CONTEXT pillar: the manifest's
`relevant_code_and_interfaces` must be populated from a repository map or file
tree analysis instead of staying `None`, and a new attempt must be able to
find the structural symbols, interfaces, and files it needs before it runs.
This increment was written and executed by the primary agent without a
separate prompt-writing agent, because another agent was committing to the
same repository and one writer held the tree. That is a deviation from the
standing workflow and is recorded here rather than papered over.

The manifest said so plainly: "no context builder exists: nothing is
assembled from a codebase, and no file or interface was read into this
manifest". That is now false.

```text
python3 scripts/check
python3 scripts/check-doc-references
```

`overseer/codemap.py` assembles the context. It walks the workspace file
tree with explicit bounds: at most 4000 files, a depth of 12, and the usual
build and cache directories left out. It selects the files the task's own
commands name and the files whose path matches the terms of the objective and
the contract, at most 12 of them, and it extracts their structural symbols:
Python files through the standard library parser, other files through a
declared set of declaration forms. The map is written to `codebase.json` in
the run evidence and handed to the worker through `OVERSEER_CODEBASE_PATH`,
`OVERSEER_CODEBASE_FILES`, `OVERSEER_CODEBASE_SELECTED`, and a bounded
`OVERSEER_CODEBASE_SUMMARY`. The manifest records the assembly, the selected
files with their symbols, the digest of the map, and the real reason when
nothing could be assembled.

The map names files and symbols and carries no file content, which a test
holds: a secret written into a workspace file does not appear in the map. A
file that is binary, too large, or not text is left unread and the reason is
recorded. The assembly changes what an attempt is informed by, not what it is
judged by.

The suite grew from 205 to 217 tests, all passing, and the document reference
checker resolves all 127 citations. The CONTEXT row of the pillar map carries
this increment, and the next CONTEXT increment is named: the map names the
files but does not carry their code.

A live run against a temporary ledger and a temporary workspace showed the map
working, and showed two things worth tightening. The task terms at first
carried the words of the command strings, so the terms are now the objective
and the contract only, and the files the commands name are found by path
instead. The run also showed that a file a command will create is not context
yet, so a named file counts only when it already exists.

```text
pkg/widget.py (the path matches the task terms, score 1): WidgetFilter, WidgetFilter.apply, build_filter
```

The terms of that run were `filter, implementation, limit, repair, size,
widget`, and only `pkg/widget.py` was selected.

### Bounded code excerpts in the codebase context

The user asked for the last part of the CONTEXT pillar: the selected files
must carry safe, bounded code excerpts or line ranges for their relevant
symbols, not only structural names, and the bounds must prevent token bloat
and context flooding. This increment was written and executed by the primary
agent without a separate prompt-writing agent, because another agent was
committing to the same repository and one writer held the tree. That is a
deviation from the standing workflow and is recorded here rather than
papered over.

```text
python3 scripts/check
python3 scripts/check-doc-references
```

The excerpt of a file is the code of its symbols: the block of a Python
function or class, taken from the standard library parser, and the declared
line and the lines after it for other languages. The bounds are explicit and
are recorded with the map: at most 8 KiB and 60 lines and 12 line ranges per
file, and 32 KiB for the whole attempt, so a wide tree cannot flood a
context. What the excerpt holds is named by its line ranges, so a reader can
find the same code in the file itself.

A file whose name marks it as a secret is never read for its content: the
reason is recorded and the text is absent. A file that is binary, too large,
or not text is left alone. The manifest records the excerpt's line ranges and
byte counts per file, and the total, and the supplied source says how many
bytes of code the attempt was given.

The suite grew from 217 to 223 tests, all passing, and the document reference
checker resolves all 127 citations. The CONTEXT row of the pillar map carries
this increment, and the next CONTEXT increment is named: the map relates the
symbols to their code, but not to their callers and their tests.

The live run showed that a secret named file was selected but that the reason
was not recorded, and that the file was read before the secret check. The
check now comes first: a file whose name marks it as a secret is never opened,
its structure is reported as `secret`, its excerpt is reported as skipped with
the reason, and its content is absent from the map. The live run now reports:

```text
pkg/.env -> structure_kind: secret
  structure_reason: the file name marks it as a secret
  excerpt: {'skipped': 'the file name marks it as a secret', 'lines': [], 'bytes': 0}
```

The same run showed the bounds holding: a file with a four hundred line
function was excerpted to sixty lines and 758 bytes with the truncation
recorded, and the whole attempt was given 969 bytes of code.

### Callers and tests in the codebase context

The user asked for the last part of the CONTEXT pillar: the map must relate
each selected symbol to the code that calls it and to the test files that
cover it, not only name the files and the symbols. The prompt for this
increment was written by the dedicated prompt-writing agent and executed by
the primary agent, which is the standing workflow and not a deviation from
it. The prompt is kept in `CONTEXT_CALLERS_TESTS_NEXT_PROMPT.md`.

```text
python3 scripts/check
python3 scripts/check-doc-references
```

The relation is a static reference and not a proven call, and the map says so
wherever it reports one. Python is parsed with the standard library parser:
a module level symbol is referenced by a name, a method by an attribute, and
a reference that is the callee of a call is marked as a call. Every other
language is matched textually with word boundaries, and a textual match is
reported as a mention, because it may be a comment, a string, or an unrelated
identifier. A reference inside the definition of the symbol is the
definition, not a caller, and it is excluded. A method reference does not name
the object it belongs to, and the entry says that it cannot.

Every symbol of every selected file gets a relation, including the symbols
nothing references. A symbol with no caller is recorded with an empty list and
a reason that names the number of files that were searched, so the absence is
a fact and not a gap. A file is a test file when its path names it so, and a
reference in a test file is a test relation while any other reference is a
caller relation. The map also records the inventory of the test files of the
workspace, taken from the file tree alone.

One limit is worth naming: a reference is a use of the symbol, so an import
line is not one. A module that only imports a symbol and re-exports it
therefore shows no caller, and the map says so rather than guessing.

The bounds are explicit and are recorded with the map: at most 400 files
opened for the search, 2 MiB read for it, 20 callers and 10 tests for one
symbol, and 20 skipped-file records. The excerpt bounds are unchanged: 8 KiB
and 60 lines and 12 ranges per file, and 32 KiB for the whole attempt. The
relation has its own budget and adds no file content to the map; it adds
paths and line numbers. A file whose name marks it as a secret is never
opened, and the map records how many such files the workspace holds, whether
or not the search would have reached them. A file that is binary, too large,
or not text is left alone with the reason recorded. The relation block
carries a reason of its own, so what could not be done is stated.

The attempt sees the relation and not only the evidence file: the digest the
worker receives names the caller and the test of a symbol, the manifest's
`relevant_code_and_interfaces` source carries the counts, and the manifest's
`codebase` block holds the per-symbol entries.

The suite grew from 223 to 234 tests, all passing, and the document reference
checker resolves all 134 citations. The CONTEXT row of the pillar map carries
this increment, and the next CONTEXT increment is named: the map relates the
symbols to their code, to their callers, and to their tests, but not to the
recalled memory records that speak about them.

A live run against a temporary ledger and a temporary workspace showed the
relation working, and it showed that a secret named file that was never a
candidate of the search was not counted as excluded. The count is now taken
from the file tree alone, so every secret named file is counted and none of
them is opened. The live run reports:

```text
state: passed

--- relation block ---
{
  "candidate_files": 4,
  "searched_files": 3,
  "opened_files": 3,
  "truncated": false,
  "bytes_read": 340,
  "test_file_count": 1,
  "test_files": [
    "tests/test_widget.py"
  ],
  "test_files_truncated": false,
  "secrets_excluded": 2,
  "skipped": [
    {
      "file": "pkg/secrets.py",
      "reason": "the file name marks it as a secret"
    }
  ],
  "reason": "one candidate file was left out of the search, and the relation it holds is not represented",
  "caller_count": 3,
  "test_count": 1
}

--- per symbol relation ---
WidgetFilter         caller=[pkg/widget.py line 7 (call, parsed)] test=[]
                     reason: no test file references the symbol in the 3 searched files
WidgetFilter.apply   caller=[pkg/app.py line 5 (call, parsed)] test=[]
                     reason: no test file references the symbol in the 3 searched files
build_filter         caller=[pkg/app.py line 4 (call, parsed)] test=[tests/test_widget.py line 4 (call, parsed)]
unused               caller=[]                                    test=[]
                     reason: no reference to the symbol was found in the 3 searched files
test_build           caller=[]                                    test=[]
                     reason: no reference to the symbol was found in the 3 searched files

--- supplied source ---
the workspace file tree: 5 files, 2 selected for this task with 5 structural symbols, 206 bytes of code excerpt, and 3 caller and 1 test references
--- secret content absent from the map --- True
```

### Review correction: the relation bounds did not hold, and the citations drifted

A fresh reviewer read the increment against the prompt and the acceptance
criteria. It found that two of the promises the increment made did not hold,
and that the citations of the document drifted. The findings were checked by
running them, not taken on trust, and they were true.

The byte budget was checked after a file had been read, so the map reported
2 MiB while 48 MiB was read, and the files that were read and thrown away did
not count against the file cap either. The size of a file is now checked
before it is opened, the number of files opened is counted and reported, the
search stops when the budget is spent, and a corpus the cap cut short is
recorded as truncated with the reason that says so. Two tests hold the bounds
now, and they were checked against the defect: with the old check put back,
the byte test reads 3,840,243 bytes against a bound of 2,097,152, and the
file test opens 431 files against a bound of 400.

The relation block carried no reason of its own, the inventory of the test
files was cut at 400 without saying so, and the digest lost its truncation
marker when the first selected file alone overflowed it. The block carries a
reason now, the inventory says whether it was cut, and the marker is kept.

A method that a file that is not Python refers to by its bare name was not
found, while the same reference in a Python file was, so the map missed a
caller in one language and found it in the other. The bare name is tried when
the qualified name is not found, and the entry says that the map cannot
resolve the object it belongs to.

Eleven citations of `overseer/factory.py` had drifted, because the increment
added lines to the factory and the document was not re-derived. Two of them
were in the CONTEXT row itself, and one more had been wrong before this
increment: the document pointed at a line of the restore path for the run of
the factory. Every citation was re-derived by hand against the code it
names, and the reference checker resolves all 134 of them.

The tests were weak in three places and are not weak now: the caller and the
test of a symbol are checked by their line, the attempt is checked against
the relation in the digest and not against a file name that the digest also
lists, and the workspace is checked to be untouched by the search.

A Python file with a null byte past the first kilobyte raised a `ValueError`
from the parser before Python 3.12, and the map could not read such a file
at all. The parser call now treats that as the file it is, and the search
leaves the file alone with the reason recorded.

### Recalled memory attached to the symbols it names

The user asked to continue the work. The CONTEXT row named the next
increment: relate the recalled memory records to the symbols they name, so a
decision or a verified fact about a symbol is attached to that symbol in the
map instead of listed beside it. The prompt for this increment was written by
the dedicated prompt-writing agent and executed by the primary agent, which is
the standing workflow and not a deviation from it. The prompt is kept in
`CONTEXT_MEMORY_SYMBOLS_NEXT_PROMPT.md`.

```text
python3 scripts/check
python3 scripts/check-doc-references
grep -n "^from overseer\|^import overseer" overseer/codemap.py
```

The recall is computed before the map, so the runner now hands the recalled
records to the map as plain dicts. The map reads no ledger and imports nothing
from the factory; the grep prints nothing. The recall, its file, its digest,
and its variables are unchanged: the recall stays the complete list, and the
map adds the attachment.

The attachment is a textual match, and every attachment says so. A symbol's
name is matched case-sensitively on identifier boundaries, so `build_filter`
does not match `build_filter_v2`. Every name is matched in the record's
affected component; only an identifier-shaped name, one with `_` or `.` or a
capital after its first character, is matched in its entry, because a plain
lowercase word in free text is far more often an English word than a symbol.
The most specific name wins: `WidgetFilter.apply` in a record attaches to the
method and not to the class. A record that names a selected file's path and
none of its symbols attaches to the file. A record that names nothing selected
stays in the recall and is counted in the map as unattached, with the reason.

Every status attaches. A superseded decision, a fact whose bound revision is
not the workspace's base commit, a hypothesis, and a past attempt are attached
with `usable` false and a reason that names why, and the digest prints
`NOT USABLE` on their lines; the usable records are listed first. The bounds
are module constants and are recorded in the map's limits: 5 records per
symbol and 5 per file, 160 characters of entry, 32 unattached records listed,
and 6 memory lines per file in the digest. A cap that drops an attachment is
recorded with the count.

The attachment reaches the attempt through the memory lines of
`OVERSEER_CODEBASE_SUMMARY`, the attached count in `OVERSEER_CODEBASE_MEMORY`,
the `memory` block of the manifest's codebase entry, and `codebase.json`. The
supplied list says how many records were attached and how many current
decisions; it says they were supplied, and it claims no enforcement.

Eight tests were added with the increment, and eight more with the review
correction below; the suite runs 250 tests. Each of the first eight was
checked against the defect: with the records withheld from the map, all eight
fail.

Every citation of `overseer/factory.py` and `overseer/codemap.py` in the
pillar map was re-derived after the last edit. A line map of the old and the
new code was built from the diff, and each cited line was checked to hold the
same text after it moved; nine citations in other rows of the map moved with
the code and were carried. Three citations had drifted before this increment
and were corrected by hand: the memory record API pointed at two `return`
lines, and the process paragraph pointed at the line before `assemble`.

### Review correction: paths read as symbols, and the counts counted what was dropped

A fresh reviewer read the increment against the prompt and found four
defects and weak tests. The findings were checked by running them, and they
were true.

A path in a record attached to a symbol of the same name instead of to the
file: `pkg/build.py` holds the identifier `build` between its separators, so
the symbol `build` was named and the file was not. The selected paths are now
blanked out of a record's text before the names are matched, so a path names
its file, and only its file.

The counts were taken before the caps, so a record every attachment of which
a cap had dropped was counted as attached; with eight records on one symbol
the map said eight were attached and showed five. The counts now describe the
attachments the caps kept, and the records a cap dropped are counted apart in
`dropped_by_cap`, with the dropped attachments in `attachments_dropped`. The
test that asserted eight had locked the defect in and now asserts five.

The digest ordered the usable records first only inside one symbol's list,
so the not-usable records of one symbol could fill the six lines of a file
and hide a usable record of another. The room is now shared by the whole file
and the usable records take it first. The line about the unattached records
could also carry the digest past a limit shorter than itself; it is now cut
to the limit.

The reviewer made nine mutations of the code, and eight of them passed the
tests: the path boundaries, the usable-first order, the entry, file, and
unattached bounds, the rule that a symbol named with its file attaches only to
the symbol, case sensitivity, and the skip of an error or a short name. Eight
tests were added on plain dicts. The nine mutations and four more for the
corrections, the path blanking, the counts after the cap, the digest order,
and the cut of the line, all fail the tests now.

The invalidated reason names the fact's bound revision, so the attachment
reads the record's `revision`, a key the prompt's list did not name; the
prompt's own test required the reason to name it. A record that names a
symbol of one file and the path of another is counted both as attached to a
symbol and as attached to a file, and once as attached.

Moving the factory's lines moved citations in the STATE, TOOLS, PERMISSIONS,
and EVIDENCE rows of the pillar map. They were carried with the code, which
the prompt's list of passages did not name; leaving them would have left them
false. Two older citations had drifted and were corrected: the decision
record pointed inside `resolve`, and the submission pointed inside `event`.
Every citation of the factory and the map in the pillar map was checked by
hand against the line it names after the last edit, and the reference checker
resolves 138 of them; the count fell by two because two corrected citations
now name lines that were already cited.

### The prompt-writer loop coded into the monitor

The user's instruction: "its not your fault but make sure this gets coded into
the program to do it this way". The way is the standing loop of
`/home/kali/Programming/Projects/AGENTS.md`: after a step is executed, its
results go to the dedicated prompt-writing agent, which writes the next
bounded prompt, which the primary agent executes. A prompt's stopping
condition ends that prompt, not the objective.

The observed failure: a pane finished one increment, printed the next
increment it had named, and ended with `OVERSEER_DONE`, and Overseer stopped.
The monitor treated every `OVERSEER_DONE` and every `done` report as the end of
the objective, and no prompt it sent had a status for a finished step of an
unfinished objective. The prompt for this increment was written by the
dedicated prompt-writing agent and executed by the primary agent, and it is
kept in `WRITER_LOOP_NEXT_PROMPT.md`. It is filed against the CONTEXT row,
which owns the continuation instruction and the prompt assembly.

```text
python3 scripts/check
python3 scripts/check-doc-references
git diff --stat
```

The report gains the status `step_done`: the step is finished and
`remaining` names the next step. It needs a nonempty objective and remaining,
like `continue`; with either blank no handoff is composed, and the reason is
that the report has no remaining work. A `step_done` report gets a
writer-handoff prompt that tells the pane to give the step's results to the
dedicated prompt-writing agent, have it write one bounded next prompt for the
named step, execute and verify it, and report `needs_input` if no separate
writer can be used. A `done` report keeps its meaning, the objective is
finished, and still stops even when its `remaining` is not empty: the program
takes it at its word and does not guess. `needs_input` always stops.

One function, `stop_requested`, now decides the stop for both the classifier
and the queue's phase, so the two cannot disagree. `OVERSEER_NEEDS_INPUT`
always stops. `OVERSEER_DONE` stops unless the latest valid report on the
screen is `step_done`, because the structured report names the next step and
the bare marker does not. A new marker, `OVERSEER_STEP_DONE`, does the same
under a `step_done` report and is neither a stop nor a reason to send on its
own. The permission and generation patterns are checked before the handoff and
still win. The handoff goes through `Policy.consider` in the monitor and in the
queue, so the idle threshold, the already-sent and held screens, the cooldown,
and the daily limit bound the loop.

The report tail of every composed prompt and the configured `reply` now
state the loop and the rule; only the `reply` key of `config.json` changed. The
reply is 937 characters and the tail 443, and neither matches the permission
pattern. With every report field at 5000 characters both composers still return
one line of at most 1000 characters that keeps the rule and the first 40
characters of the remaining step. The dry-run and sent logs name a handoff as
`writer handoff prompt`; the prompt allowed only the dry-run log in
`__main__.py`, and the sent logs of the monitor and the queue were changed as
well, because a handoff logged as a routine continuation would misstate what
was typed.

Fourteen tests were added, eleven for the policy, two for the queue, and one
for the monitor; the suite runs 264 tests and the 250 earlier tests pass
unchanged. Each mutation of the prompt was applied alone and failed the suite:
M1 `step_done` treated as a stop (ten tests, among them
`test_a_step_done_report_yields_the_writer_handoff`); M2 `needs_input`
overridden (`test_needs_input_is_never_overridden`,
`test_needs_input_after_a_step_report_stops_the_pane`); M3 a handoff with an
empty remaining (`test_no_handoff_is_composed_with_an_empty_remaining`); M4 the
handoff past the bounds of `Policy.consider` (`test_the_handoff_loop_is_bounded`
and the two end-to-end tests); M5 a legacy `done` with a remaining step taken
as a handoff (`test_a_legacy_done_report_still_stops` and four more); M6 the
queue's phase on the raw stop pattern
(`test_a_finished_step_is_handed_to_the_writer_once`); M7 the handoff before
the permission check (`test_blocked_text_still_wins_over_a_handoff`); M8 a
`step_done` report composed with the continue template (three tests); M9 the
handoff taken from an older report (`test_the_latest_report_wins`); M10 the old
status list in the tail (three tests) and in the reply
(`test_every_prompt_states_the_loop`); M11 a `step_done` report answered with
the fallback reply (five tests); M12 `OVERSEER_DONE` ignored without a
`step_done` report (six tests).

What it does not do: Overseer instructs the handoff. It cannot see or verify
that a separate prompt-writing agent ran, wrote the next prompt, or that the
prompt was executed; it reads only the next report, and the pillar map says so
under what it does not claim.

Every citation of `overseer/policy.py`, `overseer/scheduler.py`, and
`overseer/__main__.py` in the pillar map was re-derived from a line map of the
old and the new code, each moved line checked to hold the same text, and the
new ones checked by hand. Three had drifted before this increment and were
corrected: the queue pointed at `_missing_process`, the single-writer lock at a
log line, and the command surface at a line inside `run`. The reference
checker resolves 144 references.

### Review correction: a stale or echoed report could override a stop

A fresh reviewer read the handoff against the prompt and found four ways in
which a screen that should stop got a prompt. They were checked by running
them, and they were true.

A step report of an earlier turn overrode the `OVERSEER_DONE` of the newest
turn, because the report was read from the whole screen; the monitor sent the
old step's handoff once per cooldown. A report and every marker override now
count only in the current turn, the text after the last submitted prompt line,
which the queue already used; that function moved from the scheduler into the
policy, and the scheduler's `response` calls it. A handoff composed from a
report of an earlier turn is withheld with its own reason.

The prompts named `OVERSEER_STEP_DONE` mid-sentence, and a client that wraps
its echo of a sent prompt could put the marker at the start of a line, so the
monitor's own typed text became its signal to send again. The marker names in
the report tail and the reply are now quoted; a test wraps the reply, the
handoff, and the continue prompt at every width from 30 to 240 and finds no
marker at a line start.

A step report quoted in the answer, with prose after it, overrode the
`OVERSEER_DONE` that ended the answer. The prompt's rule, that the latest valid
report decides, was narrowed: a bare `OVERSEER_DONE` ends only the step when
the line directly above it, blank lines aside, is that step report.
`OVERSEER_STEP_DONE` stays enough under a step report of the current turn.

`OVERSEER_NEEDS_INPUT` above the last eighteen lines no longer stopped the
monitor, because its stop check reads only the tail and the handoff added a
reason to send. `OVERSEER_NEEDS_INPUT` anywhere in the current turn now stops,
in the safe direction.

The reviewer's mutations found seven more gaps in the tests: the outcome
fingerprint of the step marker, the marker condition of the handoff, a report
above the tail, the dry-run log, the objective in the handoff, the stop check of
the queue's phase, and the daily limit in the monitor. Fourteen tests were added
for the four defects and the gaps, and one new test was changed: the test that
the permission text wins over a handoff put the permission line between the
report and `OVERSEER_DONE`, which the narrowed rule now stops before the
permission check is reached, so it uses `OVERSEER_STEP_DONE` and still proves
that the permission text wins. Twenty-six mutations were applied one at a time,
M1 to M12 of the prompt with M10 also on the reply, the reviewer's N2 to N8, and
five that undo the corrections; each fails the suite. The suite runs 278 tests.

A `continue` report of an earlier turn still drives a prompt in the queue, as
it did before the handoff existed; that is not changed here. The citations of
the policy and the scheduler were re-derived by hand after the last edit, and
the reference checker resolves 147 references.

### The selection widened by the relation and the memory

The user asked to continue the work through the standing loop. The CONTEXT
row named the next increment: widen the selection with the relation and the
memory. The prompt was written by the dedicated prompt-writing agent, refreshed
by it after the writer loop landed, and executed by the primary agent; it is
kept in `CONTEXT_WIDEN_SELECTION_NEXT_PROMPT.md`.

```text
python3 scripts/check
python3 scripts/check-doc-references
grep -n "^from overseer\|^import overseer" overseer/codemap.py
git diff --stat
```

The map now adds, in one round, the files that a current decision names by
path and the files that hold a caller of a symbol of the task's own selection,
even when the task terms do not match them. A decision widens only when it is a
decision, its status is current, and it informs a decision, and only its
affected component and its entry are read for a path, on path boundaries; its
source, its invalidation condition, and its reason never are. A decision that
names a symbol but no path does not widen, because the map cannot know the
symbols of a file it has not read. A verified fact, a superseded decision, a
hypothesis, and a historical attempt never widen. A caller comes from the
callers of the primary relations, so a test file, which is the test relation,
never widens as a caller, and a secret is never widened and is counted apart.
What a widened file calls, or what names it, does not widen further.

The decision candidates come first, in the order of the recall, then the
callers by their reference count and then by path. At most 4 files are added,
never past the selection bound of 12 and never in place of a file the task
selected; every candidate the bounds left out is listed with its reason, up to
20. The task's own files are detailed first and spend the excerpt budget
first; a widened file is excerpted from what is left, and its relations come
from the same, single relation search, so the bytes and files the search
reads are unchanged. The counts describe what is shown: the widened count is
the number of widened files in the selection, the primary and widened counts
add up to the selection, and the candidates are the widened files and the
left-out ones.

The widening reaches the attempt through the digest, where a widened file's
header says why it was widened and a tail line counts what was left out,
through `OVERSEER_CODEBASE_WIDENED`, through the manifest, where each selected
file carries `widened_by` and the codebase block carries the selection, and
through `codebase.json`. The supplied list says how many files were widened;
it claims context supplied, not proof of relevance.

No existing test needed to be made more specific: the 278 earlier tests pass
unchanged. Thirteen tests were added and the suite runs 291 tests. Each
mutation was applied alone and failed the suite: M1 a primary file displaced
(`test_the_widening_never_displaces_and_keeps_its_bounds`,
`test_the_selection_is_bounded`); M2 any decision status widens and M3 a fact
widens (`test_a_record_that_is_not_usable_never_widens`); M4 the test relation
fed in as callers (`test_a_test_file_is_not_widened_as_a_caller`); M5 a second
round (`test_the_widening_is_one_round` and the bound test); M6 the widening
bound ignored and M8 callers ordered by path only
(`test_the_widening_adds_at_most_its_bound_by_reference_count`); M7 candidates
counted as widened (three tests); M9 the widened files excerpted before the
primary ones (`test_the_primary_excerpts_are_unchanged_by_the_widening`); M10
a substring path match (`test_a_path_widens_only_on_its_boundaries`); M11 a
secret admitted (`test_a_secret_is_never_widened`); M12 widened files without
relations (`test_a_caller_file_is_widened`, `test_the_widening_is_one_round`)
and without memory (`test_a_current_decision_widens_the_file_it_names`); M13
the other fields of a decision read for a path
(`test_only_the_component_and_entry_of_a_decision_widen`); M14 a hidden second
round in the same pass (`test_the_widening_is_one_round`). Three mutations
first survived and the tests were strengthened: the first M4, which removed
the test-file check, was equivalent, because the callers already exclude the
test files, and was replaced by one that feeds the test relation in; M8
survived because the test's paths sorted in the order of their reference
counts; and M9 survived because the test's files never spent the excerpt
budget, so it now fills most of the budget with four primary files.

A secret-named file that calls a selected symbol is never opened, so the map
cannot know it is a caller; only a secret that a decision names is counted as
left out. Every citation of `overseer/codemap.py` and `overseer/factory.py` in
the pillar map was re-derived from a line map of the old and the new code and
checked by hand after the last edit; the checker resolves 155 references.

### Review correction: the wrong bound named, ties by the file tree, and capped callers unseen

A fresh reviewer read the widening against the prompt and found three defects
and weak tests. They were checked by running them, and they were true.

With nine to eleven primary files the room the selection bound left was
smaller than the widening bound, and a candidate past it was still told that
the widening bound of 4 was reached, though fewer than 4 files were widened.
The reason now names the bound that applied.

The paths one decision names were taken in the order of the file tree, which
puts the root before its directories, so the file tree decided which one the
bound kept; the prompt asked for ties by path. They are now taken in path
order.

The callers come from the caller lists of the relation, which hold at most 20
references per symbol, so a file holding only callers past that cap was never
a candidate and was not counted as left out, while the selection said nothing
was left out. Each relation now records its full caller count, and the
selection counts the caller lists that were cut and says that a file holding
only callers past the cap is not a candidate. A widened file's reference count
is still the count of the references inside the cap.

A decision without a record id put `None` into the widened record ids and the
digest; it no longer does. A file named by a decision and calling a selected
symbol is now marked by whether a decision named it, not by whether it has a
record id.

The reviewer's mutations of the order of the decision tier, the count of a
file in both tiers, the reasons of such a file, the record id in the digest,
the bounds of the record ids, the symbols, and the left-out list, and a secret
taking a slot all passed the tests. Six tests were added for them and the
defects, and the test that the widening never displaces now names the twelve
files it expects instead of computing them with the code it checks. Thirty
mutations were applied one at a time, M1 to M14 of the prompt with the
replaced M4 and the memory variant of M12, the reviewer's, and four that undo
the corrections; each fails the suite, and the runner now reports a mutation
whose pattern no longer applies instead of counting it. The suite runs 297
tests.

Two limits remain. A file a decision names that is binary or too large is
widened with no symbols and no excerpt, and takes a slot. The digest's
truncation note is added after its limit, as it was before this increment.
The citations of the map in the pillar map were re-derived by hand after the
last edit; the checker resolves 155 references.

### The skill provenance recorded in the context of every attempt

The user asked: "Implement skills provenance integration for the CONTEXT
pillar in the factory: 1. Update the manifest builder and run execution
pipeline so that `factory/skills-provenance.json` is read and recorded in the
context manifest for every attempt, identifying which skills were active or
provided. 2. Expose the skill provenance details via environment variables or
manifest records in the run evidence directory. 3. Add comprehensive unit
tests in tests/test_factory.py covering skill provenance parsing and manifest
integration. 4. Run python3 scripts/check and python3
scripts/check-doc-references to ensure 100% test pass rates and valid
citations, update WORK_LOG.md, and commit clean." It was also the CONTEXT
row's named next increment. The prompt was written by the dedicated
prompt-writing agent and executed by the primary agent from `dba883a`; it is
kept in `CONTEXT_SKILLS_PROVENANCE_NEXT_PROMPT.md` and committed with this
increment.

```text
python3 scripts/check
python3 scripts/check-doc-references
grep -n "^from overseer.factory\|^import overseer.factory" overseer/skills.py
```

The request asked which skills were active or provided. The factory runs
argument-vector commands, passes no skill to them, and cannot see whether a
client loaded one, so the honest answer is recorded in three layers and never
a fourth: the skills the file declares, the skills whose installed files match
the recorded hashes at the start of the attempt, and the skills Overseer
supplied to the attempt, which is none. Every skill carries
`supplied_to_attempt` and `activation_observed` as false, and the file's own
status and runtime text is copied only under `declared_` keys, as the file's
statement. A file that says a skill is active does not make it so; a test
holds that.

A new module, `overseer/skills.py`, reads and validates the file. Its size is
checked before it is opened, at most 64 KiB; a file with more than 32 skills is
rejected whole, so a truncated list is never shown as the whole; a bad entry is
rejected with its reason and its siblings are kept; only the listed fields are
copied, an unknown top-level key is named and not copied, and the blueprint
block, which holds a host path outside the repository, is not copied. The
installed check opens no secret-named file, follows no symlink out of the
installed directory, checks the size before it opens a file, and keeps only
the outcome and, for a mismatch, the observed digest. The license file is not
checked, because the provenance names no path for it.

Every attempt writes `skills.json` into its run evidence, records one `skills`
event, hands the worker `OVERSEER_SKILLS_PATH`,
`OVERSEER_SKILLS_PROVENANCE_SHA256`, `OVERSEER_SKILLS_DECLARED`, and
`OVERSEER_SKILLS_VERIFIED`, and its manifest carries a `skills` block with the
digests, the counts, and the per-skill layers. The manifest's supplied list is
unchanged, because no skill is supplied. A missing or malformed provenance file
is recorded with its reason and does not block the attempt. The factory takes
the provenance path as a keyword, so every test that asserts a skill fact
builds its own file and installed directory. The other context tests use the
repository's file and so read the host's installed skill files, read-only,
without asserting what they find.

Thirteen tests were added and the suite runs 310 tests. Each mutation was
applied alone and failed the suite: M1 supplied derived from the status and M2
activation copied from the file
(`test_a_file_that_says_a_skill_is_active_does_not_make_it_so`); M3 the whole
entry copied (that test and
`test_only_the_listed_fields_of_the_provenance_are_copied`); M4 the size checked
after reading, M7 a malformed file failing the attempt, and M9 the first 32
skills kept
(`test_a_provenance_file_that_cannot_be_used_is_recorded_and_the_attempt_runs`);
M5 a symlink followed out of the skill
(`test_a_missing_file_and_a_symlink_out_of_the_skill_are_not_verified`); M6 a
path or dotted file key accepted and M8 rejected entries counted as declared
(`test_a_bad_skill_entry_is_rejected_and_its_siblings_are_kept`); M10 verified
when any file matches, which first survived and is now held by
`test_a_skill_is_verified_only_when_every_file_matches`; M11 the skills left
unsorted (two tests); M12 a supplied item added for skills (two tests); M13 an
`OVERSEER_SKILLS_ACTIVE` variable (`test_the_attempt_sees_the_skill_provenance`).

The CONTEXT row's next increment is now the handoff record of the blueprint.
Every citation of `overseer/factory.py` and `overseer/skills.py` in the pillar
map was re-derived from a line map of the old and the new code and checked by
hand after the last edit; the checker resolves 166 references.

### Review correction: a provenance file could block the job, and formats let a newline through

A fresh reviewer read the increment against the prompt and found that a
provenance file could raise out of the reader and block the job, and that the
tests passed nine of ten of its mutations. The findings were checked by
running them, and they were true.

JSON allows a lone surrogate, and an `installed_path` made of one raised a
`UnicodeEncodeError` from the path functions, which is not an `OSError`; the
exception left the dispatch transaction open, the job stayed queued, and the
next run raised from the database. Text that cannot be encoded as UTF-8 is now
rejected as a field, the check of an installed file treats any `OSError` or
`ValueError` as unreadable, and the factory catches anything the reader raises
and records that the provenance could not be checked, so the attempt runs.

The formats were matched with `match` and `$`, which accepts a trailing
newline, so a skill named `alpha` and one named `alpha` with a newline both
passed, and a revision kept its newline. Every format is now matched whole. A
`schema_version` of `1.0` was accepted; only the integer 1 is. A rejected file
key was copied into its reason, and every unknown top-level key name was
listed whatever its length or characters; a rejected value is no longer
echoed, and only plain key names are listed, at most 32, the rest counted. A
top-level field or a revision that is not copied now says so in the record's
notes. The read of the provenance file and of an installed file is now bounded
as well as its size checked, so a file that grows after its size was taken is
not read whole.

Nine tests were added, and the test that every rejection has its own reason
now expects the two bad file keys to share one, because the key is no longer
echoed. Twenty-five mutations were applied one at a time, M1 to M13 of the
prompt, with M4 rewritten as a read before the size check and M7 as a factory
that fails on a bad file, the reviewer's ten, and three that undo the
corrections; each fails the suite. The suite runs 319 tests. The citations of
the factory and the reader were re-derived from a line map and checked by hand
after the last edit; the checker resolves 166 references.

### The workspace diff of an attempt captured as a patch receipt

The user asked: "Implement workspace diff and patch receipt capture for the
CONTEXT and EVIDENCE pillars in the factory: 1. Update the run execution and
manifest pipeline so that the exact git diff (patch) of any changes made to the
workspace during an attempt is automatically captured and stored in the run
evidence directory (e.g., as `diff.patch`). 2. Record diff statistics, modified
file lists, and path summaries in the context manifest. 3. Add comprehensive
unit tests in tests/test_factory.py covering diff capture, patch generation,
and manifest integration. 4. Run python3 scripts/check and python3
scripts/check-doc-references to ensure 100% test pass rates and valid
citations, update WORK_LOG.md, and commit clean." `AGENTS.md` asks for one
pillar row, and this increment is filed against EVIDENCE: a patch of what an
attempt changed is a receipt of its result, the verification record of the
blueprint. CONTEXT is touched only where the manifest must stay honest, by the
manifest's `workspace_diff` block and the candidate revision. The prompt was
written by the dedicated prompt-writing agent and executed by the primary agent
from `c1c9637`; it is kept in `EVIDENCE_WORKSPACE_DIFF_NEXT_PROMPT.md` and
committed with this increment.

```text
python3 scripts/check
python3 scripts/check-doc-references
grep -n "^from overseer.factory\|^import overseer.factory" overseer/workdiff.py
grep -n "'add'\|'stash'\|'apply'\|'reset'\|'checkout'\|update-index" overseer/workdiff.py
```

The attempt's change is what differs between a snapshot taken immediately
before the implementation command and one taken immediately after it returns,
whatever its exit. A path dirty or untracked at the start keeps its before
bytes in memory only, so a path the attempt edits again is patched from that
content, not from HEAD, and an untouched earlier edit is only listed as
pre-existing; a path clean at the start is patched from the before head's blob,
so a commit the attempt made is inside the patch. Paths are compared by their
git blob ids, computed in Python for the worktree, so a change is found without
reading the head blob. What the checks change afterwards is listed apart, by
path and status. When HEAD moved, the new HEAD is recorded as the candidate
revision and leaves the manifest's unmeasured list; otherwise it stays there,
because an uncommitted worktree is not a revision.

Git is only read. Every call goes through one runner with a timeout, a bounded
output, `GIT_OPTIONAL_LOCKS=0` so `git status` does not refresh the index, no
system configuration, pager, or prompt, and the fsmonitor and the untracked
cache off. The patch is built in Python as a git-style unified diff, with the
mode lines, the new and deleted file headers, and the marker of a missing final
newline, and a test applies it with `git apply` to a copy of the before state
and compares the bytes. Secret-named files are listed without content or hash;
binary files by their hashes; symlinks without their target; oversized files,
pre-existing files whose bytes were not held, paths that are not UTF-8 or need
quoting, and every file past the patch bound are withheld with the reason. The
patch holds at most 1 MiB and is cut only at a file boundary, at most 200 files
are listed and the rest counted, and the stats count only what the patch holds
and say whether it is complete. A workspace that is not a git repository, the
three modes that run in the evidence directory, and any exception inside the
capture, recorded by its type name only, leave the attempt as it was.

Four departures from the prompt, all read-only: `rev-parse --show-prefix` and
`--show-object-format`, `ls-tree`, and `diff-tree --name-only` are run as well
as the commands the prompt listed, because the workspace may be a subdirectory,
the blob of a clean path must be found, and the paths a commit changed must be
seen; a repository that does not use SHA-1 object ids records that and captures
nothing; and `capture` returns the after snapshot with the patch and the
receipt, so the changes of the checks are compared with the same state.

Sixteen tests were added in `WorkspaceDiffTests` and the suite runs 335 tests.
Each mutation was applied alone and failed the suite: M1 the before snapshot
dropped (`test_a_change_made_before_the_attempt_is_not_attributed_to_it` and
two more); M2 untracked files skipped (eight tests); M3 `git add -N` and M4
`GIT_OPTIONAL_LOCKS` removed (`test_the_capture_never_writes_to_git`); M5 a
secret's content and M6 its hash
(`test_a_secret_named_file_is_listed_without_content_or_hash`); M7 truncation
unrecorded (two tests); M8 a patch cut mid-file
(`test_the_patch_bounds_hold_at_a_file_boundary`); M9 a non-git workspace
raising (`test_a_workspace_that_is_not_git_runs_as_before`); M10 the capture
taken after the checks (`test_a_change_made_by_a_check_is_listed_apart`); M11
a candidate revision without a moved HEAD
(`test_a_commit_made_by_the_attempt_is_in_the_patch_and_names_the_revision`);
M12 withheld files counted in the insertions (four tests); M13 the missing
newline marker (`test_a_file_without_a_final_newline_carries_the_marker`); M14 a
symlink followed (`test_a_binary_file_and_a_symlink_are_withheld_with_the_reason`);
M15 the guard removed (`test_a_capture_that_raises_does_not_block_the_attempt`);
M16 a non-UTF-8 path written into the patch
(`test_a_path_that_is_not_utf8_is_listed_and_withheld`).

The mutation set was run again, alone and reverted, against the final tree, and
each of the sixteen still failed the suite with the test named above. Three of
the mutations only fail when they are applied faithfully, and the record says
so: the before snapshot must be dropped rather than ignored, the non-git
workspace must raise rather than be handled, and the withheld files must be
counted as files of the patch. The count helper now also holds that a withheld
file carries no insertions and no deletions, so a mutation that gives one a
count fails as well.

The CONTEXT row's named handoff record now has the candidate revision in one
case, when HEAD moved; its next increment is otherwise unchanged. Every
citation of `overseer/factory.py`, `overseer/workdiff.py`, and the new test
class in the pillar map was re-derived from a line map of the old and the new
code and checked by hand after the last edit; the checker resolves 183
references.

### The factory agent directives added to the project entry point

The user asked for the Overseer factory agent directives to be added to the
project's `AGENTS.md`. The file is the navigation-first entry point the
blueprint asks for, so the directives were appended there as a third section,
`## Overseer factory agent directives`, with the two subsections the user
named, `### Core execution mandates` and `### Verification and handoff
protocol`. The four mandates are there in the user's words: no premature
completion, the sandbox self-correction loop of at most three attempts,
recursive prompt generation, and the file writing rules. The handoff protocol
names the syntax or AST check, the unit or dry run, and the status block with
its four keys.

No code, test, schema, service, ledger, or pane was touched, so no pillar row
in `docs/HARNESS_FRAMEWORK.md` changed and no verdict moved. The change is
checked, not assumed: a structure check parsed the file and confirmed the
code fences balance, the fence carries a language, the headings do not jump a
level, the four numbered mandates each hold a bold label, the handoff block
holds the four required keys, and no line has trailing whitespace; a fidelity
check confirmed all twenty-three clauses of the user's text survive the
reformatting. The suite runs 335 tests and the checker resolves 183
references.

### The blueprint's handoff record persisted for every attempt

The user asked: "Execute the next authorized step from AGENTS.md: Persist the
blueprint's handoff record in `docs/HARNESS_FRAMEWORK.md` (for the CONTEXT
row) based on evidence from commit 9a88598—including candidate revision,
completed/failing acceptance IDs, and next eligible action—leaving
unobservable fields marked unmeasured. Verify execution with the test suite
(`python3 scripts/check`) and `scripts/check-doc-references` before
reporting." `AGENTS.md` asks for one pillar row, and this increment is filed
against CONTEXT: the handoff record is the context of an attempt, the
blueprint's own summary of what that attempt left behind. The prompt was
written by the dedicated prompt-writing agent and executed by the primary
agent; it is kept in `CONTEXT_HANDOFF_RECORD_NEXT_PROMPT.md` and committed
with this increment.

The blueprint's sentence is `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299`: on
handoff, persist objective, base and candidate revisions, completed acceptance
IDs, failing IDs, environment state, commands actually run, unresolved effects,
remaining budget, and next eligible action; the successor checks the ledger
and the workspace before trusting the summary, and reconciles a disagreement.

The three decisions the increment had to make were settled in the prompt and
are recorded here. The record lives in a new `handoff.json` in the run's
evidence directory, next to `context.json` and `summary.json`, and the
manifest carries a `handoff` block that names the file, its digest, and the
headline facts. The ledger records its path and digest without a schema
change: `summary.json` gains a `handoff` entry and the `events` table gains
one `handoff` row, beside the `context_manifest` event. The record is scoped
to one attempt by its run directory; it names its `job_id`, `run_id`, and
`spec_hash`, and a later run of the same job leaves an earlier record
byte-identical.

The rules are the blueprint's, and the record is honest about each of them.
The objective is the specification's own field. The base revision is the
commit observed at attempt start, before the implementation command. The
candidate revision is the post-implementation HEAD when the attempt moved it,
and is unmeasured with the reason when it did not, because an uncommitted
worktree is not a revision. The acceptance identifiers are the contract's, one
per acceptance command, and the run loop stops at the first failing command,
so the record carries three disjoint lists — completed, failing, and not run —
that together cover the contract's identifiers; an identifier whose command
never ran is in neither the completed nor the failing list. The environment
state carries the mode, the controller epoch, and the per-command timeout; the
tokens and the cost are null and never estimated, and no environment digest is
computed. The commands actually run are this run's results. The unresolved
effects and the remaining budget are unmeasured: the contract's external
effects are a declaration and not an observation, and the declared repair
allowance is not the budget that remains, because the factory tracks no
consumption. The next eligible action is one of three closed values —
`product_review`, `bounded_repair`, or `controller_decided` — and it says
whether the factory or the successor decides it, and it names the observed
evidence: the exit code of the implementation command, or the identifier and
exit code of the failing acceptance command, or the run's own detail.

The finding the prompt-writing agent measured and the primary agent
re-measured: the manifest's `repository` block was built by a fresh
`repository_identity(workspace)` probe at manifest-write time, after the
command loop, while the block's own source string said "git rev-parse HEAD
observed at attempt start". In an attempt that commits, the manifest held the
new commit under the label of the attempt-start one, while the recall's copy
held the old one. The manifest now uses the attempt-start identity that the
recall already holds, so the two artifacts cannot disagree and the source
string is true. The record's base revision is that same observation.

The record is context and never a verdict: the verifiers, the publish gate,
the state machine, the ledger schema, the monitor, the codemap, the recall,
the skills reader, and the workspace-diff capture semantics are unchanged, and
a write that fails is recorded with its reason and leaves the attempt exactly
as it was.

```text
python3 scripts/check
python3 scripts/check-doc-references
grep -n "overseer.factory\|overseer.codemap" overseer/handoff.py
grep -rn "TODO\|FIXME\|XXX" overseer/handoff.py overseer/factory.py
```

Fifteen tests were added in `HandoffRecordTests` and the suite runs 350
tests. Each of the fourteen mutations was applied alone and failed the suite:
M1 the base revision taken from a later probe
(`test_the_base_revision_is_the_attempt_start_commit`); M2 the identifiers
mapped off by one, so the implementation result names the first identifier
(`test_the_failing_acceptance_identifier_is_reported_alone` and three more);
M3 the not-run identifiers counted as failing
(`test_the_checks_after_the_first_failure_are_not_run` and one more); M4 a
failed implementation counted as a failing acceptance identifier
(`test_a_failed_implementation_leaves_every_identifier_not_run` and three
more); M5 a timed-out command not counted as failing
(`test_a_timed_out_acceptance_command_is_failing`); M6 identifiers invented
when the stored job names none
(`test_a_job_stored_before_the_contract_rule_names_no_identifiers`); M7 tokens
given a number
(`test_the_environment_state_marks_tokens_cost_and_digest_unmeasured`); M8 the
remaining budget filled with the declared repair allowance
(`test_the_unresolved_effects_and_the_remaining_budget_are_unmeasured`); M9
the action always `product_review`
(`test_the_next_eligible_action_is_one_of_three_closed_values` and one more);
M10 the record written to a path shared by every run, so a later run overwrites
the earlier one (every test that reads the record, and
`test_a_later_run_leaves_the_earlier_record_byte_identical` first); M11 the
write of the record unguarded
(`test_a_failing_write_leaves_the_attempt_exactly_as_it_was`); M12 the record
carrying the command's output
(`test_the_record_carries_no_output_and_names_every_unmeasured_field`); M13
an unmeasured name dropped from the list
(`test_a_passing_attempt_writes_the_record_with_the_blueprint_fields` and
three more); M14 the manifest's handoff block carrying the wrong digest
(`test_the_manifest_the_summary_and_the_event_agree_with_the_file`). The
mutation set was run again, alone and reverted, against the final tree, and
each of the fourteen still failed the suite with the test named above. M10
was first written so that the later run overwrote the first run's directory,
which failed only when the run identifiers sorted that way, so it was rewritten
to a path shared by every run and now fails the same way every time.

Every citation of the pillar map was re-derived by hand after the last edit:
the eighty-five references that moved were remapped from a line map of the
committed file and the new one, each was checked to still name the thing it
claimed, and the new citations of `overseer/handoff.py` and of the lines that
write the record were checked the same way. The checker resolves 189
references.

Four departures from the prompt, all recorded here. The module grew a third
function, `candidate_revision(receipt)`, so that the manifest and the record
share one rule and cannot drift; the manifest's copy now calls it. The
`mode_result` and `attempt` blocks keep the value-and-source shape of every
other field, with their own `unmeasured` lists, so that the rule "every null
value is named in an unmeasured list and carries a reason" holds for them too;
the prompt's shape left them as bare objects. The manifest's new keyword is
`handoff_info` rather than `handoff`, because a keyword named `handoff` would
shadow the module inside the method. The prompt's line references were
measured at `9a88598` and were re-measured before anything was edited: all
resolved, and three of them name the first line of a block rather than its
first statement, which is correct.

### The handoff record read back and reconciled against the ledger and the workspace

The objective is the CONTEXT row's next increment, quoted: "read the persisted
handoff record back and reconcile it against the ledger row and the workspace
— the blueprint's 'the successor checks the ledger and workspace before
trusting the summary; if they disagree, reconcile'
(`docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299`) is still done by hand, and no
code reads handoff.json". It is filed against CONTEXT, because the
reconciliation is the successor's side of the context the handoff record
carries; no other row's verdict changes. The prompt is
`CONTEXT_HANDOFF_RECONCILE_NEXT_PROMPT.md`, which states that it was written by
the dedicated prompt-writing agent; it is committed with this increment. It was
executed in two sessions. The first, an OpenCode session, did Phase 0 and
Phase 1 and wrote a first `overseer/reconcile.py`, and then the operator paused
it. The second, a Claude Code session, resumed at Phase 2 from that session's
handoff block, verified the tree against it (HEAD `fcf5586`, the test file's
digest `491ff0f9…3c3121`), and did the rest. There is no `SPEC.md`; the blueprint
sentence and the CONTEXT row are the ground truth, and both were re-read.

The ten decisions were settled in the prompt and are kept. The module is
`overseer/reconcile.py`; it imports only the standard library, reads no ledger,
and starts no process, and the grep for `overseer.factory`, `overseer.codemap`,
and `subprocess` in it prints nothing. The factory's surface is
`Factory.reconcile_handoff(job_id)`, which holds the worker lock, and the CLI's
is `reconcile-handoff <id>`, a name that cannot be confused with the existing
`reconcile`. The ledger facts are the `jobs` row and the job's latest `handoff`
event. The workspace facts come from `workdiff.snapshot(workspace,
hold=False)`, the existing read-only snapshot. The disagreement list is closed
at nine kinds, and every entry names both sides. The verdict is closed at
three values: a disagreement outranks an unverifiable fact, and an
unverifiable fact is never agreement. The result goes to three places and no
fourth: `reconciliation.json`, a `reconciliation` key in `summary.json`, and one
`reconciliation` event. The bounds are 64 KiB per record, 64 levels of
nesting, 20 identifiers, and 32 disagreements.

Two of the decisions depart from the brief's wording, each for a measured
reason. The `jobs` table has no commit column (`overseer/factory.py:411`), so
no attempt-start commit can be read back out of the ledger. The revisions are
therefore anchored in the workspace: `candidate_revision_mismatch` when the
record says HEAD moved and the workspace's HEAD is not that commit, and
`base_revision_unanchored` when the workspace's HEAD is neither the record's
base nor its candidate. The context manifest is not rewritten either. Its digest
is already recorded in the `context_manifest` event and in `summary.json`, so
rewriting it would leave the ledger claiming a digest the file no longer has.
The report says so with `manifest_updated: False` and a `manifest_reason`.

Smaller departures. The secret-name function is `is_secret`, not the prompt's
`is_secret_path`, because the red test imports `is_secret`; a test holds it
equal to `overseer.codemap.is_secret`, and the duplication is deliberate so
that the module imports nothing from codemap. The module does not import `re`,
because nothing in it needs it. The factory reads `summary.json` to add its
one key; that is the only file besides the record that the reconciliation
opens, and it opens it to add to it, not to compare it. The report carries four
keys beyond the prompt's shape: `not_applicable` (a revision comparison that
does not apply because the record carries no such revision), `disagreements_beyond_bound`,
`written`, and `written_reason`. A `spec` column that is not JSON, or a
contract that is not an object, makes the identifier check unverifiable rather
than raising. A `handoff` event whose detail carries no digest is reported
with that detail as the reason.

The red-green separation, with its two returns to Phase 1. The first session
ended Phase 1 with 21 new tests in `class HandoffReconciliationTests`, red as
20 errors and 1 failure, and the test file at
`491ff0f9012383a5576375838ef0255f0c22657130f97e7d63b9f554c63c3121`. In Phase 2,
20 of 21 passed, and `test_the_reconciliation_never_writes_to_the_workspace_or_to_git`
failed on the index file's `st_mtime_ns`. A probe outside the suite showed that
`workdiff.snapshot()` leaves the index untouched, and that the test's own
`git status --porcelain` rewrites it: that call runs without
`GIT_OPTIONAL_LOCKS=0`, and git refreshes a racily clean index. In the test,
that call ran before the index was stat'ed, so the test failed whatever the
implementation did. Phase 1 was re-entered and the index assertion was moved
ahead of the test's own git calls, with nothing else changed. The red check
was re-run on a `git archive HEAD` export with only the new test file copied
in: 21 tests, 20 errors and 1 failure, digest
`def20136301fc877b9bd55c5c9bd3e0dfeb93847f97a6e86567526bb9418e2d1`. In Phase
3, M11 survived. The only identifier test named an identifier outside the
contract, and a subset comparison flags that too. Phase 1 was re-entered a
second time to add one assertion to
`test_acceptance_identifiers_that_do_not_match_the_stored_contract_are_a_disagreement`:
a record whose lists are empty is a mismatch against a contract that names
`A1`. The red check on a fresh export again gave 21 tests, 20 errors and 1
failure. The final Phase 1 digest is
`305bfddb872e2ac6542cfcb6f808c3bf4d82ade95b212d4489fb2bc440f1e779`, and the
digest at the end of Phase 2, through Phase 3 and Phase 4, is the same
`305bfddb…40f1e779`. No implementation file was written while `tests/` was
open in either return.

The first session's `overseer/reconcile.py` was 341 lines. It lacked the
`workspace` entry in `unverifiable` that the not-a-git-repository test
requires, so it was rewritten: the identity comparison is a table, the report
blocks are built from key tuples, and the module is now 298 lines, under the
300-line flag of `HARDENING_BLUEPRINT.md`. `overseer/factory.py` grew by 83
lines, from 2304 to 2387, which is 3.6% and far below the 15% limit.

The commands and their real output on the final tree:

```text
$ python3 scripts/check
Ran 371 tests in 44.441s
OK
$ python3 scripts/check-doc-references
204 references checked in HARNESS_FRAMEWORK.md
$ grep -n "overseer.factory\|overseer.codemap\|subprocess" overseer/reconcile.py
(no output, exit 1)
$ python3 -m overseer.factory --db <scratch>/jobs.sqlite3 reconcile-handoff demo
verdict agree, 0 disagreements, unverifiable [], written True; exit 0
$ python3 -m overseer.factory --db <scratch>/jobs.sqlite3 reconcile-handoff nope
{"error": "unknown job"}; exit 1
```

The test count went from 350 to 371, and the reference count from 189 to
204.

The mutations, one at a time on implementation code only, each run against the
new class alone and restored byte for byte (the `sha256sum` of every
`overseer/*.py` was checked after the set):

- M1, the state comparison dropped: `test_a_ledger_state_changed_after_the_attempt_is_a_disagreement`,
  `test_the_reconciliation_does_not_resolve_a_disagreement`, `test_the_record_itself_is_not_rewritten`.
- M2, a disagreement verdict reported as `agree`: the same three tests.
- M3, `unverifiable` reported as `agree`: the missing-record, JSON-array,
  wrong-typed-field, not-a-git-repository, and git-unavailable tests.
- M4, the digest check dropped: `test_a_tampered_record_whose_digest_differs_from_the_ledger_is_a_disagreement`.
- M5, the identifiers compared against the record's own lists:
  `test_acceptance_identifiers_that_do_not_match_the_stored_contract_are_a_disagreement`.
- M6, `GIT_OPTIONAL_LOCKS` set to `1` in the workspace snapshot's git runner:
  `test_the_reconciliation_never_writes_to_the_workspace_or_to_git`.
- M7, a malformed record's reason not recorded as unverifiable: the
  missing-record, JSON-array, and wrong-typed-field tests.
- M8, the reconciliation calls `transition`: `test_the_reconciliation_never_changes_the_job_state`.
- M9, the reconciliation rewrites `handoff.json`: the agree, tampered-digest,
  and record-not-rewritten tests.
- M10, the identifier lists compared in order: `test_the_identifier_lists_are_compared_as_sets`.
- M11, the identifier comparison made a subset test:
  `test_acceptance_identifiers_that_do_not_match_the_stored_contract_are_a_disagreement`,
  after the second Phase 1 return; before it, M11 survived.
- M12, a disagreement without its authority side: the job-id, run-id,
  spec-hash, state, candidate-revision, identifier, and digest tests.
- M13, the `unverifiable` list emptied in the report: the missing-record and
  not-a-git-repository tests. The git-unavailable test asserts the reason
  in the report's `workspace` block and not in the list, so it does not catch
  M13.
- M14, `ValueError` removed from the CLI's error handler: `test_the_cli_reports_an_unknown_job_as_a_json_error`.
- M15, the reconciliation rewrites `summary.json`'s `state`:
  `test_the_result_is_recorded_in_the_evidence_directory_the_summary_and_the_event`.

The citations. Every `overseer/factory.py` citation in
`docs/HARNESS_FRAMEWORK.md` was shifted by the measured hunks: +1 after the
import, +81 after the two new methods, and +83 after the CLI lines. Each
shifted line was then compared by content with the line it named at `fcf5586`.
All 78 distinct citations matched, and no cited range straddles an
insertion. The `tests/test_factory.py` citations all lie before the new class
and did not move. The fifteen new citations were read by content.

The limits that remain. The reconciliation reports a disagreement and nothing
acts on it. It never re-reads the run's own results: the identifier lists are
checked against the contract the ledger stored, not against the exit codes the
commands produced, so a record that was written wrongly and digested
faithfully is reported as agreeing. The ledger holds one evidence pointer per
job, so only the latest run's record is reachable through it. Whether the
worktree is dirty is reported and not compared. A workspace that moved on
after the attempt is reported as an unanchored revision, which is not proof
that the record is wrong.

### The handoff record's identifier lists reconciled against the recorded exit codes

The user asked: "Close the reconciliation gap in `overseer/reconcile.py` and
`overseer/factory.py`: 1. Modify reconciliation so it compares the handoff
record's completed/failing/not-run acceptance IDs not just against the ledger
contract, but against the actual command exit codes and run evidence (e.g.,
verifying that claimed "completed" IDs actually map to successful execution
exits). 2. Ensure any mismatch surfaces a proper disagreement
dictionary/report instead of blindly trusting a faithful but incorrect record.
3. Add a corresponding test case in `tests/test_factory.py`. 4. Adhere strictly
to AGENTS.md hardening mandates." It is the first half of the CONTEXT row's
previous next increment, and it is filed against CONTEXT; no other row's
verdict changes. The prompt, `CONTEXT_RECONCILE_RESULTS_NEXT_PROMPT.md`, was
written by the dedicated prompt-writing agent and executed by the primary
agent; it is committed with this increment.

The six decisions were settled in the prompt and are kept. The authority for
the exit codes is `commands_actually_run` in the run's `context.json`, because
its digest is sealed in the ledger's `context_manifest` event in the same
transaction as the final state change. `results.json` is rewritten after every
command and has no digest anywhere, and `summary.json`'s `results` has no
digest and is itself rewritten by the reconciliation, so neither is an
authority; the record's own `commands_actually_run` is part of the record
under test. The ledger digest proves that the factory's record is unchanged
since the attempt, not that the factory observed the exits correctly, and the
report's `results.source` says so. The classification rule is one function:
`handoff._acceptance` became the public `handoff.acceptance` and the
reconciliation applies it to the manifest's commands, so the record and its
check cannot drift apart; a test asserts the two names are the same object.
The new disagreement kind, `acceptance_results_mismatch`, takes the closed
list from nine to ten; the three lists are compared as sets, and one entry
names both sides in full plus each differing identifier with its recorded exit
code, bounded at 20. A manifest the ledger did not seal, that is missing,
oversized, re-digested, malformed, or whose command list has the wrong shape
is unverifiable with an exact reason, and a job with no usable contract
records the results check as not applicable. The report stays read-only and
keeps its three writes; it gains a `results` block. The bounded readers moved
out of `reconcile.py` into the new leaf module `overseer/readback.py`, with
their reason strings unchanged for the record, and the factory reads both
recorded digests through one `_recorded_digest` lookup. No departure from the
prompt was needed.

The red-green separation held with no return to Phase 1. Phase 1 added two
helpers, one optional helper, and ten tests to `HandoffReconciliationTests`;
the class ran 31 tests and failed with 7 failures and 3 errors, all ten in the
new tests, and the 21 existing tests passed. The digest at the end of Phase 1
was `d16240453ae9192eb1275c00a85128109b772db189015995b1975078d4bd270d`, and it
is the same at the end of Phase 2 and after Phases 3 and 4. The class passed
on the first green run.

Line counts, before and after: `overseer/reconcile.py` 298 to 256,
`overseer/readback.py` new at 174, `overseer/factory.py` 2387 to 2395 (8
lines, 0.3%), `overseer/handoff.py` 287 to 287 (the rename only).

The commands and their real output on the final tree:

```text
$ python3 scripts/check </dev/null
Ran 381 tests in 53.123s
OK
$ python3 scripts/check-doc-references
208 references checked in HARNESS_FRAMEWORK.md
$ grep -n "overseer.factory\|overseer.codemap\|subprocess" overseer/reconcile.py overseer/readback.py
(no output, exit 1)
$ python3 -m overseer.factory --db <scratch>/jobs.sqlite3 reconcile-handoff demo
verdict disagree, ['acceptance_results_mismatch'], A2 recorded completed,
derived failing, exit_code 3; exit 0
$ python3 -m overseer.factory --db <scratch>/jobs.sqlite3 reconcile-handoff nope
{"error": "unknown job"}; exit 1
```

The demo job ran two checks; the second exited 3, so the job failed, and the
record was forged to list A2 as completed and resealed. The test count went
from 371 to 381 and the reference count from 204 to 208.

The mutations, one at a time on implementation code only, each run against the
class alone, and every `overseer/*.py` restored byte for byte by digest:

- M1, the disagreement never appended: T1, T3, and T8.
- M2, the categories compared as ordered lists: the existing
  `test_the_identifier_lists_are_compared_as_sets`.
- M3, the manifest digest check skipped: T5.
- M4, an unread authority appending nothing: T4, T5, T6, and T7.
- M5, the authority derived from the record's own commands: T1 and T8.
- M6, the authority read from `results.json`: T1 and eight more.
- M7, the manifest digest taken from the `handoff` event: T1, T2, and six more.
- M8, the per-identifier detail emptied: T1 and T3.
- M9, the mismatch appended to `unverifiable`: T1, T3, and T8.
- M10, the command-shape validation removed: T5.
- M11, the size bound removed and the whole file read: T6. Removing only the
  pre-open size check is not observable, because the capped read gives the
  same reason, so M11 removes the bound as a whole.
- M12, the reconciliation rewriting `context.json`: T1, T8, and the existing
  `test_the_result_is_recorded_in_the_evidence_directory_the_summary_and_the_event`.

The citations. Every `overseer/factory.py` citation was shifted by the
measured hunks (unchanged up to line 1437, +4 and +6 between the edited hunks,
+8 after line 1477), and each shifted line was compared by content with the
line it named at `2ef797d`: all 78 distinct citations matched. The eight
`overseer/reconcile.py` citations were re-derived by content, and the bounded
read now cites `overseer/readback.py`. The `tests/test_factory.py` citations
lie before the new tests and did not move. The four new citations were read
by content. The earlier entry's sentence that `summary.json` "is the only file
besides the record that the reconciliation opens" is superseded:
`context.json` is now read too, and never written.

The limits that remain. The reconciliation reports a disagreement and nothing
acts on it. The exit codes it checks the lists against are the factory's own
record in the context manifest: the ledger digest proves that record
unchanged since the attempt, not that the factory observed the exits
correctly, and the per-command logs are not re-read. The ledger holds one
evidence pointer per job, so only the latest run's record and manifest are
reachable through it.

## 2026-10-20 — Hardening blueprint rewrite and the repair-lineage freeze

### User objective and order

The operator asked, in order: (1) rewrite the mediocre `HARDENING_BLUEPRINT.md`
to the rigor of `docs/AUTONOMY_BLUEPRINT.md`, choosing between folding it into
the measurable frame (option a) or quarantining it as principles (option b);
(2) implement autonomy increment 1, the repair lineage and three-strike freeze.
Option (a) was chosen. A full project evaluation and a `DESCRIPTION.txt` were
also produced earlier in the same session.

### The hardening blueprint, wired to the code

`HARDENING_BLUEPRINT.md` was rewritten from aspirational prose into a
measured document. It is anchored to commit `f28bb7d`; every `path:line`
resolves with `python3 scripts/check-doc-references HARDENING_BLUEPRINT.md` (34
references). Each of the five failure modes now carries a status vocabulary
(IMPLEMENTED / DATA-ONLY / BY DISCIPLINE / FILED / OUT OF SCOPE), a citation or
a filing for every signal and mitigation, a §0 tying it to the harness map and
the autonomy plan, the real table of seven over-300-line files with the rule
scoped to new modules, two honest corrections (the per-command timeout and
SIGKILL at `overseer/factory.py:1536`, not a fixed 60 s; one SQLite ledger with
git as read-only revision authority, a deliberate divergence from "derive all
state from git"), a scorecard, and a "what hardening cannot detect" section.
The LaTeX notation was removed. The file stays at the repository root so the
autonomy blueprint's references to it keep resolving.

### Increment 1: repair lineage and the three-strike freeze (STATE)

Red-green, one commit. Phase 0 re-read the increment 1 spec and the factory
schema, `submit`, `run_one`, `resolve`, `cancel`, `_ensure_side_tables`,
`backup`, and `restore`. Phase 1 wrote the nine named tests as
`tests/test_factory.RepairLineageTests` and recorded the file digest
`169b78b2aaa89a1fc808d5f5f8cb2d9c9f9e8dbb96a393bd80773a0cde34ba35`; all nine
failed ("no such table: lineages"). Phase 2 implemented it; the test digest was
unchanged after the green phase.

New module `overseer/strikes.py` (192 lines, under the 300-line rule; over the
blueprint's ≤160 estimate — recorded honestly as the one deviation). It is
self-contained ledger logic over a passed-in sqlite3 connection: it never
imports `overseer.factory` or `subprocess`, runs no command, and reads no file
outside the database. It holds the schema for two tables (`repairs`,
`lineages`), the bound (`bound_for`), the strike test, the lazy lineage
creation, `join_lineage`, `record_terminal`, and `release`.

`overseer/factory.py` grew by a net +33 lines (within the +40 budget), all
small call sites: `strikes.ensure_tables` in the schema (`:459`) and in
`_ensure_side_tables` (`:2033`); a `repair_of` keyword on `submit` whose join
(`:494`) runs inside the submit transaction so a frozen-lineage refusal rolls
the new job back; `strikes.record_terminal` inside the terminal transaction of
`run_one` (`:2352`) and of `resolve` (`:784`), placed before the transition's
own event so the terminal state stays the job's last event; and a public
`lineage` read (`:787`) and `release` method and CLI subcommand (`:791`), plus
`--repair-of` on `submit`.

Design decisions settled in the implementation, matching the blueprint's
recommended answers: two tables, `lineage_id` keyed by the root job id; a strike
is a terminal `failed` state only (`passed` closes, `cancelled`/refused are
neither); `bound = min(3, 1 + repair_allowance)` with `bound_source` naming
which limit applied; a freeze raises on a further `submit(..., repair_of=...)`
and never changes a job state; `release(lineage, decider, note)` requires both
and resets the count; both tables survive backup and restore (the whole-db
backup copies them, and `_ensure_side_tables` recreates them when a pre-schema
backup is restored). One scoping choice beyond the blueprint: only command-mode
jobs carry a lineage, so the fixture, fake-provider, and isolation-probe tests
are untouched. Verified that no existing test asserts a full event sequence, and
that the two `ORDER BY seq DESC LIMIT 1` assertions both expect the
post-reconcile event; recording the strike before the transition keeps them
valid.

### Verification

- `python3 -m unittest tests.test_factory.RepairLineageTests`: 9 tests, OK.
- Full suite: `Ran 390 tests ... OK` (was 381; +9).
- Mutations confirmed to fail the suite, each reverted after: bound fixed at 4
  (caught by `test_three_consecutive_failures_freeze_the_lineage`); `passed` not
  closing (caught by `test_a_passed_attempt_closes_the_lineage`); the strike
  skipped in `resolve` (caught by `test_a_resolved_interrupted_attempt_counts_as_a_strike`).
- `python3 scripts/check-doc-references`: 208 in HARNESS_FRAMEWORK.md, 66 in
  AUTONOMY_BLUEPRINT.md, 34 in HARDENING_BLUEPRINT.md, all resolving.

### Citations re-derived by content

The +33-line `overseer/factory.py` edit shifted every later line. All 131
`overseer/factory.py:NNN` citations across the three harness docs were re-mapped
by content with a difflib old→new line map (HEAD vs the working tree), not by
hand; none were left unmapped, and the file end moved 2395→2428 (+33),
consistent with the measured delta. Spot checks confirmed the new targets
(`def execute` at `:1556`, `def worker_lock` at `:720`, `def run_one` at
`:2170`, `def restore` at `:2121`). Citations into `tests/test_factory.py` sit
before the appended class and did not move; no other `overseer/*.py` file
changed, so their citations were left alone.

### Docs updated

The STATE pillar row of `docs/HARNESS_FRAMEWORK.md` now records the lineage with
its citations, verdict, and next increment; `docs/AUTONOMY_BLUEPRINT.md` marks
M3-a and increment 1 as landed with the one size deviation noted;
`HARDENING_BLUEPRINT.md` moves the repair-lineage strike count from FILED to
IMPLEMENTED in Pillar 3 and the scorecard; `README.md` gains the repair-lineage,
freeze, and release paragraph.

### Limits that remain

The freeze is a cost cap, not a diagnosis: a worker that changes its patch each
time produces "new evidence" by the (not-yet-built) fingerprint rule and runs
to the bound. Nothing consumes `repair_allowance` beyond the bound; it is not
the remaining budget. The lineage lives in the factory ledger only; the
monitor's pane hold (increment 6) is a separate store. Increments 2–10 of the
autonomy blueprint are still owed before unattended operation.

### Increment 2: the status-block parser (CONTEXT)

Red-green, one commit, no change to any existing file. Phase 0 re-read the
increment 2 spec and the monitor's sent-line rule (`overseer/policy.py`: the
`ANSI` regex and `_controls`, ord < 32 or == 127). Phase 1 wrote the eight named
tests as `tests/test_statusblock.py` and recorded the digest
`c5e4cd0b6daaf272b9e17eeeec3c6e2b78e0033df0ca82d31108f52fe06118e4`; they failed
on the missing module. Phase 2 implemented `overseer/statusblock.py` (123 lines,
under the 180 budget); the test digest was unchanged after the green phase.

The parser reads the AGENTS.md worker status block out of bounded text: the last
complete four-line block (STATUS, TESTS_PASSED, FILES_MODIFIED,
NEXT_AGENT_INSTRUCTION, in order) wins, ANSI is stripped, and only the last
64 KiB is considered. Values are closed: STATUS in {SUCCESS,
STUCK_NEEDS_ESCALATION}, TESTS_PASSED in {TRUE, FALSE}, FILES_MODIFIED a
bracketed list of at most 200 entries, and the instruction a JSON-quoted string
decoded with `json.loads` as data — never evaluated — at most 4000 characters
and no control character. The unfilled template line
`[SUCCESS | STUCK_NEEDS_ESCALATION]` is "template not filled", and every
over-bound or unknown value is reported invalid with its reason, never truncated
into validity. Result shape: `{found, valid, reason, status, tests_passed,
files_modified, next_instruction}`.

Decision settled beyond the spec letter: the control-character rule and the ANSI
regex are imported from `overseer/policy.py` rather than re-implemented, so the
parser and the monitor stay in step; the length bound for the instruction is the
spec's 4000, not the monitor's 1000 `MAX_PROMPT`. This is the only cross-module
dependency; the module otherwise uses the standard library alone, and no other
file changed.

Verification:
- `python3 -m unittest tests.test_statusblock`: 8 tests, OK.
- Full suite: `Ran 398 tests ... OK` (was 390; +8).
- Mutations confirmed to fail the suite, each reverted: first block wins (caught
  by `test_the_last_block_wins`); template accepted (template test); truncation
  instead of rejection (over-long test); status values not closed (unknown-status
  test).
- `check-doc-references`: all three docs still resolve. No existing `.py` file
  changed, so no citation moved and none needed re-deriving.

Docs: the CONTEXT pillar row records the parser and says plainly that no caller
reads it yet; `AUTONOMY_BLUEPRINT.md` marks M3-b and increment 2 landed;
`HARDENING_BLUEPRINT.md` moves the explicit-escalation detection to PARTIAL
(parser built, acting on it still filed). `README.md` is intentionally
unchanged: increment 2 adds no command and no observable behavior — the parser
has no caller until increment 3.

Limit that remains: the parser is pure data extraction. Nothing yet reads a
worker's block, so `STUCK_NEEDS_ESCALATION` still triggers nothing; increments 3
(factory) and 6 (monitor) wire it in.

### Increment 3: worker report as evidence; stuck-escalation freezes the lineage (EVIDENCE)

Red-green, one commit. Phase 0 re-read the increment 3 spec and the run_one tail
(the implementation log `00.log`, the exit-code decision of `final`, the final
transaction, and `_context_manifest`). Phase 1 wrote the five named tests as
`tests/test_factory.WorkerReportTests` and recorded the digest
`7757e3b7d79d1ef06fa6f501b12140306043a915cc7dd701d2359c799565db3c`; all five
failed on the missing `worker_report.json`. Phase 2 implemented it; the test
digest was unchanged after the green phase.

New module `overseer/workerreport.py` (62 lines, under the 150 budget). It reads
the last 64 KiB of the implementation command's `00.log` — the size is checked
before the file is opened and the read is bounded to the tail — parses the block
with `overseer/statusblock.py`, and returns a record: the parsed block, the
bytes read and their sha256, whether the log was truncated, whether a
`TESTS_PASSED: TRUE` claim disagrees with the exit-code outcome, and whether the
block asks to escalate. It is evidence, never a verdict.

`overseer/factory.py` grew by +25 lines (inside the +30 budget): the capture and
write before the manifest, a `worker_report` pointer and digest in the manifest,
the `worker_report` event that seals the digest in the final transaction, and
the escalation call after the strike so the escalation reason is the one
recorded. `overseer/strikes.py` gained `freeze_for_escalation` (now 212 lines,
under 300): a job with an open, released, or frozen lineage is frozen with the
escalation reason, and a job with no lineage — or one already closed on a pass —
gets an `escalation_requested` event, since there is nothing to freeze. Only
command-mode runs with a `00.log` are captured, so the fixture, fake-provider,
and isolation-probe runs are untouched.

Decisions settled: exit codes decide the state (the claim is recorded as
`claim_disagrees` and changes nothing); the handoff record's ten fields are
unchanged and the manifest gains only a pointer and a digest; a missing or
invalid block is recorded with its reason and is not a strike by itself. In the
escalation freeze test the contract sets `repair_allowance: 2` (bound 3) so a
single strike cannot freeze the lineage and only the escalation can, which
isolates the escalation path from the strike path.

Verification:
- `python3 -m unittest tests.test_factory.WorkerReportTests`: 5 tests, OK.
- Full suite: `Ran 403 tests ... OK` (was 398; +5).
- Mutations confirmed to fail the suite, each reverted: the claim decides the
  state (caught by the claim test); escalation ignored (freeze test); the whole
  log read (tail test); the digest event omitted (recorded test). The first two
  attempts at the escalation and digest mutations left dangling continuation
  lines; they were redone as single-line, compiling mutations that failed the
  right test.
- No existing test pins the manifest key set, so the new `worker_report` key is
  safe; no existing test asserts a full event sequence, and recording the
  `worker_report` event and the escalation before the final transition keeps the
  terminal state the last event.

Citations re-derived: the +25-line `overseer/factory.py` edit shifted later
lines, so all 143 `overseer/factory.py` citations across the three harness docs
were re-mapped by content with the difflib old→new map (HEAD vs the working
tree); the file end moved 2428→2453. `check-doc-references` resolves for all
three docs.

Docs: the EVIDENCE pillar row records the worker report with its citations and
the honest limit that the monitor side of escalation is still unbuilt;
`AUTONOMY_BLUEPRINT.md` marks M3-c and increment 3 landed; `HARDENING_BLUEPRINT.md`
moves the explicit-escalation detection to PARTIAL (parser and factory action
built, monitor action filed); `README.md` gains the worker-report paragraph.

Limit that remains: the factory acts on a stuck block, but the monitor does not
yet react to a stuck block in a live pane; increment 6 adds that. A claim is
recorded, never trusted; a worker that lies about success cannot change the
exit-code verdict, but nothing proves the block itself is honest.

### Increment 4: the no-new-evidence early freeze (EVIDENCE)

Red-green, one commit. Phase 0 re-read the increment 4 spec, `handoff.acceptance`
(reused for the failing/not-run identifiers), and the run_one tail. Phase 1 wrote
the three named tests as `tests/test_factory.NoNewEvidenceTests` in a git
workspace (the changed-patch case needs a real patch digest) and recorded the
digest `5a46e5fb5e6a8330818b4f383fe1181b977646706aab097d758ba24e4a7c578c`. Red
was one failure (the positive freeze test) with the two "new evidence" guard
tests passing trivially, since nothing froze early yet; those guards earn their
keep against the mutations.

Implementation. `overseer/strikes.py` (now 257 lines, under 300; the added logic
is inside the +60 budget): a `fingerprint(failing_ids, not_run_ids, exit_code,
timed_out, patch_digest)` that returns a byte-stable sha256 of a sorted payload;
a `strike_evidence(job_id, lineage_id, run_id, fingerprint, at)` table created by
`ensure_tables`; and an early-freeze branch in `record_terminal` that, given a
fingerprint, compares it with the lineage's most recent prior strike fingerprint
and, on a byte-equal repeat below the bound, freezes with a reason naming both
run ids. `overseer/factory.py` grew by +12 lines (inside +15): it builds the
fingerprint of a failed command-mode attempt from `handoff.acceptance` and the
diff receipt's `patch_sha256`, and passes it with the run id to
`record_terminal`. `resolve` passes no fingerprint, so an operator-resolved
interruption never early-freezes.

A real interaction surfaced and was handled honestly: increment 1's
`test_three_consecutive_failures_freeze_the_lineage` used three identical failing
jobs, which the new early freeze (correctly) froze at strike 2 instead of the
bound. The test was updated to give each attempt a distinct exit code — new
evidence each time — so it still tests the bound. This is test maintenance driven
by the feature's semantics, not weakening: the bound assertion is unchanged, and
the scenario now actually exercises the bound. The increment-4 red digest was
already honoured (the new class passed with the file at that digest before this
unrelated edit).

Verification:
- `tests.test_factory.NoNewEvidenceTests`: 3 tests, OK.
- Full suite: `Ran 406 tests ... OK` (was 403; +3).
- Mutations confirmed to fail the suite, each reverted and re-parsed: the patch
  digest dropped from the fingerprint (caught by the changed-patch test); the
  identifiers dropped (different-identifier test).
- All 149 `overseer/factory.py` citations across the three harness docs re-mapped
  by content (file end 2453 to 2465); `check-doc-references` resolves for all.

Docs: the EVIDENCE pillar row records the fingerprint and the honest limit that a
changing patch is new evidence; `AUTONOMY_BLUEPRINT.md` marks increment 4 landed;
`HARDENING_BLUEPRINT.md` moves the no-new-evidence repeat to IMPLEMENTED in Pillar
3 and the scorecard; `README.md` gains the early-freeze sentence.

Limit that remains: the fingerprint is byte-equal only. A worker that loops on a
design flaw while changing its patch each attempt produces new evidence by this
rule and runs to the bound; the early freeze caps an *unchanged* repeat, not a
disguised one.

### Increment 5: operator pause of factory dispatch (PERMISSIONS)

Red-green, one commit. Phase 0 re-read the spec and `run_one`'s dispatch
transaction. Phase 1 wrote the four named tests as `tests/test_factory.PauseTests`
(digest `2fa20209880851fc8dabca94ed1a0cf9d1f07f2f7c82151b9600261cbcda00a7`); the
dispatch test uses a small `_RecordingDB` proxy to assert the pause is read
*after* `BEGIN IMMEDIATE`, which deterministically catches a check placed outside
the transaction. Red was four errors on the missing pause API.

Implementation in `overseer/factory.py` (+36 lines; just over the +35 estimate,
under the +40 cap): a one-row `dispatch_pause(id, paused, note, at)` table in the
schema and in `_ensure_side_tables`; a pause read at the top of `run_one`'s
`BEGIN IMMEDIATE` transaction that rolls back and returns a JSON reason when
paused; `pause`/`unpause`/`_set_pause` methods that require a note and record it
under the worker lock; `pause`/`unpause --note` CLI subcommands; and a one-token
fix of `main`'s exit logic to `result.get('state')` so a paused run-one exits 1
without a KeyError.

Decisions settled: the pause is checked inside the dispatch transaction
(decision 1); a paused `run_one` returns `{dispatched: false, paused: true,
reason: ...}` and the CLI exits 1 (decision 2); the table lives in the ledger and
survives backup and restore (decision 3). It pauses dispatch, not running work:
`_set_pause` never touches the jobs table, and a job already `running` is left
alone.

Verification:
- `tests.test_factory.PauseTests`: 4 tests, OK.
- Full suite: `Ran 410 tests ... OK` (was 406; +4).
- Mutations confirmed to fail the suite, each reverted and re-parsed: the pause
  check moved before `BEGIN IMMEDIATE` (caught by the dispatch test's order
  assertion); the note requirement removed (caught by the unpause test).
- All 151 `overseer/factory.py` citations across the three harness docs re-mapped
  by content (file end 2465 to 2501); `check-doc-references` resolves for all.

Docs: the PERMISSIONS pillar row records the dispatch pause and keeps the honest
limit that it is not a pause of running work; `AUTONOMY_BLUEPRINT.md` marks M3-d
and increment 5 landed; `README.md` gains the pause/unpause commands.
`HARDENING_BLUEPRINT.md` is unchanged: the operator pause is a PERMISSIONS control
and maps to no one of the five hardening failure modes.

Direction note from the operator, mid-increment: "we need to make this real."
The factory still runs argument-vector worker commands against a fake worker in
the tests; no real model is invoked. The agreed next direction is a provider
adapter targeting OpenCode (the operator's machine cannot run a local Ollama
model), proven first on a single manually submitted job before the unattended
loop (increment 9) drives it. The safety brakes (increment 6 remains) still come
before any unattended sending.

### Making it real: the worker PWD fix, and a free model driven by the factory

Operator direction: "make this real." The factory had never invoked a model — a
job's implementation is an argv, and the whole suite uses a fake worker. We
targeted OpenCode (the operator's machine cannot run a local Ollama model).

Feasibility, verified on this machine:
- OpenCode v2.0.32 is installed; `opencode run` is its headless mode, with
  `--model`, `--format json`, and `--auto` (auto-approve edits).
- `opencode auth list` is empty, but `opencode models` lists `opencode/*-free`
  models served through OpenCode's gateway. `opencode/deepseek-v4.1-flash-free`
  ran headless with no auth, used its write tool to create a file, and reported
  cost 0.

Two integration facts found by probing:
1. `opencode run` without `--standalone` talks to a background `opencode serve
   --service`, which is rooted wherever it was started, not the job's workspace;
   `--standalone` runs a private server instead.
2. Even with `--standalone`, OpenCode trusts the `$PWD` environment variable over
   the actual working directory. The factory's `execute` ran the child with
   `cwd=workspace` but inherited `PWD=<factory's own dir>`, so OpenCode edited the
   factory's directory. This is a general correctness bug for any `$PWD`-trusting
   tool, not just OpenCode.

Fix (red-green, this commit): `overseer/factory.py:execute` now sets
`env['PWD'] = str(cwd)` for every worker command (+5 lines), with
`tests/test_factory.WorkerPwdTests.test_the_worker_environment_pwd_is_the_workspace`
asserting a worker sees `PWD` equal to its workspace. Red failed on the inherited
PWD; green passes. Full suite 411.

Proof it is real (scratch, not committed): a factory job whose implementation is
`opencode run --standalone --model opencode/deepseek-v4.1-flash-free --format
json --auto "Create calc.py ... add(a, b) ..."`, workspace a fresh git repo,
check `python3 -c "import calc; assert calc.add(2,3)==5"`. After the PWD fix the
job reached `passed`: the model wrote `def add(a, b): return a + b` into the
workspace, the diff receipt captured `calc.py` as added, acceptance `A1`
completed, and the worker report was captured (its block is invalid because the
`--format json` stream carries no line-start AGENTS.md block — recorded, not
invented). `candidate_revision` is null because the worker did not commit.

What is still not real: there is no provider-adapter module that constructs the
OpenCode invocation from an instruction, model, and workspace — today the argv is
hand-written in the task. The unattended feed loop (increment 9) needs that
adapter. The free models are rate/quality limited and their output is not the
AGENTS.md status block unless the prompt asks for text format. The safety brake
increment 6 (monitor-side hold) also remains before any unattended sending.
