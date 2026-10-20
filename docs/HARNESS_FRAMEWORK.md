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
| CONTRACT | contract `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:139`, unit of work `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:168` | task validation `overseer/factory.py:345`; closed field sets per mode `overseer/factory.py:354`, `overseer/factory.py:361`, `overseer/factory.py:368`; unknown fields rejected `overseer/factory.py:376`; argument arrays only, no implicit shell `overseer/factory.py:383`; frozen spec hash `overseer/factory.py:466`; contract block validation `overseer/factory.py:216`; contract field set `overseer/factory.py:62`; routing-policy input map `overseer/factory.py:94`; contract in the inspect result `overseer/factory.py:531`; monitor report contract `overseer/policy.py:60`; prompt length bound `overseer/policy.py:42`; monitor request contract `config.json:1` | partial — the factory contract is closed, hashed, and immutable, and a command-mode spec carries a closed, validated contract block with a risk tier, external effects, protected paths, approval requirements, acceptance identifiers, the routing-policy required inputs, and a budget; the contract block is required for new command-mode submissions, validated, closed, and frozen with the specification hash at dispatch; a job stored before the requirement keeps its specification and stays dispatchable and inspectable, because the requirement is checked only at submit; the block's statements are recorded, never enforced: no budget limit, protected path, or approval requirement is acted on, the risk tier is a declaration, and there is no approver identity; the monitor's request contract is still one free-text string, so the contract gap in that system is unchanged; the routing policy's `required_decision_fields` have no code counterpart because no router exists | close the monitor-side request contract as its own increment; that gap is unchanged and separately filed, and the factory contract now covers the Risk and Budget groups while the blueprint's Identity, Dependency, Execution, Verification, and Result groups remain uncovered |
| CONTEXT | context across sessions `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:282`, the four memory kinds `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:288`, durable entry fields `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:297`, task inputs `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:180`, task result `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:186` | continuation instruction `config.json:1`; bounded report-field splicing `overseer/policy.py:111`; report contract restated `overseer/policy.py:43`; prompt assembly `overseer/policy.py:139`; skill provenance `factory/skills-provenance.json:1`; context manifest writer `overseer/factory.py:1033`; manifest written per completed attempt `overseer/factory.py:1945`; repository identity probe `overseer/factory.py:321`; memory table `overseer/factory.py:442`, `overseer/factory.py:1682`; memory record API `overseer/factory.py:815`, `overseer/factory.py:867`; memory in the inspect result `overseer/factory.py:533`; memory recall `overseer/factory.py:935`; recall environment `overseer/factory.py:1010`; recall file in the run evidence `overseer/factory.py:1865`; codebase file tree `overseer/codemap.py:101`; structure extraction `overseer/codemap.py:129`; codebase assembly `overseer/codemap.py:652`; code excerpt `overseer/codemap.py:162`; secret names `overseer/codemap.py:152`; test file convention `overseer/codemap.py:264`; parsed references `overseer/codemap.py:275`; textual references `overseer/codemap.py:303`; relation search `overseer/codemap.py:362`; relation of a symbol `overseer/codemap.py:470`; relation digest `overseer/codemap.py:726`; codebase environment `overseer/factory.py:1021`; relation counts in the supplied source `overseer/factory.py:1078`; manifest relations `overseer/factory.py:1161`; codebase file in the run evidence `overseer/factory.py:1875` | partial — the factory now writes a context manifest into the run evidence directory of every completed attempt, recording the objective, the spec hash, the workspace, the repository identity and base commit when one was observed, the acceptance identifiers, the commands actually run, the environment facts the runner already holds, and a supplied list that says what was supplied and why; it stores the blueprint's four memory kinds, a verified fact, a decision, a hypothesis, and a historical attempt, in the ledger, queryable per job and per kind, durable across a backup and restore; a new attempt now recalls the relevant records of its own job and of earlier runs in the same project before it starts, marks the superseded decisions and the facts whose bound revision has moved as unusable, writes the recall into the run evidence, and hands it to the execution environment; it also assembles a codebase context from the workspace file tree, selects the files the task names or whose path matches the task terms, extracts the structural symbols of those files, and hands the map to the attempt; the map names files and symbols and carries a bounded excerpt of the code of those symbols, at most 8 KiB and 60 lines per file and 32 KiB for the whole attempt, and a file whose name marks it as a secret is never read for its content; the map also relates each selected symbol to the code that calls it and to the test files that cover it, and that relation is honest about what it is: Python is parsed and every other language is matched textually, so a relation is a static reference and not a proven call, an attribute reference does not name the object it belongs to, and a textual match may be a comment or a string; the search is capped at 400 files and 2 MiB with 20 callers and 10 tests per symbol, the size of a file is checked before it is opened so the bytes read never pass the bound, a symbol nothing references is recorded with the number of files that were searched, and a corpus the cap truncated is recorded as truncated with the reason that says so; a hypothesis stays unverified, a historical attempt is preserved as a result and not as current state; the skill provenance file is still read by no code | relate the recalled memory records to the symbols they name, so a decision or a verified fact about a symbol is attached to that symbol in the map instead of listed beside it |
| STATE | durable state and recovery `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:192` | ledger schema `overseer/factory.py:403`, `overseer/factory.py:408`, `overseer/factory.py:417`, `overseer/factory.py:423`; immutable submission `overseer/factory.py:459`; run evidence directory `overseer/factory.py:1858`; memory records `overseer/factory.py:442`; monitor state file `overseer/__main__.py:19`; atomic save `overseer/__main__.py:23`; single-writer lock `overseer/__main__.py:256` | partial — artifacts and decisions are durable and survive restart; the memory kinds are stored in the ledger and a new attempt now recalls the relevant ones, of its own job and of earlier runs in the same project; monitor state holds hashes and timestamps only, never conversation text | keep the recalled records and the ledger they are read from in step |
| TOOLS | safe execution `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:244` | terminal transport `overseer/tmux.py:220`; pane inventory and exclusion `overseer/tmux.py:99`; read-only pane inspection `overseer/tmux.py:170`; client model picker driver `overseer/tmux.py:184`; driven clients `overseer/tmux.py:15`; client phase detection `overseer/scheduler.py:52`; OpenCode composer and running markers `overseer/modelchoice.py:280`, `overseer/modelchoice.py:293`; target scope `overseer/tmux.py:116`, `overseer/tmux.py:136`, scope-aware opt-in `overseer/tmux.py:145`; client directory `overseer/tmux.py:28`; session routing `overseer/route.py:62`; argument-vector command runner `overseer/factory.py:1213`; bubblewrap profile `overseer/isolation.py:98`; probe verdict `overseer/isolation.py:138`; probe entry `overseer/isolation.py:166` | partial — real but narrow; the bubblewrap profile probes a disposable runtime and is not a sandbox for the trusted argument-vector runner `overseer/factory.py:1`; Codex, Claude, and OpenCode sessions can be driven, a Grok session cannot because its composer is not recognized; the OpenCode turn states are recognized, so a finished turn releases the queue reservation; the transport manages only the panes that are enrolled or inside the configured target scope, and ignores every other tmux window; there is no file, git, network, or browser tool, and no provider adapter | keep the probe as recorded evidence; add any real tool surface only behind a proven boundary |
| PERMISSIONS | risk group `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:168`, envelope modes `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:543`, effect broker `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:230` | screen-text deny list `overseer/policy.py:19`; screen classification `overseer/policy.py:171`; rate and scope policy `overseer/policy.py:191`; opt-in enrollment `overseer/__main__.py:372`; exclusion list `overseer/__main__.py:362`; provider failure detection `overseer/modelchoice.py:85`; model decision pause `overseer/scheduler.py:240`; credit fallback policy `overseer/modelchoice.py:126`; zero-credit route `overseer/scheduler.py:152`; exhausted status `overseer/scheduler.py:260`; operator model choice `overseer/__main__.py:139`; isolation fails closed `overseer/isolation.py:166`; policy proposal `factory/routing-policy.json:3`; envelope field set `overseer/factory.py:82`; envelope modes `overseer/factory.py:83`; envelope validation `overseer/factory.py:270`; awaiting-approval submission `overseer/factory.py:459`; approvals table `overseer/factory.py:438`; decision record `overseer/factory.py:769`; dispatch gate `overseer/factory.py:1826`; decision in the inspect result `overseer/factory.py:535` | partial — policy, isolation, and one operator approval gate exist: a pane that reports an unsupported model, exhausted credits, or a failed login is paused, never retried, and never given a substituted model; exhausted credits route the work to the configured zero-credit tier, and when that tier is exhausted too the pane waits in `CREDITS_EXHAUSTED_WAITING` instead of downgrading; the factory now carries a recorded envelope: a command-mode task may name one of the blueprint's four modes, its declared scope, whether a fresh decision is required, and the decider it names, and a task that declares it needs a decision waits in `awaiting_approval` and is not dispatched until a decision is recorded in the ledger; the record names the decider, the decision, and the time; the mode, the scope, and the decider identity are recorded, never enforced — there is no roster check, no scope check, no policy engine, no operator pause of running work, and no retry-with-reason path; `factory/routing-policy.json:3` still states that no runtime code reads it and no router enforces its decisions | make the envelope mandatory for new command-mode submissions, and add the blueprint's remaining permission controls: an operator pause of running work and a retry-with-reason path |
| EVIDENCE | verification `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:303`, release gates `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:332`, bounded repair `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:350`, failure drills `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:616` | controller-owned verifier identity `overseer/factory.py:43`, `overseer/factory.py:57`; verifiers `overseer/factory.py:125`, `overseer/factory.py:136`; publish gate `overseer/factory.py:1528`; reconcile `overseer/factory.py:733`; resolve with operator note `overseer/factory.py:753`; backup `overseer/factory.py:1641`; fenced restore `overseer/factory.py:1777`; run summary `overseer/factory.py:1933`; continuous integration `.github/workflows/check.yml:22`; coverage `tests/test_factory.py:77`, `tests/test_isolation.py:52` | implemented for local runs — receipts are bound to candidate and verifier identity, a stale lease cannot publish, restore fences under a fresh epoch; absent for the real product: no agent traces, no token or cost measurement, no product-level acceptance, no independent reviewer identity | add reviewer identity and trace capture when a real adapter exists, not before |

