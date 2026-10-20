# Harness framework

`agents.jpeg` at the repository root is the source of this frame.

![Harness engineering frame](../agents.jpeg)

## The frame

REQUEST (goal · inputs · risk) → THE AGENT HARNESS → RESULT (verified · traceable).

Six pillars surround a MODEL. Given to the model: CONTRACT (scope · success ·
constraints), CONTEXT (maps · rules · evidence), STATE (artifacts · decisions ·
memory). Constraining the model: TOOLS (sandbox · browser · shell), PERMISSIONS
(policy · approval · isolation), EVIDENCE (tests · traces · recovery).

The frame's own caption: **MODEL REASONS · HARNESS CONTROLS · TOOLS ACT**.

The bottom band is the process order, and each band stage maps to one pillar:
CONTRACT → CONTRACT, CONTEXT → CONTEXT, TOOLS → TOOLS, POLICY → PERMISSIONS,
RECOVERY → EVIDENCE.

This frame compresses [SOFTWARE_FACTORY_BLUEPRINT_V2.txt](SOFTWARE_FACTORY_BLUEPRINT_V2.txt);
it does not replace it. The blueprint keeps the prescriptions, this file maps
them onto the code that exists. Verified outcomes stay in
[FACTORY_EXECUTION.md](FACTORY_EXECUTION.md).

## The pillar map

