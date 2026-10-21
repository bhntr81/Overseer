"""Build the worker invocation that drives a real coding agent: OpenCode.

The factory runs a job's implementation as an argument vector. This module
builds that vector for the OpenCode CLI in headless mode (`opencode run`), so a
job can be driven by a real model instead of a hand-written command. The
instruction is placed as one whole argv element and is never formatted into a
string or passed through a shell, so nothing in it can be read as a flag or a
command.

`--standalone` runs a private server rooted in the workspace rather than the
shared background service, and the factory sets the child's PWD to the
workspace, so the model's edits land there. OpenCode's `opencode/*-free` gateway
models cost nothing and need no credentials; the ones listed here were seen with
`opencode models` on 2026-10-21 and can go stale. A stronger or paid model is
one identifier change; this module never invents a model name.

This module detects the active coding-agent session from the environment and
defaults to its runner, so when an LLM launches Overseer the work is driven by
that same LLM (run from Claude Code, the default runner is `claude`). The free
OpenCode gateway is the fallback, used only when no session is detected or when
a runner is named explicitly. Inheriting a paid runner (Claude Code or Codex)
spends that account's credits, and the chosen runner and its source are always
reported, never hidden. Nothing here runs a command; it builds argv and task
specs that the factory runs and records.
"""
import os

DEFAULT_OPENCODE = 'opencode'

# opencode/*-free models seen with `opencode models` on 2026-10-21. This list
# can go stale; it is the operator's recorded snapshot, not a live check.
FREE_MODELS = (
    'opencode/deepseek-v4.1-flash-free',
    'opencode/glm-5.3-flash-free',
    'opencode/nemotron-3-ultra-free',
    'opencode/minimax-m3.1-flash-free',
    'opencode/beam-free',
)
DEFAULT_MODEL = FREE_MODELS[0]

# The instruction bound matches the status block's NEXT_AGENT_INSTRUCTION bound
# (overseer/statusblock.py), so an instruction the loop fed from a worker report
# cannot grow past what that parser accepted.
MAX_INSTRUCTION_CHARS = 4000


def is_free(model):
    """Return whether a model id is one of the recorded free gateway models."""
    return model in FREE_MODELS


def worker_argv(instruction, model=DEFAULT_MODEL, opencode=DEFAULT_OPENCODE,
                json_output=False):
    """Return the OpenCode worker argv for one instruction.

    The instruction is validated and placed as the single trailing element. A
    shell is never used, so the instruction cannot be split or interpreted. With
    ``json_output`` the stream is machine-readable; by default the model's text
    output is produced, so a downstream reader can find an AGENTS.md status
    block the model prints.
    """
    _require_instruction(instruction)
    if not isinstance(model, str) or model.count('/') < 1 or not model.strip():
        raise ValueError('a model id of the form provider/model is required')
    argv = [opencode, 'run', '--standalone', '--model', model, '--auto']
    if json_output:
        argv += ['--format', 'json']
    argv.append(instruction)
    return argv


RUNNERS = ('opencode', 'claude', 'codex')
DEFAULT_RUNNER = 'opencode'

# Environment markers that reveal an active coding-agent session, in priority
# order; the first present marker names the runner. These were recorded on
# 2026-10-21 (CLAUDECODE is set by Claude Code itself) and can go stale.
SESSION_MARKERS = (
    ('CLAUDECODE', 'claude'),
    ('CLAUDE_CODE_ENTRYPOINT', 'claude'),
    ('OPENCODE', 'opencode'),
    ('OPENCODE_BIN', 'opencode'),
    ('CODEX_SANDBOX', 'codex'),
    ('CODEX_HOME', 'codex'),
)


def _require_instruction(instruction):
    """Validate a worker instruction, or raise ValueError."""
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError('a non-empty instruction is required')
    if '\x00' in instruction:
        raise ValueError('the instruction must not contain a NUL character')
    if len(instruction) > MAX_INSTRUCTION_CHARS:
        raise ValueError('the instruction is longer than %d characters' % MAX_INSTRUCTION_CHARS)


def detect_session(env=None):
    """Detect the active coding-agent session from the environment.

    Returns ``{'runner', 'marker', 'detail'}``. ``runner`` is None when no known
    session marker is present. This reads only the given mapping (or os.environ);
    it never guesses from process inspection.
    """
    env = os.environ if env is None else env
    for marker, runner in SESSION_MARKERS:
        if env.get(marker):
            return {'runner': runner, 'marker': marker,
                    'detail': 'detected the %s session from $%s' % (runner, marker)}
    return {'runner': None, 'marker': None,
            'detail': 'no active coding-agent session detected'}


