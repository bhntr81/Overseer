# Software factory execution record

## Blueprint and skills integration

Overseer is the software factory project. Version 2 was moved unchanged from
Downloads to [SOFTWARE_FACTORY_BLUEPRINT_V2.txt](SOFTWARE_FACTORY_BLUEPRINT_V2.txt);
the original blueprint remains historical. Its stronger acceptance requirements
have not all been implemented by the existing trusted-command runner.

The [harness framework](HARNESS_FRAMEWORK.md) maps the blueprint's pillars onto
the current code and records which pillars are implemented, partial, or absent.

The dedicated `/root/skills_integration_prompt` authored the bounded integration
handoff. The primary agent installed three reviewed instruction-only skills from
`davidondrej/skills` at revision `27e2e3a63f36ef8c962dae08d5ed59b27d72249e`
using the system skill-installer helper: better-prompt, goal-loop, and
effective-agent-skills. Upstream file hashes match the reviewed checkout; MIT
licenses accompany the installations. [Integration](FACTORY_SKILLS.md) and
[provenance](../factory/skills-provenance.json) record scope and verification.
Runtime activation and usefulness remain untested; no provider run or controller
change was made in this integration.

## Authorship and scope

The dedicated `/root/factory_prompt_writer` authored the research and implementation
handoffs. The primary agent researched the sources, wrote the blueprint, implemented
the local runner, and executed its checks. `/root/factory_review` independently
reviewed the runner and verified the fixes. Shared coder_optimization task/review
and measurement guidance was applied. No measured model ranking is claimed.

The CEO, director, supervisor, QA, and Model Router roles are specified in
[the blueprint](SOFTWARE_FACTORY_BLUEPRINT.md). They are an organizational design,
not a claim that persistent autonomous supervisors have been deployed. The
routing-policy JSON is a proposal, not an active authority mechanism.

## Implemented

- `python3 -m overseer.factory`: explicit submit, status, inspect, run-one, cancel,
  reconcile, and resolve commands. SQLite records immutable task definitions,
  specification hashes, attempts, transitions, command results, and evidence.
- A single worker lock and transactional FIFO claim. Active or unresolved prior
  runs prevent new dispatch. Duplicate task IDs cannot change their acceptance.
- A gated child launch: task code begins only after its process group is recorded.
  Command timeouts kill the process group; per-command captured logs cap at 2 MiB.
- Separate implementation and acceptance commands. `passed` requires every
  command to exit successfully and is explicitly not product/release acceptance.
- Recovery tests for persistence/selector failure and a killed worker. Interrupted
  work is not automatically rerun. A recorded live child group prevents resolution.
- `scripts/check` isolates tests from the live tmux server.
- `.github/workflows/check.yml` defines a read-only CI check, using pinned checkout
  and setup-python action commits. It is not yet running on a remote repository.
- Private runtime state under `~/.local/state/overseer/factory`; profiles, downloads,
  and runtime artifacts are excluded from the source repository.

## Using the first slice

```sh
cd /home/kali/Projects/Overseer
python3 scripts/check
python3 -m overseer.factory submit factory/tasks/overseer-checks.json
python3 -m overseer.factory run-one
python3 -m overseer.factory status
python3 -m overseer.factory inspect overseer-foundation-checks-001
```

The example already ran successfully. Submitting it again is idempotent and will
not rerun a passed job. For a new run, create an explicitly reviewed task with a
new ID. Each task specifies an existing absolute workspace, an objective, one
implementation argv, one or more acceptance argvs, and a per-command timeout.
There is no implicit shell or automatic tool/model selection.

After an interrupted worker, use `reconcile`, inspect its evidence/workspace and
recorded child group, then `resolve ID --note 'what was inspected'` only after
checking actual effects. Resolution marks it failed rather than pretending it
passed or silently retrying it. A queued task can be cancelled with `cancel ID`.

## Observed validation

49 tests passed after recovery fixes. The independent reviewer reran the 12 factory
tests successfully. The suite covers immutable submission, real file changes,
independent failed checks, timeout, bounded logs, FIFO, cancellation, worker lock,
setup failure, and actual worker death. Existing monitor/queue/transport tests pass.

Persisted runs:

- `overseer-foundation-checks-001`: passed the initial real 45-test validation run;
  run `fc5e075ca6074e6c992c8a29ddd7b357`. This is local validation, not AI coding.
- `factory-fixture-pass-001`: changed `result.txt` in a private fixture workspace
  and passed an independent assertion; run `ba33f29d3c6d4cb78cb9812f7617844d`.
- `factory-fixture-fail-001`: deliberately mismatched acceptance and correctly
  failed; run `cc43db2d0cf6455eb34fa2fc848592c7`.

Each run's evidence is under the private factory `runs/RUN_ID` directory. Tokens
and cost remain null because no runtime billing measurement was supplied. These
fixture results are not provider benchmark data and were not appended to the
optimizer's provider-comparison dataset.

## Boundaries and next work

This worker executes explicitly trusted local command specifications. It is not a
security sandbox: commands run with the user's local privileges/environment and
can access files outside the workspace. Process-group cleanup does not constrain
malicious children that daemonize into a different session. Use disposable,
externally constrained workers before accepting less-trusted code. Do not place
credentials in task argument arrays or logs.

Workspaces are explicitly supplied; automatic worktree creation, immutable Git
revision enforcement, credential isolation, and tamper-resistant acceptance code
are not implemented yet. Freeze command definitions does not make files referenced
by those commands immutable. Independent review remains required.

The legacy terminal monitor remains running and unchanged. Its resource gate is
separate from this local runner; no provider-wide concurrency claim is made.
No provider workers, nested supervisor swarms, automatic repairs, GitHub issue/PR
integration, merge enforcement, release pipelines, or live Model Router are enabled
by this slice. All are acceptance-defined phases in the blueprint.

The local fake-provider slice is a closed controller-owned mode. Its scenarios
cover a good candidate, an incorrect candidate, a timeout, and an uncertain
interruption. A log line that says SUCCESS does not accept the incorrect
candidate. Acceptance goes through a publish gate bound to the current
controller epoch, attempt id, and lease generation. Reconciliation and lease
replacement supersede the old lease. SQLite backup and restore advance the
epoch, keep the lease counter from moving backward, and invalidate a passed
fixture or fake-provider job whose candidate is missing or no longer matches
its receipt. Fencing is committed in a staging database before the live ledger
is replaced, so a fencing failure leaves the live epoch and lease counter as
they were. An unreadable passed specification is invalidated instead of
aborting that fence. Temporary-database tests demonstrated those behaviors. This slice
is not an OS sandbox, and it does not finish M1.

An `isolation_probe` task runs one controller-owned bubblewrap profile. The
probe's disposable workspace is writable. Its ledger, credential, and other
workspace files are read-only, and those host bytes are checked after the
probe. The profile has no network route, a hard 128 MiB address-space limit
that the probe cannot raise, and a controller wall-clock kill for a sleep
command. Passing that probe does not make the trusted argv command runner a
sandbox, and it does not by itself finish M1. No real provider adapter,
including Codex, Claude, or Grok, is implemented. Do not enable unattended
provider dispatch from this slice.
