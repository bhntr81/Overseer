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

This module only builds the command. Nothing here runs it, reads a file, or
talks to a network; the factory runs the argv and records the evidence.
"""

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
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError('a non-empty instruction is required')
    if '\x00' in instruction:
        raise ValueError('the instruction must not contain a NUL character')
    if len(instruction) > MAX_INSTRUCTION_CHARS:
        raise ValueError('the instruction is longer than %d characters' % MAX_INSTRUCTION_CHARS)
    if not isinstance(model, str) or model.count('/') < 1 or not model.strip():
        raise ValueError('a model id of the form provider/model is required')
    argv = [opencode, 'run', '--standalone', '--model', model, '--auto']
    if json_output:
        argv += ['--format', 'json']
    argv.append(instruction)
    return argv
