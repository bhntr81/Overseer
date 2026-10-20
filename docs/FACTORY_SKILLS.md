# Skills for Overseer

Overseer is the software factory project. Its current design is the imported
[Version 2 blueprint](SOFTWARE_FACTORY_BLUEPRINT_V2.txt). This addendum incorporates
selected workflows from [davidondrej/skills](https://github.com/davidondrej/skills/tree/27e2e3a63f36ef8c962dae08d5ed59b27d72249e).
The imported blueprint is unchanged; its research claims were not reverified in
this integration task. Actual implementation remains in
[FACTORY_EXECUTION.md](FACTORY_EXECUTION.md).

## Installed selection

Three instruction-only skills are installed for this user's Codex sessions under
`/home/kali/.codex/skills`. All upstream files were reviewed and compared byte for
byte with commit `27e2e3a63f36ef8c962dae08d5ed59b27d72249e`. Each copy includes the
upstream MIT license. [Provenance](../factory/skills-provenance.json) records paths,
hashes, installation status, and the blueprint move.

| Skill | Factory use | Boundary |
| --- | --- | --- |
| `better-prompt` | Explicit refinement of an ambiguous task: primary evidence, methods, and an independent correctness check | Deepen the same task without expanding scope. The dedicated prompt writer remains responsible for the executable handoff. |
| `goal-loop` | Objective, constraints, validation command, and observable stop condition for bounded work | A skill is not a scheduler. Persistent goal creation requires explicit user instruction and runtime support. |
| `effective-agent-skills` | Design small, relevant skills with targeted references and activation checks | Complements the installed system skill-creator; does not replace it or prove portability across clients. |

Installation is complete. The acceptance reviewer observed all three skills in
its runtime catalog, confirming discovery there. A small usefulness evaluation
then ran one realistic request and one near-miss for each skill in separate
fresh agent contexts. The realistic `better-prompt` output stayed in scope but
omitted an explicit independent correctness check; the `goal-loop` draft-only
case produced the requested contract after its first, underspecified setup was
clarified; `effective-agent-skills` identified metadata, trigger, workflow, and
validation gaps in a sample skill. All three near-misses received direct answers
without unnecessary prompt rewriting, goal drafting, or skill authoring.

Runtime activation remains unverified. This interface does not expose whether a
skill body was loaded for a turn, and catalog presence or an agent's self-report
is not proof. The output sample does not demonstrate improved task quality,
efficiency, or cost. `better-prompt` requests explicit invocation in its text
but has no Codex-specific `agents/openai.yaml`; runtime-enforced manual-only
behavior is not claimed. No Cursor, Claude, or Grok skill installation was
performed.

## Fit with the factory workflow

The prompt writer reads the latest execution evidence and the applicable project
contract, optionally uses explicit prompt refinement, and produces one bounded
handoff. The primary agent executes it, verifies the outcome, and reports evidence
back. Existing coder_optimization guidance and project-specific model constraints
remain authoritative. Skills do not add permission to run external effects.

Use the loop contract's objective, preservation constraints, exact checks, and stop
condition in existing task records. Keep attempt budgets, dispatch ownership,
protected verification, and model eligibility in the controller. The current local
runner does not automatically load or enforce these skills. The factory now
records the provenance and checks the installed bytes for each attempt, and it
still loads and supplies none of them.

Before expanding use, test one realistic request and one near-miss for each skill
in a fresh session, inspect actual activation, then assess the produced artifact
against the task contract. Record failures as well as successes in the existing
optimizer workflow. No efficiency gain or model ranking is claimed here.

## Reviewed but deferred

- `git-worktree`: useful isolation checklist, but its default copying of `.env`
  files and optional shared services do not fit disposable factory workers.
  Retain separate task workspaces with explicitly scoped configuration instead.
- `handoff`: useful state, decisions, and verification structure, but its mandatory
  wait-for-user ending conflicts with the authorized prompt-write/execute loop.
- `before-building`: mandatory no-inspection response and waiting for answers do
  not fit our evidence-first, autonomous handling of routine choices.
- `larp-detector`: retain evidence-based assessment of whether a change solves a
  real problem; do not infer contributor motives or competence.
- `codex-subagent` and `total-review`: fixed model choices and, for total-review,
  five maximum-effort/full-permission reviewers conflict with measured routing,
  bounded resources, and scoped worker authority.
- `cmux`: its instructions target macOS; the existing Kali tmux hub stays in place.

Other repository skills were inventoried, not comprehensively audited or installed.
Infrastructure-specific tools and integrations need their own task and capability
check before adoption. Upstream updates require review and a new recorded revision;
there is no automatic update hook.

## Next factory milestone

Follow Version 2's M1 acceptance gaps: trusted fixture modes, candidate-bound
verification, stale-worker rejection, and backup/restore evidence. The existing
trusted-command runner is not proof of those stronger guarantees. Proven runtime
isolation and protected verification precede unattended real provider workers.
Installing skills does not complete those milestones.
