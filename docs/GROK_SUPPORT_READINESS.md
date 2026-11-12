# Grok support readiness

**Reviewed:** 2026-10-19  
**Status:** planning only. Grok is installed locally; Overseer Grok integration,
authentication, and model access are not implemented or verified.

## Decision

There are two distinct integration paths:

1. **Interactive terminal monitoring:** recognize a Grok Build TUI pane and
   decide whether its screen is safe for Overseer to continue. This would extend
   the existing tmux monitor, whose process and empty-prompt checks currently
   allow only Codex and Claude. It would remain a heuristic terminal control
   path and could trigger a model turn.
2. **Structured factory worker:** dispatch one bounded task through Grok Build's
   noninteractive CLI and parse its result into the factory ledger. This is the
   closer fit for a software-factory job because the installed CLI's saved help
   shows single-turn mode and JSON output. It would still be an external model
   run and would execute agent tools unless those are explicitly constrained.

**Recommendation:** do not enable either path yet. Complete the remaining M1
reliability gates with a fake worker, then consider one Grok Build headless
adapter as an M2 pilot after separate authorization for authentication and a
bounded model request. Keep the provider routing proposal disabled until that
pilot passes its acceptance checks. The current project's existing single
worker path should be reused; no agent swarm or additional concurrency is
proposed.

The readiness work itself required no authentication or inference. An actual
Grok adapter run does.

## Verified local facts

- The install record reports Grok Build **1.0.62** in
  `/home/kali/.local/share/grok-build/1.0.62/grok`, linked from
  `/home/kali/.local/bin/grok`. It records successful version, help, and fresh
  shell resolution checks. See [DEVTOOLS_INSTALL_RESULT.md](internal/DEVTOOLS_INSTALL_RESULT.md)
  and the retained output in
  `../artifacts/devtools-install/20261019T031003Z/`.
- The saved 1.0.62 help output includes `-p/--single`, `--output-format`
  (including JSON), `--tools`, `--max-turns`, `--sandbox`, and a top-level
  `agent` command. The saved `grok login --help` includes `--device-auth`.
  These are local version/help observations only; no sign-in or model request
  was made. The saved help does **not** establish that this version supports
  the current docs' exact `grok agent stdio` interface.
- Overseer's interactive monitor and `overseer start` command whitelist Codex
  and Claude. `Tmux.Snapshot.ready` also checks for those process names and a
  small set of terminal prompt markers. Grok panes are not supported today;
  adding a process name alone would not verify its screen-state behavior.
- `overseer.factory` is a single-worker local task runner. It supports explicit
  argv tasks and the controller-owned fixture mode completed in Phase 1. It has
  no Grok or other provider adapter. The routing policy says
  `proposal_not_enforced_by_local_command_runner` and marks every provider
  disabled, including `grok_build` and `grok_bot`.
- Phase 1 closed the fixture-verification slice. The remaining blueprint gates
  include F06 stale-worker/reconciliation drills, F07 proven runtime isolation
  and resource controls, plus ledger backup/restore and lease invalidation on
  restore. No evidence in this task closes those gates. A same-user workspace,
  file permissions, or Grok's own sandbox option is not proof that the factory
  has contained an agent-authored process.
- The install result says Grok authentication and model access were not tested.
  It separately reports Cursor's welcome screen could not use the OS keyring
  and that `gnome-keyring-daemon` was absent from `PATH`. This is a Cursor
  credential-storage observation; it does not establish a Grok keyring failure
  or a Grok prerequisite.

## Current official Grok behavior

The official xAI Grok Build docs describe three surfaces: an interactive TUI,
headless CLI use for scripts/integrations, and ACP over stdio. The headless docs
describe `grok -p` and plain, JSON, and streaming-JSON output; the official
repository README describes tool allowlists, deny rules, and turn limits.
These are current upstream docs, not proof that every documented option exists
in the installed 1.0.62 build.

The official sandbox documentation says sandboxing is off by default. It
describes Linux Landlock profiles, but notes that child-network enforcement is
Linux-only, the model API and web tools are not blocked by child-network rules,
and `~/.grok/` remains writable. Treat this as one possible worker control to
evaluate, not as a replacement for the factory's own proven isolation gate.

Current official docs describe browser login, API-key use, and credentials
stored under `~/.grok/auth.json`. The local installation record did not perform
any of these steps, and neither account entitlement nor model availability is
known. Do not read, print, copy, or place credentials in factory task records.

## Prerequisites before an unattended adapter

