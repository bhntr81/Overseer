# Reconcile the handoff record's identifier lists against the recorded exit codes

Status: **ready to execute at commit `2ef797d`**. The Overseer project's
dedicated prompt-writing agent wrote this prompt. The primary agent executes
it. Writing or acknowledging the prompt does not complete the step.

## Objective (the user's words, verbatim)

> Close the reconciliation gap in `overseer/reconcile.py` and `overseer/factory.py`:
> 1. Modify reconciliation so it compares the handoff record's completed/failing/not-run
>    acceptance IDs not just against the ledger contract, but against the actual command
>    exit codes and run evidence (e.g., verifying that claimed "completed" IDs actually map
>    to successful execution exits).
> 2. Ensure any mismatch surfaces a proper disagreement dictionary/report instead of
>    blindly trusting a faithful but incorrect record.
> 3. Add a corresponding test case in `tests/test_factory.py`.
> 4. Adhere strictly to AGENTS.md hardening mandates: Red-Green separation (test files
>    read-only during implementation); keep module line counts clean (under 300 lines);
>    re-derive reference maps and run `python3 scripts/check` and
>    `python3 scripts/check-doc-references` before finalizing.

This objective is the first half of the CONTEXT row's current "Next increment" cell
(`docs/HARNESS_FRAMEWORK.md:32`), quoted:

> the reconciliation reports a disagreement and nothing acts on it, and it never
> re-reads the run's own results: the completed, failing, and not-run identifier lists
> are checked against the contract the ledger stored but not against the exit codes the
> commands actually produced, so a record that was written wrongly and digested
> faithfully is reported as agreeing; the ledger also holds one evidence pointer per
> job, so only the latest run's record is reachable through it

**Out of scope:** the second half of that cell, one evidence pointer per job. It
stays a limit. Two more things stay out of scope: acting on a disagreement, and
comparing the dirty-worktree flag.

## Pillar row

Exactly one: **CONTEXT** (`docs/HARNESS_FRAMEWORK.md:32`). No other row's verdict
changes. Other rows change only where a cited line moved, and those citations are
re-derived.

## Preconditions (measured by the prompt writer at the time of writing)