def default_runner(env=None):
    """Return the client to default to: the launching session's runner, else OpenCode.

    When an LLM session launched Overseer (its env marker is present), its own
    runner is the default, so work is driven by the model that ran it. With no
    session detected, the free OpenCode gateway is the fallback.
    """
    return detect_session(env)['runner'] or DEFAULT_RUNNER


def _claude_argv(instruction, model, claude='claude'):
    """Claude Code headless. Unverified here; it spends the account's credits."""
    argv = [claude, '-p', '--permission-mode', 'acceptEdits']
    if model:
        argv += ['--model', model]
    argv.append(instruction)
    return argv


def _codex_argv(instruction, model, codex='codex'):
    """Codex headless. Unverified here; it spends the account's credits."""
    argv = [codex, 'exec']
    if model:
        argv += ['--model', model]
    argv.append(instruction)
    return argv


def resolve_worker(instruction, model=None, runner=None, env=None,
                   opencode=DEFAULT_OPENCODE, claude='claude', codex='codex'):
    """Resolve the worker invocation for one instruction.

    Runner precedence: an explicit ``runner`` wins, else the detected session's
    runner is inherited, else the execution-safe default (OpenCode free). The
    result names the runner, the model, the argv, the detected session, and the
    source of the choice, so an inherited paid runner is never silent.
    """
    _require_instruction(instruction)
    detected = detect_session(env)
    chosen = runner or detected['runner'] or DEFAULT_RUNNER
    if chosen not in RUNNERS:
        raise ValueError('unknown runner: %s; expected one of %s'
                         % (chosen, ', '.join(RUNNERS)))
    if runner:
        source = 'explicit runner %s' % chosen
    elif detected['runner']:
        source = 'inherited %s session (via $%s)' % (detected['runner'], detected['marker'])
    else:
        source = 'default runner %s (no session detected)' % chosen
    if chosen == 'opencode':
        model = model or DEFAULT_MODEL
        argv = worker_argv(instruction, model=model, opencode=opencode, json_output=True)
    elif chosen == 'claude':
        argv = _claude_argv(instruction, model, claude)
    else:
        argv = _codex_argv(instruction, model, codex)
    return {'runner': chosen, 'model': model, 'argv': argv,
            'detected': detected, 'source': source}


def build_task(task_id, objective, workspace, checks, instruction,
               model=None, runner=None, env=None, timeout_seconds=600,
               opencode=DEFAULT_OPENCODE, repair_allowance=1):
    """Return ``(spec, resolved)``: a submittable command-mode factory task whose
    implementation is the resolved worker invocation.

    The spec carries a minimal valid contract whose acceptance identifiers match
    the checks one for one. Submitting and running it drives the chosen model;
    the factory validates, hashes, and freezes the spec as for any other task.
    """
    resolved = resolve_worker(instruction, model=model, runner=runner, env=env, opencode=opencode)
    spec = {
        'id': task_id, 'objective': objective, 'workspace': workspace,
        'timeout_seconds': timeout_seconds,
        'implementation': resolved['argv'],
        'checks': [list(check) for check in checks],
        'contract': {
            'role': 'implementation', 'risk_tier': 'low',
            'external_effects': [], 'protected_paths': [], 'approval_requirements': [],
            'acceptance_ids': ['A%d' % (index + 1) for index in range(len(checks))],
            'required_capabilities': [], 'project_constraints': [],
            'measured_evidence': None, 'provider_availability': None,
            'budget': {'wall_time_seconds': 600, 'token_limit': None,
                       'cost_limit_usd': None, 'resource_limits': None,
                       'repair_allowance': repair_allowance},
        },
    }
    return spec, resolved


def main(argv=None):
    """Print the resolved worker invocation for an instruction, as JSON.

    This only reports what would run; it dispatches nothing.
    """
    import argparse
    import json
    parser = argparse.ArgumentParser(description='Resolve a worker invocation.')
    parser.add_argument('instruction')
    parser.add_argument('--runner', choices=RUNNERS)
    parser.add_argument('--model')
    args = parser.parse_args(argv)
    resolved = resolve_worker(args.instruction, model=args.model, runner=args.runner)
    print(json.dumps(resolved, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
