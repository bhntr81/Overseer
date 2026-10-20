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
| CONTRACT | contract `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:139`, unit of work `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:168` | task validation `overseer/factory.py:100`; closed field sets per mode `overseer/factory.py:108`, `overseer/factory.py:115`, `overseer/factory.py:122`; unknown fields rejected `overseer/factory.py:127`; argument arrays only, no implicit shell `overseer/factory.py:137`; frozen spec hash `overseer/factory.py:202`; monitor report contract `overseer/policy.py:60`; prompt length bound `overseer/policy.py:42`; monitor request contract `config.json:1` | partial — the factory contract is closed, hashed, and immutable; the monitor's request contract is one free-text string; no risk tier, protected path, approval requirement, acceptance ID, or budget field exists in either system | add the missing REQUEST inputs as spec fields so the required-input list in `factory/routing-policy.json:9` has a code counterpart |
| CONTEXT | context across sessions `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:282` | continuation instruction `config.json:1`; bounded report-field splicing `overseer/policy.py:111`; report contract restated `overseer/policy.py:43`; prompt assembly `overseer/policy.py:139`; skill provenance `factory/skills-provenance.json:1` | absent — no context builder, no repository map, no memory kinds, and no record of what context was supplied and why; the skill provenance file is read by no code | write a context manifest per attempt into the run evidence directory and introduce the blueprint's memory record kinds beside it |
| STATE | durable state and recovery `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:192` | ledger schema `overseer/factory.py:152`, `overseer/factory.py:157`, `overseer/factory.py:166`, `overseer/factory.py:172`; immutable submission `overseer/factory.py:197`; run evidence directory `overseer/factory.py:1115`; monitor state file `overseer/__main__.py:17`; atomic save `overseer/__main__.py:21`; single-writer lock `overseer/__main__.py:102` | partial — artifacts and decisions are durable and survive restart; recall and memory are absent; monitor state holds hashes and timestamps only, never conversation text | land the memory record kinds in the same schema family as the ledger, in the CONTEXT increment |
| TOOLS | safe execution `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:244` | terminal transport `overseer/tmux.py:130`; pane inventory and exclusion `overseer/tmux.py:79`; read-only pane inspection `overseer/tmux.py:98`; client model picker driver `overseer/tmux.py:102`; argument-vector command runner `overseer/factory.py:500`; bubblewrap profile `overseer/isolation.py:98`; probe verdict `overseer/isolation.py:138`; probe entry `overseer/isolation.py:166` | partial — real but narrow; the bubblewrap profile probes a disposable runtime and is not a sandbox for the trusted argument-vector runner `overseer/factory.py:1`; only the codex and claude clients can be driven, and there is no file, git, network, or browser tool, and no provider adapter | keep the probe as recorded evidence; add any real tool surface only behind a proven boundary |
| PERMISSIONS | risk group `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:168`, envelope modes `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:525`, effect broker `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:230` | screen-text deny list `overseer/policy.py:19`; screen classification `overseer/policy.py:171`; rate and scope policy `overseer/policy.py:191`; opt-in enrollment `overseer/__main__.py:344`; exclusion list `overseer/__main__.py:334`; provider failure detection `overseer/modelchoice.py:70`; model decision pause `overseer/scheduler.py:181`; slot release for a paused pane `overseer/scheduler.py:159`; operator model choice `overseer/__main__.py:128`; isolation fails closed `overseer/isolation.py:166`; policy proposal `factory/routing-policy.json:3` | partial — policy, isolation, and one operator approval gate exist: a pane that reports an unsupported model, exhausted credits, or a failed login is paused, never retried, and never given a substituted model until an operator chooses; there is still no approver identity, no permission envelope, and no policy engine, and `factory/routing-policy.json:3` states it is not enforced by the local command runner and no code reads it | carry an envelope mode on the task spec with an awaiting-approval state and an approval record in the ledger |
| EVIDENCE | verification `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:303`, release gates `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:332`, bounded repair `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:350`, failure drills `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:616` | controller-owned verifier identity `overseer/factory.py:41`, `overseer/factory.py:55`; verifiers `overseer/factory.py:78`, `overseer/factory.py:89`; publish gate `overseer/factory.py:815`; reconcile `overseer/factory.py:457`; resolve with operator note `overseer/factory.py:477`; backup `overseer/factory.py:928`; fenced restore `overseer/factory.py:1053`; run summary `overseer/factory.py:1167`; continuous integration `.github/workflows/check.yml:22`; coverage `tests/test_factory.py:36`, `tests/test_isolation.py:52` | implemented for local runs — receipts are bound to candidate and verifier identity, a stale lease cannot publish, restore fences under a fresh epoch; absent for the real product: no agent traces, no token or cost measurement, no product-level acceptance, no independent reviewer identity | add reviewer identity and trace capture when a real adapter exists, not before |

## Process order

The band is a sequence, not a legend. Overseer runs stage 1 (CONTRACT), stage 3
(TOOLS), and stage 5 (RECOVERY). Stage 2 (CONTEXT) is skipped. Stage 4 (POLICY)
is now only partly present: a pane that reports an unsupported model, exhausted
credits, or a failed login is paused until an operator chooses a model
`overseer/scheduler.py:181`. There is still no general permission envelope, so
the stage that decides what the model sees is missing and the stage that
decides what it may do covers one failure class only.

The REQUEST box names three inputs. The goal exists as the task objective
`overseer/factory.py:105`. Inputs are partly expressed as the workspace and
command arguments `overseer/factory.py:131`. Risk is required by
`factory/routing-policy.json:9` and recorded nowhere in code.

## Two systems, not bridged

- System A, the terminal monitor: command surface `overseer/__main__.py:270`,
  prompt decision `overseer/policy.py:139`, queue `overseer/scheduler.py:84`,
  transport `overseer/tmux.py:82`. It reads visible output, builds one bounded
  prompt, and types it into a pane.
- System B, the local job factory: submission `overseer/factory.py:197`, run
  `overseer/factory.py:1102`, isolation probe `overseer/isolation.py:166`. It
  runs explicitly trusted local commands against a durable ledger.

Nothing bridges them. The monitor does not drive the factory and the factory
does not drive the monitor. This document does not claim a bridge.

## What this framework does not claim

- No provider adapter is implemented. There is no Codex, Claude, or Grok worker;
  the fake provider is a deterministic simulator. `docs/FACTORY_EXECUTION.md:136`
- The model decision gate is one failure class on one subsystem. It does not
  substitute a model, does not retry a blocked pane, and cannot drive an
  `opencode` or `grok` session because the monitor only watches `codex` and
  `claude` clients `overseer/tmux.py:11`.
- The bubblewrap profile in `overseer/isolation.py:98` is a probe, not a
  sandbox for the trusted argument-vector runner. `docs/FACTORY_EXECUTION.md:97`
- Token and cost fields are null and are never estimated.
  `overseer/factory.py:1167`
- `factory/routing-policy.json:3` and `factory/skills-provenance.json:1` are
  documentation only. No code reads either file.
- A factory run marked passed is not product or release acceptance.
  `docs/FACTORY_EXECUTION.md:42`
- The continuous-integration check `.github/workflows/check.yml:22` has not run
  on a remote repository. `docs/FACTORY_EXECUTION.md:48`
- There is no approval gate and no approver identity.
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
