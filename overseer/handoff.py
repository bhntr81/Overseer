"""The blueprint's handoff record: one attempt's own evidence, summarized.

The blueprint asks that, on handoff, the objective, the base and candidate
revisions, the completed and failing acceptance identifiers, the environment
state, the commands actually run, the unresolved effects, the remaining
budget, and the next eligible action are persisted, and that the successor
checks the ledger and the workspace before trusting the summary.

This module builds that record from the facts of one run. Every field is
traceable to that run's evidence, or it is marked unmeasured with the reason
that it could not be observed. Nothing is estimated, nothing is guessed, and
nothing is carried over from another run. The record never judges the
attempt: it tells a successor what the attempt left behind.
"""

MAX_TEXT_CHARS = 4096
MAX_COMMANDS = 21
MAX_IDENTIFIERS = 20
LIMITS = {'max_text_chars': MAX_TEXT_CHARS, 'max_commands': MAX_COMMANDS,
          'max_identifiers': MAX_IDENTIFIERS}

NOTE = ('this record summarizes the evidence of one attempt only; the ledger row '
        'and the workspace are the authority, and the successor checks both '
        'before trusting this summary and reconciles a disagreement between '
        'them; a run that was interrupted leaves no record, so a missing '
        'handoff.json is itself information')

SCOPE_RULE = ('this record describes the attempt that produced this run\'s '
              'evidence; it is never merged with another run\'s record, and a '
              'later attempt of the same job writes its own record in its own '
              'run directory')

ACTIONS = ('product_review', 'bounded_repair', 'controller_decided')
DECIDERS = ('the factory', 'the successor')


def _text(value, limit=MAX_TEXT_CHARS):
    """Return a string bounded in length; a cut string says that it was cut."""
    if not isinstance(value, str) or len(value) <= limit:
        return value
    return value[:limit] + ' [cut at %d characters]' % limit


def commands(results):
    """Return the commands this run actually ran, as the manifest projects them.

    A result without an argument vector is not a command and is skipped. The
    manifest and the handoff record use this one projection, so the two lists
    cannot drift apart.
    """
    projected = []
    for result in results or []:
        if 'argv' not in result:
            continue
        projected.append({
            'stage': result.get('stage'),
            'argv': list(result['argv']),
            'exit_code': result.get('exit_code'),
            'timed_out': bool(result.get('timed_out')),
            'elapsed_seconds': result.get('elapsed_seconds'),
            'log': result.get('log'),
        })
    return projected


def candidate_revision(receipt):
    """Return the candidate revision of a workspace-diff receipt.

    A revision is observed only when the attempt moved HEAD. A worktree that
    was not committed is not a revision, and the reason says so.
    """
    receipt = receipt or {}
    if receipt.get('captured') and receipt.get('head_moved') and receipt.get('head_after'):
        return {'value': receipt['head_after'],
                'source': 'git rev-parse HEAD after the implementation command; HEAD '
                          'moved during the attempt'}
    return {'value': None,
            'source': 'unmeasured: HEAD did not move during the attempt, and an '
                      'uncommitted worktree is not a revision'
                      if receipt.get('captured') else
                      'unmeasured: no workspace diff was captured'}


def _acceptance(identifiers, results):
    """Return the completed, failing, and not-run identifiers of this run.

    The contract names one identifier per acceptance command, and the run loop
    stops at the first failing command, so the acceptance results that exist
    are a prefix of the checks. An identifier whose command never ran is not
    failing and is not completed: it is not run.
    """
    ran = [result for result in (results or []) if result.get('stage') == 'acceptance']
    completed, failing, not_run = [], [], []
    for index, identifier in enumerate(identifiers):
        if index >= len(ran):
            not_run.append(identifier)
            continue
        result = ran[index]
        if result.get('timed_out') or result.get('exit_code') != 0:
            failing.append(identifier)
        else:
            completed.append(identifier)
    return completed, failing, not_run, ran