| Pillar | Blueprint V2 section(s) | Current implementation (file:line) | Verdict | Next increment |
| --- | --- | --- | --- | --- |
| CONTRACT | contract `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:139`, unit of work `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:168` | task validation `overseer/factory.py:300`; closed field sets per mode `overseer/factory.py:309`, `overseer/factory.py:316`, `overseer/factory.py:323`; unknown fields rejected `overseer/factory.py:327`; argument arrays only, no implicit shell `overseer/factory.py:338`; frozen spec hash `overseer/factory.py:413`; contract block validation `overseer/factory.py:210`; contract field set `overseer/factory.py:60`; routing-policy input map `overseer/factory.py:88`; contract in the inspect result `overseer/factory.py:478`; monitor report contract `overseer/policy.py:60`; prompt length bound `overseer/policy.py:42`; monitor request contract `config.json:1` | partial — the factory contract is closed, hashed, and immutable, and a command-mode spec may now carry a closed, validated contract block with a risk tier, external effects, protected paths, approval requirements, acceptance identifiers, the routing-policy required inputs, and a budget; the block is optional for command-mode submissions, and its statements are recorded, never enforced: no budget limit, protected path, or approval requirement is acted on, and there is no approver identity; the monitor's request contract is still one free-text string, so the contract gap in that system is unchanged; the routing policy's `required_decision_fields` have no code counterpart because no router exists | make the contract block required for new command-mode submissions, reconcile the repository example task and stored legacy jobs with it, and close the monitor-side request contract as a separate increment |
| CONTEXT | context across sessions `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:282` | continuation instruction `config.json:1`; bounded report-field splicing `overseer/policy.py:111`; report contract restated `overseer/policy.py:43`; prompt assembly `overseer/policy.py:139`; skill provenance `factory/skills-provenance.json:1` | absent — no context builder, no repository map, no memory kinds, and no record of what context was supplied and why; the skill provenance file is read by no code | write a context manifest per attempt into the run evidence directory and introduce the blueprint's memory record kinds beside it |
| STATE | durable state and recovery `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:192` | ledger schema `overseer/factory.py:357`, `overseer/factory.py:362`, `overseer/factory.py:371`, `overseer/factory.py:377`; immutable submission `overseer/factory.py:406`; run evidence directory `overseer/factory.py:1406`; monitor state file `overseer/__main__.py:17`; atomic save `overseer/__main__.py:21`; single-writer lock `overseer/__main__.py:102` | partial — artifacts and decisions are durable and survive restart; recall and memory are absent; monitor state holds hashes and timestamps only, never conversation text | land the memory record kinds in the same schema family as the ledger, in the CONTEXT increment |
| TOOLS | safe execution `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:244` | terminal transport `overseer/tmux.py:154`; pane inventory and exclusion `overseer/tmux.py:85`; read-only pane inspection `overseer/tmux.py:104`; client model picker driver `overseer/tmux.py:118`; driven clients `overseer/tmux.py:14`; client phase detection `overseer/scheduler.py:52`; OpenCode composer and running markers `overseer/modelchoice.py:280`, `overseer/modelchoice.py:292`; session routing `overseer/route.py:62`; argument-vector command runner `overseer/factory.py:768`; bubblewrap profile `overseer/isolation.py:98`; probe verdict `overseer/isolation.py:138`; probe entry `overseer/isolation.py:166` | partial — real but narrow; the bubblewrap profile probes a disposable runtime and is not a sandbox for the trusted argument-vector runner `overseer/factory.py:1`; Codex, Claude, and OpenCode sessions can be driven, a Grok session cannot because its composer is not recognized; the OpenCode turn states are recognized, so a finished turn releases the queue reservation; there is no file, git, network, or browser tool, and no provider adapter | keep the probe as recorded evidence; add any real tool surface only behind a proven boundary |
| PERMISSIONS | risk group `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:168`, envelope modes `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:541`, effect broker `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:230` | screen-text deny list `overseer/policy.py:19`; screen classification `overseer/policy.py:171`; rate and scope policy `overseer/policy.py:191`; opt-in enrollment `overseer/__main__.py:359`; exclusion list `overseer/__main__.py:349`; provider failure detection `overseer/modelchoice.py:81`; model decision pause `overseer/scheduler.py:230`; credit fallback policy `overseer/modelchoice.py:122`; zero-credit route `overseer/scheduler.py:143`; exhausted status `overseer/scheduler.py:250`; operator model choice `overseer/__main__.py:131`; isolation fails closed `overseer/isolation.py:166`; policy proposal `factory/routing-policy.json:3`; envelope field set `overseer/factory.py:80`; envelope modes `overseer/factory.py:81`; envelope validation `overseer/factory.py:264`; awaiting-approval submission `overseer/factory.py:406`; approvals table `overseer/factory.py:392`; decision record `overseer/factory.py:715`; dispatch gate `overseer/factory.py:1374`; decision in the inspect result `overseer/factory.py:481` | partial — policy, isolation, and one operator approval gate exist: a pane that reports an unsupported model, exhausted credits, or a failed login is paused, never retried, and never given a substituted model; exhausted credits route the work to the configured zero-credit tier, and when that tier is exhausted too the pane waits in `CREDITS_EXHAUSTED_WAITING` instead of downgrading; the factory now carries a recorded envelope: a command-mode task may name one of the blueprint's four modes, its declared scope, whether a fresh decision is required, and the decider it names, and a task that declares it needs a decision waits in `awaiting_approval` and is not dispatched until a decision is recorded in the ledger; the record names the decider, the decision, and the time; the mode, the scope, and the decider identity are recorded, never enforced — there is no roster check, no scope check, no policy engine, no operator pause of running work, and no retry-with-reason path; `factory/routing-policy.json:3` still states that no runtime code reads it and no router enforces its decisions | make the envelope mandatory for new command-mode submissions, and add the blueprint's remaining permission controls: an operator pause of running work and a retry-with-reason path |
| EVIDENCE | verification `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:303`, release gates `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:332`, bounded repair `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:350`, failure drills `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:616` | controller-owned verifier identity `overseer/factory.py:41`, `overseer/factory.py:55`; verifiers `overseer/factory.py:119`, `overseer/factory.py:130`; publish gate `overseer/factory.py:1083`; reconcile `overseer/factory.py:679`; resolve with operator note `overseer/factory.py:699`; backup `overseer/factory.py:1196`; fenced restore `overseer/factory.py:1325`; run summary `overseer/factory.py:1458`; continuous integration `.github/workflows/check.yml:22`; coverage `tests/test_factory.py:41`, `tests/test_isolation.py:52` | implemented for local runs — receipts are bound to candidate and verifier identity, a stale lease cannot publish, restore fences under a fresh epoch; absent for the real product: no agent traces, no token or cost measurement, no product-level acceptance, no independent reviewer identity | add reviewer identity and trace capture when a real adapter exists, not before |

## Process order

