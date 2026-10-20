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