def _identifier_source(identifiers, ran):
    """Return the source of the three identifier lists, and why it is what it is."""
    if not identifiers:
        return ('unmeasured: the stored job names no acceptance identifiers, so no '
                'identifier can be completed or failed')
    if len(ran) > len(identifiers):
        return ('the contract names %d identifiers and this run produced %d acceptance '
                'results; the surplus results are listed under commands_actually_run '
                'and no identifier is invented for them'
                % (len(identifiers), len(ran)))
    return ('the contract names one identifier per acceptance command; an identifier '
            'is completed when its command exited 0, failing when it exited non-zero '
            'or timed out, and not run when the run stopped before it')


def _failure_evidence(results, ran, failing, identifiers, detail):
    """Return the observed evidence of a failed run, in one sentence."""
    implementation = next((result for result in (results or [])
                            if result.get('stage') == 'implementation'), None)
    if implementation is None:
        return 'no command produced a result; the run reported: %s' % (detail or 'no detail')
    if implementation.get('timed_out') or implementation.get('exit_code') != 0:
        return ('the implementation command exited %s%s'
                % (implementation.get('exit_code'),
                   ' and timed out' if implementation.get('timed_out') else ''))
    if failing:
        index = identifiers.index(failing[0]) if failing[0] in identifiers else 0
        result = ran[index] if index < len(ran) else {}
        return ('the acceptance command %s exited %s'
                % (failing[0], result.get('exit_code')))
    return 'the run reported: %s' % (detail or 'no detail')


def _next_action(mode, state, detail, results, ran, failing, identifiers):
    """Return the next eligible action of this run, and who decides it."""
    if mode != 'command':
        return {'value': {'action': 'controller_decided', 'decided_by': 'the factory',
                          'reason': 'the %s mode is a controller-owned slice; its own '
                                    'receipt is the authority and the factory has no '
                                    'further step for this attempt' % mode},
                'source': 'the run\'s mode and its final state',
                'unmeasured': []}
    if state == 'passed':
        return {'value': {'action': 'product_review', 'decided_by': 'the successor',
                          'reason': 'every acceptance command of this run exited 0; a '
                                    'passed attempt is a candidate and not a product or '
                                    'release acceptance'},
                'source': 'the run\'s final state and the exit codes of its commands',
                'unmeasured': ['unresolved_effects']}
    evidence = _failure_evidence(results, ran, failing, identifiers, detail)
    return {'value': {'action': 'bounded_repair', 'decided_by': 'the successor',
                      'reason': '%s; the blueprint\'s policy is a bounded repair within '
                                'the same task budget' % evidence},
            'source': 'the run\'s final state and the observed exit codes of its commands',
            'unmeasured': ['remaining_budget', 'unresolved_effects', 'failure_class']}


def _nulls(value):
    """Return the names of the sub-values of a mapping that are null."""
    if not isinstance(value, dict):
        return []
    return [name for name, item in value.items() if item is None]


def _mode_result(results, detail):
    """Return the controller-owned mode's own result, or None in command mode."""
    for result in results or []:
        stage = result.get('stage')
        if stage in ('fixture', 'fake_provider', 'isolation_probe'):
            value = {'stage': stage,
                     'exit_code': result.get('exit_code'),
                     'timed_out': bool(result.get('timed_out')),
                     'detail': result.get('detail') or detail}
            return {'value': value,
                    'source': 'the %s mode\'s own result; its receipt is the authority' % stage,
                    'unmeasured': _nulls(value)}
    return {'value': None,
            'source': 'not applicable: the command mode runs no controller-owned verification',
            'unmeasured': ['mode_result']}


