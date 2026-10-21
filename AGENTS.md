# Project instructions

## Shared optimizer and prompt-writing workflow

Follow `/home/kali/Programming/Projects/AGENTS.md`: use the `coder_optimization`
playbook and task/review guidance; assign a dedicated prompt-writing agent to
read the latest
output and write the next bounded prompt, then have the primary agent execute
and verify it within the authorized scope. Preserve this project's specific
constraints and model requirements. This standing workflow supersedes older
wording that made optimizer guidance optional; it adds no runtime dependency.

## Harness framework

`docs/HARNESS_FRAMEWORK.md` maps the six harness pillars onto the code that
implements them. File every increment against exactly one pillar row there, and
keep its verdicts honest.

## Overseer factory agent directives

These directives bind every agent that works on this project. They name what
must be executed and shown, not what may be assumed.

### Core execution mandates

1. **NO PREMATURE COMPLETION:** Never report a task as "complete", "finished",
   or "working" based on static analysis alone. You MUST execute, lint, or run
   tests using terminal tools to verify execution output.
2. **SANDBOX SELF-CORRECTION LOOP:** If code fails compilation, type-checking,
   or test execution, read the `stderr` trace, attempt a fix, and run the
   execution test again. Attempt up to 3 self-correction loops before
   escalating.
3. **RECURSIVE PROMPT GENERATION:** When generating prompts for down-stream
   worker agents:
   - Include exact technical constraints (framework versions, file locations,
     expected return types).
   - Do NOT assume the next agent remembers previous context. Make every
     sub-prompt self-contained with explicit code context or logs.
4. **FILE WRITING RULES:**
   - Write clean, production-ready code with complete logic (NO
     `// TODO: implement later` or placeholder stubs).
   - Keep file edits modular to prevent prompt decay over long sessions.

### Verification and handoff protocol

Before passing output to the next agent or marking a task done, you must
execute the following terminal checks:

1. **Syntax / AST Check:** Run language linter or compiler (e.g.,
   `python -m py_compile <file>`, `tsc --noEmit`, or equivalent).
2. **Automated Unit / Dry Run:** Execute the newly created/modified code or
   its corresponding test suite.
3. **Status Logging:** Output a brief handoff block at the end of your
   response:
###

## HARDENING COMPLIANCE MANDATES
1. **RED-GREEN SEPARATION:** When assigned an implementation task, you are STRICTLY FORBIDDEN from modifying any file inside `tests/`. Test files are read-only during coding phases.
2. **LOCALITY LIMIT:** Keep file growth lean. If a single module modification adds more than 15% new lines or creates massive duplicate functions, split the logic or flag it for structural review.
3. **GROUND TRUTH RE-READ:** Always re-read the core feature intent from `SPEC.md` or the primary spec before writing code to prevent prompt drift.
   ```yaml
   STATUS: [SUCCESS | STUCK_NEEDS_ESCALATION]
   TESTS_PASSED: [TRUE | FALSE]
   FILES_MODIFIED: [<list of files>]
   NEXT_AGENT_INSTRUCTION: "<clear self-contained prompt for next iteration>"
   ```