## Process order

The band is a sequence, not a legend. Overseer runs stage 1 (CONTRACT), stage 3
(TOOLS), and stage 5 (RECOVERY). Stage 2 (CONTEXT) is still not run: the
factory records what it supplied for each attempt in a context manifest
`overseer/factory.py:1033`, the memory kinds are stored, a new attempt recalls
the relevant records and is handed them, and a codebase map is assembled from
the workspace file tree before the work starts; it names the files, the
symbols, a bounded excerpt of their code, and the callers and the test files
of those symbols `overseer/codemap.py:649`. Stage 4 (POLICY)
is now only partly present: a pane that reports an unsupported model, exhausted
credits, or a failed login is paused until an operator chooses a model
`overseer/scheduler.py:215`, and exhausted credits follow a configured
zero-credit route. The factory also carries a recorded capability envelope
`overseer/factory.py:82`: a task that declares it needs a fresh decision
waits in `awaiting_approval` and is not dispatched until a decision naming
the decider is recorded in the ledger `overseer/factory.py:767`. The envelope's
scope and its decider identity are recorded, not authorized. The stage that
decides what the model sees is still missing, the stage that decides what it
may do covers one failure class in the monitor and one pre-dispatch gate in
the factory, and there is no operator pause of running work.

The REQUEST box names three inputs. The goal exists as the task objective
`overseer/factory.py:351`. Inputs are partly expressed as the workspace and
command arguments `overseer/factory.py:383`. Risk is required by
`factory/routing-policy.json:9` and now has a validated code counterpart in the
contract block `overseer/factory.py:62`, which is required for new
command-mode submissions; the block records a risk tier, and nothing enforces
it.