def build(job_id, run_id, spec, spec_hash, epoch, results, receipt,
          base_identity, state, detail):
    """Return the blueprint's handoff record for one attempt.

    Every field is one observation of this run, or it is unmeasured with the
    reason that it could not be observed. The function never raises for a
    missing identity, a missing receipt, a result without an argument vector,
    or a spec without a contract: the field that could not be measured says so.
    """
    spec = spec if isinstance(spec, dict) else {}
    contract = spec.get('contract') or {}
    mode = spec.get('mode') or 'command'
    identifiers = [str(value) for value in (contract.get('acceptance_ids') or [])][:MAX_IDENTIFIERS]
    completed, failing, not_run, ran = _acceptance(identifiers, results)
    identity = base_identity or {}
    if identity.get('present'):
        base = {'value': identity.get('base_commit'),
                'source': 'git rev-parse HEAD observed at attempt start, before the '
                          'implementation command'}
    else:
        base = {'value': None,
                'source': 'unmeasured: %s' % (identity.get('reason')
                                              or 'the attempt-start repository identity '
                                                 'was not observed')}
    identifier_source = _identifier_source(identifiers, ran)
    ran_commands = commands(results)
    environment = {
        'mode': mode,
        'epoch': epoch,
        'timeout_seconds': spec.get('timeout_seconds'),
        'tokens': None,
        'cost_usd': None,
        'environment_digest': None,
    }
    attempt = {'value': {'attempt_id': None, 'lease_generation': None},
               'source': 'the command mode reserves no attempt lease; the attempts table '
                         'is written by the lease allocator, which this path never calls',
               'unmeasured': ['attempt_id', 'lease_generation']}
    fields = {
        'objective': {'value': _text(spec.get('objective')),
                      'source': "the task specification field 'objective'"},
        'base_revision': base,
        'candidate_revision': candidate_revision(receipt),
        'completed_acceptance_ids': {'value': completed, 'source': identifier_source},
        'failing_acceptance_ids': {'value': failing, 'source': identifier_source},
        'not_run_acceptance_ids': {'value': not_run, 'source': identifier_source},
        'environment_state': {
            'value': environment,
            'source': 'the runner\'s own facts: the mode, the controller epoch, and the '
                      'per-command timeout; tokens and cost are null and never '
                      'estimated, and the factory computes no environment digest',
            'unmeasured': sorted(set(_nulls(environment)) |
                                  {'tokens', 'cost_usd', 'environment_digest'})},
        'commands_actually_run': {
            'value': ran_commands,
            'source': 'the results of this run: each command with its stage, argument '
                      'vector, exit code, timeout flag, elapsed time, and log path'
                      if ran_commands else
                      'this run executed no argument-vector command; the %s mode runs a '
                      'controller-owned verification instead' % mode},
        'mode_result': _mode_result(results, detail),
        'attempt': attempt,
        'unresolved_effects': {
            'value': None,
            'source': 'unmeasured: the factory observes no effect outside the workspace '
                      'and the ledger; the contract\'s external effects are a declaration '
                      'and not an observation, and the patch receipt shows what the '
                      'workspace held, not which process made a change'},
        'remaining_budget': {
            'value': None,
            'source': 'unmeasured: the contract declares a repair allowance, but the '
                      'factory tracks no consumption, so what remains of the budget '
                      'cannot be derived'},
        'next_eligible_action': _next_action(mode, state, detail, results, ran,
                                             failing, identifiers),
    }
    unmeasured = []
    for name, field in fields.items():
        if field['value'] is None and name not in unmeasured:
            unmeasured.append(name)
        for sub in field.get('unmeasured') or []:
            if sub not in unmeasured:
                unmeasured.append(sub)
    record = {
        'version': 1,
        'kind': 'handoff_record',
        'job_id': job_id,
        'run_id': run_id,
        'spec_hash': spec_hash,
        'epoch': epoch,
        'mode': mode,
        'state': state,
        'detail': _text(detail),
        'scope': {'rule': SCOPE_RULE},
        'acceptance_ids_source': 'contract' if identifiers else 'absent',
        'unmeasured': unmeasured,
        'note': NOTE,
        'limits': dict(LIMITS),
    }
    record.update(fields)
    return record