Finish and record these M1 checks before M2 provider dispatch:

1. **F06 reliability:** stale-worker fencing/rejection, restart and interrupted
   run recovery, duplicate-dispatch protection, timeout/descendant handling,
   and failure drills. Preserve uncertainty rather than retrying blindly.
2. **F07 isolation:** run harmless boundary probes in the actual disposable
   runtime and prove filesystem, process, resource, and network limits. Keep the
   controller ledger, verifier rules, host credentials, and other workspaces
   outside worker write access.
3. **Ledger recovery:** back up and restore state in a disposable copy, verify
   referenced artifacts, and invalidate pre-restore leases with a fresh epoch.
4. **Acceptance:** keep controller-owned verification separate from the worker;
   bind its receipt to the exact candidate and run. Phase 1 covers trusted
   fixtures, not a live Grok candidate.
5. **Dispatch policy:** keep one writer and one provider slot for the first
   pilot. Enforce budgets and quotas in controller code. The routing JSON is
   not enforcement.

## Proposed next milestones and acceptance checks

**Next safe engineering milestone: finish M1 with a fake provider.** This can
proceed without Grok authentication or inference. Proposed checks, not run here:

- A stale or superseded worker cannot publish a candidate or obtain acceptance.
- A crash, restart, duplicate dispatch, or timeout leaves a durable, inspectable
  outcome and does not silently start a second worker.
- Boundary probes show that the worker cannot write to controller/verifier
  state, host credentials, or another task's workspace; resource and network
  limits are exercised rather than inferred from configuration.
- Backup/restore preserves valid evidence, detects missing or changed artifacts,
  and fences workers from the pre-restore epoch.
- Known-good and known-bad candidates remain distinct under independent,
  controller-owned checks.

**Then, if authorized: one Grok Build M2 pilot.** First confirm the exact
installed-version CLI and authentication behavior without exposing credentials.
Use one low-risk bounded task in the proven disposable runtime, one worker, a
narrow tool allowlist, an explicit maximum-turn/budget limit, and the documented
JSON output only if that exact build supports it. Do not use `--always-approve`
as a substitute for isolation or permission design. Proposed acceptance checks,
not run here:

- The requested and observed CLI/model identities are recorded separately; any
  identity or usage fields the CLI does not expose stay unknown.
- A real bounded change runs once in its isolated workspace; candidate output
  is parsed with strict size/schema limits and independently checked outside
  worker write access.
- Wrong, malformed, missing, or stale output fails closed; timeout, cancellation,
  restart, and child-process cleanup preserve a reconciled record.
- No provider fallback or extra worker starts on capacity/auth errors. Actual
  usage/cost is retained if available; otherwise it remains unknown.
- An operator explicitly reviews the diff and evidence before considering any
  merge or release path.

The interactive-monitor path should be evaluated separately with mocked terminal
snapshots first, then a disposable dry-run session. Do not enroll a live Grok
pane or send continuation text until that distinct behavior is authorized and
its screen-state checks are demonstrated.

## Actions requiring separate authorization

- Running `grok login`, using device/browser authentication, setting an API key,
  or changing credential/keyring storage.
- Sending a prompt, calling an API, testing model access, uploading repository
  content, or incurring provider usage/cost.
- Editing the process whitelist, routing/configuration, service, scheduler, or
  dispatch limits; adding a provider adapter or any other code change.
- Launching or enrolling a Grok pane, enabling automatic continuation, adding
  workers, or configuring fallback to another provider.
- Using Cursor in a way that changes its credential storage or desktop setup.

## Sources

Official xAI sources checked 2026-10-19:

- xAI Docs, [Grok Build](https://docs.x.ai/build/overview) — surfaces and
  authentication overview.
- xAI Docs, [Headless & Scripting](https://docs.x.ai/build/cli/headless-scripting)
  — headless mode, output formats, ACP example, and authentication assumptions.
- xAI Docs, [Sandbox](https://docs.x.ai/build/features/sandbox) — profile
  defaults and documented limitations.
- xAI Docs, [Modes and Commands](https://docs.x.ai/build/modes-and-commands) —
  documented Grok Build commands and goal behavior.
- `xai-org/grok-build`, [Grok shell README](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-shell/README.md)
  — current repository CLI modes, headless options, and auth details.

The Grok shell README and xAI docs are upstream references checked on the date
above. Installed-version behavior is grounded only in the retained local 1.0.62
help output. No login, API request, inference, tests, provider configuration,
pane launch, or code change was performed for this plan.