1. `git rev-parse --short HEAD` prints `2ef797d` ("Reconcile the handoff record
   against the ledger row and the workspace"), branch `main`. If HEAD differs, stop
   and report `needs_input`.
2. The tree is expected to be dirty with exactly these entries:
   ```text
    M AGENTS.md
   ?? HARDENING_BLUEPRINT.md
   ?? CONTEXT_RECONCILE_RESULTS_NEXT_PROMPT.md
   ```
   `AGENTS.md` and `HARDENING_BLUEPRINT.md` belong to the operator. Do not edit,
   stage, or commit them. This prompt file is committed with the increment.
3. Baselines measured now:
   ```text
   $ python3 scripts/check </dev/null
   Ran 371 tests in 52.444s
   OK
   $ python3 scripts/check-doc-references
   204 references checked in HARNESS_FRAMEWORK.md
   $ sha256sum tests/test_factory.py
   305bfddb872e2ac6542cfcb6f808c3bf4d82ade95b212d4489fb2bc440f1e779  tests/test_factory.py
   ```
   Always redirect stdin (`</dev/null`). Even then, the log shows an interactive
   provider-picker transcript ending "cancelled; nothing was changed". One test
   prints it. It is not a failure. Read the `Ran N tests` / `OK` lines.
4. There is no `SPEC.md`. The ground truth is the blueprint's handoff sentence
   `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299` ("The successor checks the ledger and
   workspace before trusting the summary. If they disagree, reconcile.") plus the
   CONTEXT row. Re-read both before writing code (AGENTS.md:60).

## Binding directives (AGENTS.md, operator-modified)

- AGENTS.md:58 **Red-green separation.** Edit `tests/` only in Phase 1. In every
  later phase `tests/` is read-only.
- AGENTS.md:59 **Locality limit.** If a module modification adds more than 15% new
  lines, or creates large duplicate functions, split the logic or flag it.
  `HARDENING_BLUEPRINT.md` also flags any file over 300 lines. Budgets for this
  increment are under "Decision 6".
- AGENTS.md:60 **Ground-truth re-read** (see Precondition 4).
- The core mandates: execute before claiming, run up to 3 self-correction loops
  before escalating, write no placeholder stubs, and finish with the status block.

## Measured map (re-measure each line by content before editing)

| What | Where (at `2ef797d`) |
|---|---|
| `handoff.commands(results)`: projection with stage, argv, exit_code, timed_out, elapsed_seconds, log | `overseer/handoff.py:44` |
| `_acceptance(identifiers, results)`: the completed/failing/not-run rule | `overseer/handoff.py:84` |
| its only caller, inside `build` | `overseer/handoff.py:200` (`build` at `:187`) |
| `MAX_COMMANDS = 21` (one implementation command plus 20 checks) | `overseer/handoff.py:17` |
| checks are capped at 20 at submission | `overseer/factory.py:388` |
| manifest writer `_context_manifest` | `overseer/factory.py:1062` |
| manifest's command projection `commands = handoff.commands(results)` | `overseer/factory.py:1096` |
| manifest key `'commands_actually_run': commands` | `overseer/factory.py:1162` |
| `_record_handoff`, and the `handoff.json sha256=` event | `overseer/factory.py:1398`, `:1422` |
| `_ledger_facts` (reads the handoff digest from the latest `handoff` event) | `overseer/factory.py:1427` |
| `reconcile_handoff` | `overseer/factory.py:1452` |
| `reconcile.compare(reconcile.read_record(...), ledger, facts)` call | `overseer/factory.py:1475` |
| `results.json` rewritten after every command (4 sites) | `overseer/factory.py:2238`, `:2246`, `:2252`, `:2268` |
| `summary.json` built with `'results': results` | `overseer/factory.py:2292`–`2293` |
| `context.json` written and its digest sealed in a `context_manifest` event, in the same transaction as the final transition | `overseer/factory.py:2311`–`2320` |
| `reconcile-handoff` CLI dispatch | `overseer/factory.py:2357` |
| reconcile module constants / `LIMITS` | `overseer/reconcile.py:23`–`29` |
| `IDENTITY` table, `LEDGER_KEYS` | `overseer/reconcile.py:49`, `:54` |
| `is_secret`, `_depth`, `_schema_problem`, `_read_bytes`, `read_record` | `overseer/reconcile.py:67`, `:77`, `:93`, `:114`, `:135` |
| `_disagreement`, `_compare_identifiers`, `_compare_revisions`, `_verdict`, `compare` | `overseer/reconcile.py:173`, `:178`, `:205`, `:231`, `:242` |
| test class `HandoffReconciliationTests` | `tests/test_factory.py:3953` |
| helpers `ledger_row`, `recorded_digest`, `reseal_record`, `kinds`, `entry`, `unverifiable_fact` | `tests/test_factory.py:4004`, `:4007`, `:4014`, `:4025`, `:4028`, `:4034` |
| last test in the class (`test_the_secret_name_rule_agrees_with_the_codemap_rule`) | `tests/test_factory.py:4307` |
| next class `RequiredContractTests` | `tests/test_factory.py:4315` |
| `store_legacy_job` (writes a job row with no contract) | `tests/test_factory.py:54` |
| `attach_contract`: acceptance ids `A1..An`, one per check | `tests/test_factory.py:30` |

File sizes: `overseer/reconcile.py` 298, `overseer/factory.py` 2387,
`overseer/handoff.py` 287, `tests/test_factory.py` 4384 lines.

Writer's probe on a real run (implementation `pass`; checks `pass`,
`raise SystemExit(3)`, `pass`):
- `context.json` was 10284 bytes.
- `commands_actually_run` held the implementation (exit 0), A1 (exit 0), and A2
  (exit 3). There was no entry for A3.
- The ledger events, in order: `handoff` (`handoff.json sha256=<64 hex>`), then
  `context_manifest` (`context.json sha256=<64 hex>`), then `failed`.
- The record put `A3` in `not_run`.

## Decisions (settled; the executor applies them and does not reopen them)

### Decision 1: the exit-code authority is the sealed context manifest

The writer measured three candidate places that hold the exit codes:

- `runs/<id>/results.json` is rewritten after every command (`factory.py:2238`…`2268`).
  No digest of it is recorded anywhere. **It is not an authority.**
- The `results` key in `summary.json` (`factory.py:2293`) has no digest of its own
  in the ledger, and `reconcile_handoff` itself rewrites `summary.json`.
  **It is not an authority.**
- `commands_actually_run` in `context.json` (`factory.py:1162`) is the projection
  `handoff.commands(results)` of the same in-memory `results` list. The file's
  SHA-256 is written into the ledger as the `context_manifest` event
  `context.json sha256=<hex>` (`factory.py:2318`), in the same transaction as the
  final state transition. **This is the authority.** Its integrity can be checked:
  the file as read back must hash to the digest the ledger recorded.

The record's own `commands_actually_run` field is part of the record under test,
so it is never the authority.

Honest label, carried in the report: the authority is the factory's own record
of the exit codes. The ledger digest proves the manifest has not changed since
the attempt. It does not prove the factory observed the exits correctly. No
command is re-run, and no log is re-read. If the manifest's digest differs from
the ledger, the authority is untrusted: the result is `unverifiable` (see
Decision 4), never a comparison against the altered file.

### Decision 2: one classification rule, shared

- Rename `handoff._acceptance` to the public `handoff.acceptance`. Change only the
  name and its single caller (`handoff.py:200`). Keep its docstring. Its behaviour
  is the rule:
  - Acceptance results are the entries whose `stage == 'acceptance'`, in order.
  - Contract identifier `i` maps to the `i`-th acceptance result.
  - **completed**: it ran, `timed_out` is falsy, and `exit_code == 0`.
  - **failing**: it ran, and it timed out or exited non-zero. A signal shows up as
    a negative return code, and `None` is also failing.
  - **not_run**: `i >= len(ran)`, because the run stops at the first failing
    command.
  - The implementation command (stage `implementation`) maps to no identifier.
    Surplus acceptance results map to none either.
- The reconciliation applies this same function to the manifest's
  `commands_actually_run` entries. The projection keeps `stage`, `exit_code`, and
  `timed_out`. Identifiers are taken exactly as `build` takes them:
  `[str(v) for v in contract][:handoff.MAX_IDENTIFIERS]`.
- The new module imports `from overseer.handoff import acceptance`. This is
  allowed: `overseer/handoff.py` imports nothing. The new module and
  `reconcile.py` must never import `overseer.factory`, `overseer.codemap`, or
  `subprocess`.

### Decision 3: the new disagreement kind

There is one new kind, `acceptance_results_mismatch`. The closed list goes from
**nine kinds to ten**.

- The existing `acceptance_ids_mismatch` is unchanged: the lists must be disjoint
  and must cover the contract. The two checks are independent, and both may
  appear in one report.
- Comparison: for each of the three categories, compare the record's list **as a
  set** with the list derived from the authority. Any difference in any category
  produces exactly **one** `acceptance_results_mismatch` entry, not one per
  identifier.
- Order does not matter, so the existing
  `test_the_identifier_lists_are_compared_as_sets` must stay `agree`.

Shape of the entry: the four standard keys, plus two keys for per-identifier
detail.

```python
{'kind': 'acceptance_results_mismatch',
 'record':    {'completed': [...], 'failing': [...], 'not_run': [...]},  # record lists as written
 'authority': {'completed': [...], 'failing': [...], 'not_run': [...]},  # derived, contract order
 'reason': 'the record\'s identifier lists do not follow from the exit codes the context '
           'manifest recorded: an identifier is completed when its acceptance command '
           'exited 0, failing when it exited non-zero or timed out, and not run when the '
           'run stopped before it',
 'identifiers': [  # only identifiers whose membership differs, at most MAX_IDENTIFIERS
     {'id': 'A2', 'record': ['completed'], 'authority': 'failing',
      'exit_code': 3, 'timed_out': False}],
 'identifiers_beyond_bound': 0}
```

How `identifiers` is built:

- Visit the contract's identifiers in contract order. Then visit identifiers that
  appear only in the record, in first-appearance order across completed, failing,
  and not_run.
- `record` is the list of record categories that contain the identifier, in the
  fixed order `completed`, `failing`, `not_run`. It may be empty or hold two names.
- `authority` is the derived category, or `None` for an identifier not in the
  contract.
- `exit_code` and `timed_out` come from the matched acceptance command. Both are
  `None` when the command never ran or the identifier is not in the contract.
  (`timed_out` is `bool(...)` when the command ran.)
- An identifier is listed when `record != [authority]`.
- Keep the first `MAX_IDENTIFIERS` (20) entries. Count the rest in
  `identifiers_beyond_bound`.

### Decision 4: fail closed with real reasons

The read order is fixed, and each step's reason string is exact:

1. Evidence path is `None`: `'the job has no run evidence directory'`.
2. No digest recorded: use the reason the factory supplies, which is
   `'the ledger records no digest for the context manifest'`. When a
   `context_manifest` event exists without a digest, append `': <its detail>'`.
3. Bounded read. Check the size before opening the file, and cap the read:
   - `'the context manifest is larger than the 1048576 byte bound'`
   - `'the context manifest does not exist'`
   - `'the context manifest could not be read: <ExceptionTypeName>'`
4. Digest check: `'the digest of the context manifest as read back is not the
   digest the ledger recorded for it'`.
5. Parse:
   - `'the context manifest is not UTF-8 text'`
   - `'… is not JSON'`
   - `'… is nested deeper than the parser allows'`
   - `'… is not a JSON object'`
   - `'… is nested deeper than the 64 level bound'`
6. Shape:
   - `'the context manifest has no commands_actually_run list'`
   - `'the context manifest records more than 21 commands'`
   - `"the context manifest's command at index <i> is malformed"`. An entry is
     well-formed when it is a dict, `stage` is a `str`, `exit_code` is an `int`
     that is not a `bool`, or `None`, and `timed_out` is a `bool`. `<i>` is the
     0-based index.

Any of these makes one entry `{'fact': 'acceptance_results', 'reason': <reason>}`
in `unverifiable`. It never yields agreement.

When the stored contract is `None`, or names more than `MAX_IDENTIFIERS`, the
existing `acceptance_ids` entry already makes the report unverifiable. The results
check then adds `{'fact': 'acceptance_results', 'reason': 'the stored job names no
usable contract, so no identifier can be mapped onto a command; the acceptance_ids
entry says why'}` to **`not_applicable`**. It does not add a second unverifiable
entry. The results check runs only when the record was read.

Bounds are module constants: `MAX_MANIFEST_BYTES = 1024 * 1024`, depth 64 (the
existing `MAX_JSON_DEPTH`), and `MAX_COMMANDS = handoff.MAX_COMMANDS` (21). Add
`max_manifest_bytes` and `max_commands` to the report's `limits`.

### Decision 5: the report stays read-only

- No `transition`.
- No write to `handoff.json`, `context.json`, `results.json`, or the workspace.
- Exactly the existing three writes: `reconciliation.json`, the `reconciliation`
  key in `summary.json`, and one `reconciliation` event.
- The verdict rule is unchanged: a disagreement outranks unverifiable, and
  unverifiable is never agree.
- The report gains one block:

```python
'results': {'path': <str|None>, 'sha256': <hex of bytes read|None>,
            'recorded_sha256': <ledger digest|None>, 'read': <bool>, 'reason': <str|None>,
            'source': RESULTS_SOURCE}
```

`RESULTS_SOURCE` is: "commands_actually_run in the run's context.json, whose
digest the ledger recorded in its context_manifest event; these are the exit codes
the factory recorded once at the end of the attempt, and no command is re-run".
`LEDGER_KEYS` gains `'manifest_sha256'` and `'manifest_sha256_reason'`.

### Decision 6: placement and line budgets

**New module `overseer/readback.py`** (leaf; target ≤ 200 lines, hard cap < 300).
It reads run evidence back, bounded. It holds:

- `depth(value, bound)`, `read_bytes(path, bound, noun)`, and
  `parse_object(data, noun, max_depth)`. These are **moved** out of
  `reconcile.py`, not copied. The reason strings take the noun, so with
  `noun='record'` they are byte-identical to today's (`'the record is larger
  than the 65536 byte bound'`, `'the record does not exist'`, `'the record is not
  a JSON object'`, …). The existing tests assert some of these strings and must
  stay green untouched.
- `MAX_MANIFEST_BYTES`, `MAX_COMMANDS`, `RESULTS_SOURCE`, `acceptance` (imported
  from handoff).
- `read_results(path, recorded_sha256, recorded_reason)`, which returns the
  `results` block above plus `'commands'`. The `'commands'` key is used
  internally; strip it before the block enters the report.
- `compare_results(record, contract, info, disagreements, unverifiable,
  not_applicable)`, which appends to the lists like `_compare_identifiers` does.

**`overseer/reconcile.py`** must end **< 300** lines (target ≈ 270). It imports
`from overseer.readback import depth, read_bytes, parse_object, read_results,
compare_results`. `read_results` is re-exported so the factory calls
`reconcile.read_results(...)` and **`factory.py`'s import block does not change**.
`compare(record_info, ledger, workspace, results_info=None)`: when `results_info`
is `None`, treat it as `{'read': False, 'reason': 'no run-results authority was
supplied'}`, which fails closed.

**`overseer/factory.py`** grows by ≤ 30 lines (≈1.3%, far below 15%):

- Add `_recorded_digest(self, job_id, state, filename, label)`. It returns
  `(digest, None)` or `(None, reason)`, using the latest event of `state` and the
  regex `re.escape(filename) + r' sha256=([0-9a-f]{64})'`.
- `_ledger_facts` uses it twice: `('handoff', 'handoff.json', 'handoff record')`,
  which keeps today's reason string exactly, and `('context_manifest',
  'context.json', 'context manifest')`.
- `reconcile_handoff` passes `reconcile.read_results(evidence / 'context.json' if
  evidence else None, ledger['manifest_sha256'], ledger['manifest_sha256_reason'])`
  as the fourth argument of `compare`. Its docstring says it also reads the
  context manifest.

**`overseer/handoff.py`**: the rename only (net 0 lines).

## Required behavior (observable)

1. Take a record whose lists were forged to call a failed acceptance command
   "completed", resealed so its digest matches the ledger. Forge the record's own
   `commands_actually_run`, `results.json`, and `summary.json['results']` to agree
   with the lie. It still yields `verdict == 'disagree'` with exactly one
   `acceptance_results_mismatch` that names both sides.
2. A faithful record of a run with completed, failing, and not-run identifiers
   yields `agree`, with an empty `unverifiable` list.
3. Swapping the failing and not_run lists is a disagreement whose per-identifier
   detail names the recorded exit codes.
4. A missing, oversized, malformed, re-digested-but-malformed, tampered, or
   unsealed manifest yields `unverifiable` with the exact reason, and never `agree`.
5. Nothing changes the job row, the record, the manifest, or `results.json`.
6. All 371 existing tests stay green, with `tests/` unchanged after Phase 1.

## Tests (Phase 1 only; append inside `HandoffReconciliationTests`, after `:4307`'s test, before `RequiredContractTests`)

Import `overseer.readback` **inside test methods**, never at module top. A top-level
import would make the whole module fail in the red phase instead of showing
per-test failures.

Add two helpers to the class:

- `manifest_digest(job_id)`: the hex of the latest `context_manifest` event.
- `reseal_manifest(job_id, path)`: rewrite that event's detail to
  `'context.json sha256=%s' % sha256(path.read_bytes())` and commit.

Optionally add `forge_completed(job_id, evidence, record)`. It applies the lie
used by T1, T5c, and T8: set the record lists to `completed=['A1','A2']` and
`failing=[]`, set `record['commands_actually_run']['value'][2]['exit_code']=0`,
set `results.json[2]['exit_code']=0` and `summary.json['results'][2]['exit_code']=0`,
then call `reseal_record`. Index 0 is the implementation command, 1 is A1, and 2
is A2.

Specs:

- `two = [[sys.executable,'-c','pass'], [sys.executable,'-c','raise SystemExit(3)']]`
- `three = two + [[sys.executable,'-c','pass']]`

Name the tests exactly as follows.

- **T1** `test_a_completed_identifier_whose_command_failed_is_a_results_disagreement`
  (spec `two`, then `forge_completed`):
  - `report['verdict'] == 'disagree'`
  - `self.kinds(report) == ['acceptance_results_mismatch']`
  - `entry['record'] == {'completed': ['A1','A2'], 'failing': [], 'not_run': []}`
  - `entry['authority'] == {'completed': ['A1'], 'failing': ['A2'], 'not_run': []}`
  - `entry['identifiers'] == [{'id':'A2','record':['completed'],'authority':'failing','exit_code':3,'timed_out':False}]`
  - `entry['identifiers_beyond_bound'] == 0`
  - `assertIn('exit', entry['reason'])`
  - `report['results']['read'] is True`
  - `report['results']['sha256'] == sha256(context.json) == self.manifest_digest(id) == report['results']['recorded_sha256']`
  - `assertIn('context.json', report['results']['source'])`
- **T2** `test_a_faithful_record_of_a_partly_failed_run_agrees_with_the_recorded_exit_codes`
  (spec `three`, untouched):
  - the record lists are `['A1']`, `['A2']`, `['A3']`
  - `verdict == 'agree'`, `disagreements == []`, `unverifiable == []`
  - `'acceptance_results' not in [i['fact'] for i in report['not_applicable']]`
  - `report['results']['reason'] is None`
  - `report['ledger']['manifest_sha256'] == self.manifest_digest(id)`
- **T3** `test_swapped_failing_and_not_run_lists_are_a_results_disagreement`
  (spec `three`; set `failing=['A3']`, `not_run=['A2']`, reseal):
  - `kinds == ['acceptance_results_mismatch']`
  - record side `{'completed':['A1'],'failing':['A3'],'not_run':['A2']}`
  - authority `{'completed':['A1'],'failing':['A2'],'not_run':['A3']}`
  - `identifiers == [{'id':'A2','record':['not_run'],'authority':'failing','exit_code':3,'timed_out':False}, {'id':'A3','record':['failing'],'authority':'not_run','exit_code':None,'timed_out':None}]`
- **T4** `test_a_missing_context_manifest_makes_the_results_unverifiable`
  (unlink `context.json`):
  - `verdict == 'unverifiable'`
  - `self.unverifiable_fact(report,'acceptance_results')['reason'] == 'the context manifest does not exist'`
  - `report['results']['read'] is False`
  - `disagreements == []`
- **T5** `test_a_malformed_or_tampered_context_manifest_is_unverifiable_with_the_reason`.
  Three sub-cases, each on its own job:
  - (a) Write `'[]'` and reseal. Reason `== 'the context manifest is not a JSON object'`.
  - (b) Set `commands_actually_run[1]['exit_code'] = '0'` and reseal. Reason
    `== "the context manifest's command at index 1 is malformed"`.
  - (c) Run spec `two` with `forge_completed`. Then set the manifest's
    `commands_actually_run[2]['exit_code'] = 0` **without** resealing. Expect
    `verdict == 'unverifiable'`, `disagreements == []`, and the reason equal to
    the digest string from Decision 4.
- **T6** `test_an_oversized_context_manifest_is_unverifiable_before_it_is_read`
  (write `b' ' * (MAX_MANIFEST_BYTES + 1)`, no reseal):
  - reason `== 'the context manifest is larger than the %d byte bound' % MAX_MANIFEST_BYTES`
- **T7** `test_a_context_manifest_without_a_ledger_digest_is_unverifiable`
  (delete the job's `context_manifest` events):
  - reason `== 'the ledger records no digest for the context manifest'`
  - `report['ledger']['manifest_sha256'] is None`
- **T8** `test_a_results_disagreement_changes_nothing` (spec `two`, `forge_completed`):
  - the row's `state`/`detail`/`run_id`/`spec_hash` are unchanged
  - the event count is +1, and the last event is `'reconciliation'`
  - the bytes of `handoff.json`, `context.json`, and `results.json` are unchanged
- **T9** `test_the_results_check_uses_the_handoff_classification_rule`:
  - `from overseer import handoff, readback`
  - `assertIs(readback.acceptance, handoff.acceptance)`
- **T10** `test_a_job_without_a_contract_skips_the_results_check_as_not_applicable`.
  Build `spec = self.spec('legacy')`, `spec.pop('contract')`, call
  `store_legacy_job(self.f, spec)`, then `run_one`. Assert:
  - `'acceptance_ids'` is in the unverifiable facts
  - `'acceptance_results'` is in the `not_applicable` facts and **not** in the
    unverifiable facts

Do not edit any existing test. The existing
`test_acceptance_identifiers_that_do_not_match_the_stored_contract_are_a_disagreement`
will now also produce an `acceptance_results_mismatch`. It uses `self.entry`, so it
stays valid.

## Mutations (Phase 3; implementation code only; revert byte-for-byte; run the class alone)

| # | Mutation | Must be caught by |
|---|---|---|
| M1 | `compare_results` never appends the disagreement | T1, T3 |
| M2 | categories compared as ordered lists, not sets | existing `test_the_identifier_lists_are_compared_as_sets` |
| M3 | manifest digest check skipped | T5(c) |
| M4 | an unread authority appends nothing to `unverifiable` | T4, T5, T6, T7 |
| M5 | authority derived from the record's own `commands_actually_run` | T1 |
| M6 | authority read from `results.json` instead of `context.json` | T1 |
| M7 | the manifest digest taken from the `handoff` event | T2 |
| M8 | per-identifier `identifiers` emptied | T1, T3 |
| M9 | the mismatch appended to `unverifiable` instead of `disagreements` | T1 (verdict) |
| M10 | entry-shape validation removed | T5(b) |
| M11 | size check removed (whole file read) | T6 (exact reason) |
| M12 | `reconcile_handoff` rewrites `context.json` | T8 and existing `test_the_result_is_recorded_in_the_evidence_directory_the_summary_and_the_event` |

If a mutation survives, return to Phase 1 under the protocol below. Do not weaken
the mutation.

## Execution order: five phases

**Phase 0: ground truth.** Re-read `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299` and
`docs/HARNESS_FRAMEWORK.md:32`. Re-measure the map. Re-run the two baseline
commands and record their real output.

**Phase 1: red. Only `tests/test_factory.py` is written.** Add the helpers and
T1–T10. Run
`python3 -m unittest tests.test_factory.HandoffReconciliationTests -v </dev/null`
and paste the real failure/error counts. Expect the new tests to fail or error:
there is no `results` key, no new kind, and no `overseer.readback`. Expect the
existing class tests to pass. Then run `sha256sum tests/test_factory.py` and
record the digest.

**Phase 2: green. `tests/` is READ-ONLY.** Implement Decisions 2–6. At the end,
`sha256sum tests/test_factory.py` must equal the Phase 1 digest, or the increment
is unacceptable.

If a test is wrong (its expectation contradicts a decision or a measured fact):

1. Stop writing implementation.
2. Return to Phase 1 and fix only that test.
3. Record the reason and the new digest in WORK_LOG.
4. Re-show red on a clean export:
   `git archive HEAD | tar -x -C <scratch>`, copy in the test file, run the class.
5. Resume Phase 2.

Never touch `tests/` while an implementation file is open for writing.

**Phase 3: mutations.** Apply M1–M12 as above. After the set, compare the
`sha256sum overseer/*.py` output with the pre-mutation values.

**Phase 4: documentation.** See below.

**Phase 5: verify and commit.** See below.

Self-correction: up to 3 fix-and-rerun loops per failure. If the same failure
recurs with no new evidence, stop with `STUCK_NEEDS_ESCALATION`.

## Documentation (Phase 4)

**`docs/HARNESS_FRAMEWORK.md:32` (CONTEXT row)**

- Citations: re-derive every `overseer/reconcile.py:` citation by content. Today:
  - `:49` ledger identity comparison
  - `:114` bounded record read: this function moves to `readback.py`, so cite
    `overseer/readback.py:<read_bytes>`
  - `:135` read-back
  - `:178` sets
  - `:205` revisions
  - `:231` verdict
  - `:242` report
  - `:58`, in the does-not-claim bullet
- Shift every `overseer/factory.py:` citation after the edited hunks by the
  measured deltas (85 distinct factory citations exist in the file), and confirm
  each by content. The `tests/test_factory.py` citations (`:77`, `:3389`) lie
  before the new tests and should not move. Verify that.
- Add new citations:
  - the results authority reader (`readback.py` `read_results`)
  - the results comparison (`compare_results`)
  - the shared classification rule (`handoff.py` `acceptance`)
  - the manifest digest lookup in `_ledger_facts` / `_recorded_digest`
- Verdict: keep `partial`. Replace "with the contract the ledger stored (the three
  identifier lists, as sets that must be disjoint and cover the contract)" with a
  sentence that also says the lists are compared, as sets, with the lists that
  follow from the exit codes the context manifest recorded. The manifest's digest
  is checked against the ledger's `context_manifest` event first. A missing,
  oversized, malformed, or re-digested manifest is unverifiable with its reason.
- Change "a closed list of nine disagreement kinds" to "ten".
- Change "it re-verifies nothing" to "it re-runs and re-accepts nothing".
- **New "Next increment"** (true after this change; use this text or an
  equally honest one):
  > the reconciliation reports a disagreement and nothing acts on it; the exit codes it
  > checks the identifier lists against are the factory's own record in the context
  > manifest — the ledger digest proves that record unchanged since the attempt, not that
  > the factory observed the exits correctly, and the per-command logs are not re-read;
  > the ledger also holds one evidence pointer per job, so only the latest run's record
  > and manifest are reachable through it

**Does-not-claim bullet** (`docs/HARNESS_FRAMEWORK.md`, the reconciliation bullet
near line 124): say that it re-runs nothing, and that the results it compares
against are the manifest's recorded exit codes, sealed by digest, not a fresh
observation. Keep "a workspace that moved on … is not proof that the record is
wrong". Re-cite the bullet by content.

**`README.md:102`–`122`**:

- Add the fourth authority: the exit codes recorded in the digest-sealed
  `context.json`.
- Change "nine" to "ten", and add `acceptance_results_mismatch` to the list.
- Add an unreadable or re-digested manifest to the unverifiable sentence.
- Say that it reads `context.json` and never rewrites it.

**`WORK_LOG.md`**: add a new section at the end titled "### The handoff record's
identifier lists reconciled against the recorded exit codes". Include:

- the objective, verbatim
- the pillar
- the prompt's authorship ("written by the dedicated prompt-writing agent")
- the six decisions, plus any departure with its measured reason
- the red-green evidence: Phase 1 counts, digests, and any return
- line counts before and after for `reconcile.py`, `readback.py`, `factory.py`,
  and `handoff.py`, with factory growth in %
- the real command outputs
- test and reference counts, before and after
- each mutation and the test that caught it
- the citation re-derivation method
- the remaining limits, matching the new Next increment

Also note that the earlier entry's sentence "that is the only file besides the
record that the reconciliation opens" is now superseded: `context.json` is read.

Then run `python3 scripts/check-doc-references` and confirm `0` unresolved
references.

## Verification commands (Phase 5; paste real output)

```text
python3 -m py_compile overseer/readback.py overseer/reconcile.py overseer/factory.py overseer/handoff.py
python3 scripts/check </dev/null            # Ran N tests ... OK  (N = 371 + new tests)
python3 scripts/check-doc-references        # M references checked, exit 0
wc -l overseer/readback.py overseer/reconcile.py overseer/factory.py overseer/handoff.py
grep -n "overseer.factory\|overseer.codemap\|subprocess" overseer/reconcile.py overseer/readback.py   # no output
git diff --stat 2ef797d -- tests/            # only tests/test_factory.py
sha256sum tests/test_factory.py              # equals the Phase 1 digest
```

CLI demo in a scratch directory (not the repo). Run a two-check job whose second
check fails, forge `handoff.json` as in T1 and reseal its event, then run
`python3 -m overseer.factory --db <scratch>/jobs.sqlite3 reconcile-handoff <id>`.
Expect verdict `disagree` with `acceptance_results_mismatch` and exit 0. An
unknown id must still print `{"error": "unknown job"}` and exit 1.

## Acceptance criteria (observable)

- All tests pass: the count is 371 plus the new tests, and the output says `OK`.
- The reference check exits 0.
- `reconcile.py` is < 300 lines. `readback.py` is < 300 lines. `factory.py` grew
  by ≤ 30 lines.
- T1–T10 exist with the assertions above. M1–M12 each fail at least one named test.
- The Phase 1 digest equals the final digest of `tests/test_factory.py`.
- The docs say ten kinds. The CONTEXT Next increment matches reality and keeps
  the one-evidence-pointer limit.
- The commit contains only the allowed paths. `git status --short` afterwards
  shows only ` M AGENTS.md` and `?? HARDENING_BLUEPRINT.md`.

## Allowed paths, staging, commit

Allowed:

- `overseer/readback.py` (new)
- `overseer/reconcile.py`
- `overseer/factory.py`: `_recorded_digest`, `_ledger_facts`, and
  `reconcile_handoff` only
- `overseer/handoff.py`: the rename only
- `tests/test_factory.py`: Phase 1 only, new helpers and tests only
- `docs/HARNESS_FRAMEWORK.md`
- `README.md`
- `WORK_LOG.md`
- this prompt file

Never `git add -A` or `git add .`.

```text
git add overseer/readback.py overseer/reconcile.py overseer/factory.py overseer/handoff.py \
        tests/test_factory.py docs/HARNESS_FRAMEWORK.md README.md WORK_LOG.md \
        CONTEXT_RECONCILE_RESULTS_NEXT_PROMPT.md
git commit -F <scratch>/msg.txt
```

Commit message (repo voice; adjust only if facts differ):

```text
Reconcile the handoff record's identifier lists against the recorded exit codes

The reconciliation now reads the run's context.json, checks its digest
against the ledger's context_manifest event, and derives the completed,
failing, and not-run identifiers from the exit codes it recorded, with the
same rule the handoff record uses. A record whose lists do not follow from
those exit codes is an acceptance_results_mismatch naming both sides and
each differing identifier; a missing, oversized, malformed, or re-digested
manifest is unverifiable with its reason. The bounded readers move to the
new overseer/readback.py, and the report stays read-only.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## Stopping condition

Stop after this one increment and its single commit. In the report, include:

- the commit hash and the diff stat
- the real outputs of the verification commands
- the test and reference counts, before and after
- the line counts
- the red-green digests and any Phase 1 return
- the mutation table with results

Report `step_done`, and put the CONTEXT row's **new** Next increment in
`remaining`. The one-evidence-pointer-per-job limit and the
factory-recorded-exit-codes limit both remain. This condition ends this prompt,
not the objective loop. The results go back to the prompt-writing agent. Do not
start the next increment.

End the response with the AGENTS.md status block:

```yaml
STATUS: [SUCCESS | STUCK_NEEDS_ESCALATION]
TESTS_PASSED: [TRUE | FALSE]
FILES_MODIFIED: [<list of files>]
NEXT_AGENT_INSTRUCTION: "<clear self-contained prompt for next iteration>"
```