## Two systems, not bridged

- System A, the terminal monitor: command surface `overseer/__main__.py:291`,
  prompt decision `overseer/policy.py:139`, queue `overseer/scheduler.py:84`,
  transport `overseer/tmux.py:152`. It reads visible output, builds one bounded
  prompt, and types it into a pane.
- System B, the local job factory: submission `overseer/factory.py:457`, run
  `overseer/factory.py:1826`, isolation probe `overseer/isolation.py:166`. It
  runs explicitly trusted local commands against a durable ledger.

Nothing bridges them. The monitor does not drive the factory and the factory
does not drive the monitor. This document does not claim a bridge.

## What this framework does not claim

- No provider adapter is implemented. There is no Codex, Claude, or Grok worker;
  the fake provider is a deterministic simulator. `docs/FACTORY_EXECUTION.md:168`
- The model decision gate is one failure class on one subsystem. It does not
  substitute a model, does not retry a blocked pane, and does not drive a
  `grok` session because the monitor does not recognize that composer
  `overseer/tmux.py:15`.
- The bubblewrap profile in `overseer/isolation.py:98` is a probe, not a
  sandbox for the trusted argument-vector runner. `docs/FACTORY_EXECUTION.md:167`
- Token and cost fields are null and are never estimated.
  `overseer/factory.py:1933`
- The contract block is required for new command-mode submissions, and it
  records declared risk, protected paths, approval requirements, and budget
  limits; it enforces none of them. The `protected_paths` check is a lexical
  shape check on a declaration, not a write guard. `overseer/factory.py:94`
- The envelope block records a capability mode, a declared scope, and a
  decider name; it authorizes none of them. The only enforced part is the
  gate: a task that declares it needs a decision is not dispatched until a
  decision is recorded, and the recorded decider is compared with no roster.
  `overseer/factory.py:86`
- The context manifest records what the controller supplied for an attempt and
  why. The memory kinds are stored and queryable, and a new attempt reads the
  relevant ones: a codebase context is assembled and the recalled records are
  consulted before the work starts. What the map relates is a static reference
  and not a proven call, and no hypothesis or historical attempt is presented
  as current truth. `overseer/factory.py:1033`
- The test suite reads `factory/routing-policy.json` to prove that its
  `required_inputs` list has a validated code counterpart; no runtime code
  reads that file, and the file's routing decisions are still a proposal with
  no router behind them. `factory/routing-policy.json:3`
- `factory/skills-provenance.json:1` is read by no code at all.
- A factory run marked passed is not product or release acceptance.
  `docs/FACTORY_EXECUTION.md:46`
- The continuous-integration check `.github/workflows/check.yml:22` has not run
  on a remote repository. `docs/FACTORY_EXECUTION.md:51`
- The factory has one pre-dispatch approval gate and one operator approval
  gate in the monitor. There is no approver identity check, no enforced scope,
  no policy engine, no operator pause of running work, and no retry-with-reason
  path. `overseer/factory.py:767`
- There are no agent traces; the execution record does not mention them.
  Terminal-state detection in the monitor is heuristic and is not a
  provider-wide concurrency lock. `docs/FACTORY_EXECUTION.md:143`
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
