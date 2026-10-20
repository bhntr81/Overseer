# What must be done before enabling unattended provider dispatch?

**Status:** manual wiki trial based on local records dated 2026-10-19  
**Recommendation:** do not enable unattended provider dispatch yet.

The records do not establish that the remaining reliability, isolation, and
ledger-recovery gates have passed. Finish M1 with a fake provider first. Only
after those gates pass should Overseer consider a separately authorized M2
trial with one structured adapter, one bounded task, one provider slot, and an
independent protected verifier.

## Current recorded facts

- The current factory is a single-worker local command runner. It has no
  provider adapter, automatic worktree/revision enforcement, credential
  isolation, or tamper-resistant acceptance code. Its fixture pass/fail work
  does not establish those controls. See [P01](../../../docs/FACTORY_EXECUTION.md),
  “Implemented” and “Boundaries and next work.”
- The readiness record says fixture acceptance is complete, while stale-worker
  handling, proven runtime isolation, and ledger backup/restore remain open
  gates. It says authentication and model access have not been tested. See
  [P02](../../../docs/GROK_SUPPORT_READINESS.md), “Verified local facts,”
  “Prerequisites before an unattended adapter,” and “Actions requiring separate
  authorization.”
- The routing file sets `status` to
  `proposal_not_enforced_by_local_command_runner` and has all providers disabled.
  Its `global_provider_concurrency` value and budget rule are proposed policy,
  not proof that the runner enforces those limits. See
  [P03](../../../factory/routing-policy.json), fields `status`,
  `global_provider_concurrency`, `providers.*.enabled_for_factory`, and `rules`.

## Open prerequisites

These are blueprint/readiness gates, not claims that the work is already
implemented or that the checks have passed.

1. **Reliability and ownership:** demonstrate stale-worker fencing, crash and
   restart reconciliation, timeout and descendant handling, interrupted-run
   recovery, duplicate-dispatch protection, and failure drills. A stale worker
   must not publish or receive acceptance. See [P02](../../../docs/GROK_SUPPORT_READINESS.md),
   “Prerequisites before an unattended adapter,” and
   [P04](../../../docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt), sections “25. Build
   sequence with evidence gates” and “26. Required failure drills,” including
   backlog items F06 and the stale-worker scenarios.
2. **Proven isolation and resource controls:** run harmless boundary probes in
   the actual disposable worker environment. Show that worker code cannot write
   to the controller ledger, verifier rules, host credentials, or another
   workspace, and exercise filesystem, process, network, CPU, memory, disk, and
   time limits. A worktree, same-user file permissions, or a provider's own
   sandbox setting is not proof of containment. See [P04](../../../docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt),
   section “11. Safe execution is a prerequisite” and backlog item F07, and
   [P02](../../../docs/GROK_SUPPORT_READINESS.md), “Prerequisites before an
   unattended adapter.”
3. **Ledger recovery:** rehearse backup and restore in a disposable copy;
   validate referenced artifacts and their digests; restore under a fresh
   controller epoch; invalidate old leases; and reconcile in-flight effects
   before resuming dispatch. See [P04](../../../docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt),
   sections “9. Durable state and recovery” and “26. Required failure drills.”
4. **Independent acceptance for one real adapter:** keep verifier material
   outside worker write access and bind the verifier receipt to the exact
   candidate and run. After M1, prove this with one low-risk bounded real task
   through one structured adapter. Fixture verification alone is not this
   evidence. See [P02](../../../docs/GROK_SUPPORT_READINESS.md),
   “Prerequisites before an unattended adapter” and “Proposed next milestones
   and acceptance checks,” and [P04](../../../docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt),
   section “25. Build sequence with evidence gates,” item F08.
5. **Enforced dispatch and budget controls:** use a controller-enforced shared
   provider capacity gate, explicit budget/quota admission, and a one-writer,
   one-provider-slot limit for the first trial. The policy JSON alone does not
   enforce these limits. See [P02](../../../docs/GROK_SUPPORT_READINESS.md),
   “Prerequisites before an unattended adapter,” [P04](../../../docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt),
   section “12. Scheduling and useful parallelism,” and
   [P03](../../../factory/routing-policy.json), fields `status`,
   `global_provider_concurrency`, and `rules`.

The safest next engineering step is to finish and record M1 using a fake
provider; that does not require provider authentication or inference. M2 would
need a separate decision after M1 acceptance. See [P02](../../../docs/GROK_SUPPORT_READINESS.md),
“Proposed next milestones and acceptance checks.”

## Unknowns requiring authorization

- Provider authentication, entitlement, and model availability are unknown for
  a future adapter. Specifically, the local readiness record says Grok
  authentication and model access were not tested. See
  [P02](../../../docs/GROK_SUPPORT_READINESS.md), “Verified local facts” and
  “Actions requiring separate authorization.”
- No reviewed record establishes an approved spend budget or quota for a live
  provider task. The routing proposal lists `budget` as a required input but
  does not set or enforce a budget. See [P03](../../../factory/routing-policy.json),
  fields `required_inputs`, `status`, and `rules`.
- Login or credential setup, a provider prompt/API call, paid inference,
  provider configuration, or unattended dispatch requires separate
  authorization. See [P02](../../../docs/GROK_SUPPORT_READINESS.md),
  “Actions requiring separate authorization.”

## Traceability and usefulness assessment

The answer is direct: current records support “not yet,” followed by a concrete
M1-to-M2 sequence. Each prerequisite above has a link to a local record and a
section, backlog item, or policy field. The records describe required gates but
do not prove those gates have passed, establish provider entitlement, or supply
an authorized budget. This manual trial shows the wiki can make the decision
and its evidence easier to inspect; it is not a measured retrieval-accuracy,
time-savings, or cost result.

## Local source IDs

- P01: [Factory execution record](../../../docs/FACTORY_EXECUTION.md).
- P02: [Grok support readiness](../../../docs/GROK_SUPPORT_READINESS.md).
- P03: [Routing policy proposal](../../../factory/routing-policy.json).
- P04: [Software Factory Blueprint v2](../../../docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt).