The band is a sequence, not a legend. Overseer runs stage 1 (CONTRACT), stage 3
(TOOLS), and stage 5 (RECOVERY). Stage 2 (CONTEXT) is skipped. Stage 4 (POLICY)
is now only partly present: a pane that reports an unsupported model, exhausted
credits, or a failed login is paused until an operator chooses a model
`overseer/scheduler.py:218`, and exhausted credits follow a configured
zero-credit route. The factory also carries a recorded capability envelope
`overseer/factory.py:264`: a task that declares it needs a fresh decision
waits in `awaiting_approval` and is not dispatched until a decision naming
the decider is recorded in the ledger `overseer/factory.py:715`. The envelope's
scope and its decider identity are recorded, not authorized. The stage that
decides what the model sees is still missing, the stage that decides what it
may do covers one failure class in the monitor and one pre-dispatch gate in
the factory, and there is no operator pause of running work.

The REQUEST box names three inputs. The goal exists as the task objective
`overseer/factory.py:305`. Inputs are partly expressed as the workspace and
command arguments `overseer/factory.py:332`. Risk is required by
`factory/routing-policy.json:9` and now has a validated code counterpart in the
optional contract block `overseer/factory.py:210`; the block records a risk
tier, and nothing enforces it.

## Two systems, not bridged

- System A, the terminal monitor: command surface `overseer/__main__.py:270`,
  prompt decision `overseer/policy.py:139`, queue `overseer/scheduler.py:84`,
  transport `overseer/tmux.py:82`. It reads visible output, builds one bounded
  prompt, and types it into a pane.
- System B, the local job factory: submission `overseer/factory.py:406`, run
  `overseer/factory.py:1374`, isolation probe `overseer/isolation.py:166`. It
  runs explicitly trusted local commands against a durable ledger.

Nothing bridges them. The monitor does not drive the factory and the factory
does not drive the monitor. This document does not claim a bridge.

## What this framework does not claim

- No provider adapter is implemented. There is no Codex, Claude, or Grok worker;
  the fake provider is a deterministic simulator. `docs/FACTORY_EXECUTION.md:136`
- The model decision gate is one failure class on one subsystem. It does not
  substitute a model, does not retry a blocked pane, and does not drive a
  `grok` session because the monitor does not recognize that composer
  `overseer/tmux.py:14`.
- The bubblewrap profile in `overseer/isolation.py:98` is a probe, not a
  sandbox for the trusted argument-vector runner. `docs/FACTORY_EXECUTION.md:97`
- Token and cost fields are null and are never estimated.
  `overseer/factory.py:1458`
- The contract block records declared risk, protected paths, approval
  requirements, and budget limits; it enforces none of them. The
  `protected_paths` check is a lexical shape check on a declaration, not a
  write guard. `overseer/factory.py:210`
- The envelope block records a capability mode, a declared scope, and a
  decider name; it authorizes none of them. The only enforced part is the
  gate: a task that declares it needs a decision is not dispatched until a
  decision is recorded, and the recorded decider is compared with no roster.
  `overseer/factory.py:264`
- The test suite reads `factory/routing-policy.json` to prove that its
  `required_inputs` list has a validated code counterpart; no runtime code
  reads that file, and the file's routing decisions are still a proposal with
  no router behind them. `factory/routing-policy.json:3`
- `factory/skills-provenance.json:1` is read by no code at all.
- A factory run marked passed is not product or release acceptance.
  `docs/FACTORY_EXECUTION.md:42`
- The continuous-integration check `.github/workflows/check.yml:22` has not run
  on a remote repository. `docs/FACTORY_EXECUTION.md:48`
- The factory has one pre-dispatch approval gate and one operator approval
  gate in the monitor. There is no approver identity check, no enforced scope,
  no policy engine, no operator pause of running work, and no retry-with-reason
  path. `overseer/factory.py:715`
- There are no agent traces. Terminal-state detection in the monitor is
  heuristic and is not a provider-wide concurrency lock.
  `docs/FACTORY_EXECUTION.md:110`
- The monitor deliberately keeps the model out of the decision path. A visible
  report is parsed as data and never evaluated. `overseer/policy.py:1`

## Filing an increment against a pillar

- Every increment is filed against exactly one pillar row.
- A verdict is raised only with a cited file and line, or a named test.
- A downgrade is allowed and must be recorded in the iteration log.
- Cited references are machine-checked. Run `python3 scripts/check-doc-references`;
  it parses the file and line references in this document and fails when a path
  is missing or a line is out of range.
- A pillar row with no new increment since the last check is a reason to
  re-verify, not a reason to claim progress.
- This file stays a map. Prescriptions live in the blueprint; evidence lives in
  the execution record.
