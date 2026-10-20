# Widen the selection with the relation and the memory

Status: **ready to execute**. This prompt was written by the dedicated
prompt-writing agent of the Overseer project. The primary agent executes it;
writing it is not completion.

Its file and line references describe the repository at the starting commit
below. The increment will move lines of `overseer/codemap.py`,
`overseer/factory.py`, and `tests/test_factory.py`. Three review lessons are
carried forward and are part of the acceptance:

1. **Line citations drift.** The references here are not updated after the
   change. Every citation in the documentation is re-derived by hand against
   the code after the last edit, in every pillar row it touches, not copied
   from this prompt.
2. **A test is only evidence if a plausible wrong implementation fails it.**
   The last two reviews found tests that survived most mutations. Section 8
   names the mutations the executor must apply, one at a time, and show the
   suite failing for each, then revert.
3. **Counts describe what is shown.** A count of widened files is the number
   of widened files in `selected`, not the number of candidates; what a bound
   left out is counted apart, with its reason.

This prompt files exactly one increment against the **CONTEXT** row of the
harness pillar map (`docs/HARNESS_FRAMEWORK.md:32`). It does not plan work for
the CONTRACT, TOOLS, POLICY, STATE, PERMISSIONS, or EVIDENCE rows.

Order: `WRITER_LOOP_NEXT_PROMPT.md` takes priority and runs first. If it has
landed, re-run the two baseline commands before starting and use their counts
in place of the 250 / 138 below, and re-derive the `docs/HARNESS_FRAMEWORK.md`,
`README.md`, and `WORK_LOG.md` line references here, which that increment
moves.

## Outcome

The codebase map selects, in addition to the files the task commands name and
the files whose path matches the task terms, the files that a **current
decision** names by path and the files that hold a **caller of a selected
symbol**, even when the task terms do not match them — within the existing
selection bound of 12 files, never displacing a file the task itself selected.
A widened file says why it was widened and by what. The widening is one round,
bounded, deterministic, and it reaches the attempt through the digest and the
manifest. What the bound left out is recorded with the reason.

## Repository and starting commit

- Repository: `/home/kali/Programming/Projects/Overseer` (git root, branch
  `main`).
- Starting commit: `4a133d21f74ea702f83819acf10de1de180832c8`
  ("Attach the recalled memory records to the symbols they name").
- Working tree clean at the time of writing.
- Python 3 standard library only. No new dependency. Nothing is installed.

## Relevant paths and existing example

| Path and line | What it is now |
| --- | --- |
| `overseer/codemap.py:28` | the module-level bounds, `MAX_FILES` through `MAX_SUMMARY_MEMORY_LINES` (line 58); `MAX_SELECTED = 12` at line 31 |
| `overseer/codemap.py:109` | `scan(workspace)`: the file tree; each entry has `path` and `kind` |
| `overseer/codemap.py:137` | `structure(path)`; `excerpt(path, symbols, budget)` at 170 |
| `overseer/codemap.py:160` | `is_secret(path)` |
| `overseer/codemap.py:272` | `is_test_file(path)` |
| `overseer/codemap.py:370` | `search_references(files, selected_paths, root)`: **one** search; `references[path]` is a per-file index of names and attributes, not per symbol |
| `overseer/codemap.py:465` | `symbol_relations(entry, references, searched_files)`; a caller record is built at 510 (`file`, `line`, `kind`, `how`) and excludes test files |
| `overseer/codemap.py:579` | `_path_pattern(path)`: a workspace path on path boundaries, the matcher to reuse |
| `overseer/codemap.py:687` | `attach_memory(selected, records)`: the record keys it reads, `informs_decision` included |
| `overseer/codemap.py:862` | `select(files, terms, named, root)`: named files (score 100), then term matches, capped at `MAX_SELECTED` |
| `overseer/codemap.py:892` | `assemble(workspace, spec, memory=None)`: select, structure and excerpt, relation search, relations, memory |
| `overseer/codemap.py:986` | `summary(context, limit)`: the digest, with its tail-room logic for the memory line |
| `overseer/factory.py:1022` | `_codebase_environment`: `OVERSEER_CODEBASE_*` (memory count at 1032) |
| `overseer/factory.py:1036` | `_context_manifest` |
| `overseer/factory.py:1091` | the `relevant_code_and_interfaces` source string |
| `overseer/factory.py:1162` | the manifest `codebase` block; its `selected` list at 1168, `relations` at 1178, `memory` at 1202 |
| `overseer/factory.py:1912` | the recall, computed before the map |
| `overseer/factory.py:1922` | `assemble_codebase(spec.get('workspace'), spec, memory=...)` |
| `tests/test_factory.py:1804` | `codebase_of(result)`; `write_source` at 1807 |
| `tests/test_factory.py:1868` | the term-selection test (`unrelated.py` must stay unselected) |
| `tests/test_factory.py:1889` | `test_the_selection_is_bounded` (20 term-matched files fill 12) |
| `tests/test_factory.py:2253` | `test_the_attempt_sees_the_relation`, the environment-carrying example |
| `tests/test_factory.py:2336` | the memory attachment tests; `record(...)`, the plain-dict helper, at 2573 |
| `README.md:57` | the manifest, recall, and codebase paragraph (to line 99) |
| `docs/HARNESS_FRAMEWORK.md:32` | the CONTEXT row |
| `docs/HARNESS_FRAMEWORK.md:41` | the process-order CONTEXT sentences |
| `docs/HARNESS_FRAMEWORK.md:103` | the context-manifest bullet under "What this framework does not claim" |
| `WORK_LOG.md:2288` | the last entry; the new entry goes after the end of the file (line 2336) |

Existing example to follow: `attach_memory` and `search_references` — pure
functions, module constants for every bound, counts that describe what is
kept, a `reason` for everything left out.

## Required behavior

### 1. Where it lives

Add one pure function to `overseer/codemap.py`:

```python
def widen(files, selected, records):
    """Return the files to add to the selection, and the facts of the widening. ..."""
```

`files` is the `scan` list, `selected` the primary entries with their
`relations` already computed, `records` the plain record dicts (or `None`).
It returns `{'added': [entries], 'facts': {...}}`. It opens no file and reads
no ledger; codemap still imports nothing from `overseer`.

`assemble` changes order, and only this:

1. primary `select` exactly as now;
2. structure and excerpt of the primary files exactly as now, so their
   excerpts and the excerpt budget they spend are unchanged;
3. the one relation search over the primary paths exactly as now, and the
   primary relations;
4. `widen(files, detailed, memory)`;
5. structure and excerpt of each added file, from the **remaining** excerpt
   budget, and its relations from the **same** `references` index (no second
   search; the relation facts — candidate, searched, opened files, bytes read
   — are unchanged; `caller_count` and `test_count` now include the widened
   files' symbols, and the docstring says so);
6. `attach_memory` over all selected entries, primary and widened.

The three failure shapes of `assemble` are unchanged. `version` stays `1`.

### 2. What widens, and what never does

**By decision.** A record widens the selection only when `kind` is
`decision`, `status` is `current`, and `informs_decision` is `True`. It names a
file when its `affected_component` or `entry` contains that file's
workspace-relative path under `_path_pattern` (`overseer/codemap.py:579`). The
match is textual and is recorded as `how: 'textual'`. Only paths in the
`scan` list are candidates. A decision that names a symbol but no path does
not widen: the map cannot know the symbols of a file it has not read, and the
docstring says so.

Never widens: a superseded decision, any verified fact (current or
invalidated), a hypothesis, a historical attempt. The named increment is
decisions; facts stay out, and the reason is stated in the docstring and the
docs.

**By caller.** A file widens when it holds at least one caller of a **primary**
selected symbol, taken from the `callers` lists of the primary relations
(`overseer/codemap.py:510`). Test files never widen as callers (they are
already the `tests` relation). The caller relation is a static reference, so
the widened entry records the `how` values of its references (`parsed`,
`textual`).

**One round only.** Callers of a widened file's symbols and decisions naming a
widened file's symbols do not widen further.

**Never widened:** a file already selected, a secret-named file
(`is_secret`; it is not opened, and it is counted in the facts as left out
with the reason), a file absent from the scan.

### 3. Order and the bounds

Candidates are ranked deterministically:

1. decision candidates, in the order of the first record naming them (the
   recall order, most recent first), ties by path;
2. caller candidates, by the number of caller references descending, then by
   path.

A file that is both a decision and a caller candidate is one candidate, in the
decision tier, with both reasons.

Add module constants beside the others and record them in `limits`:

- `MAX_WIDENED_FILES = 4` — files the widening may add;
- `MAX_WIDEN_LEFT_OUT = 20` — left-out candidates listed.

Added files = the first `min(MAX_WIDENED_FILES, MAX_SELECTED - len(primary))`
candidates. The widening **never displaces** a primary file: when the primary
selection already holds 12 files, nothing is added and every candidate is left
out with the reason `the selection bound of 12 was reached by the task's own
selection`. A candidate past `MAX_WIDENED_FILES` is left out with the reason
`the widening bound of 4 was reached`.

### 4. The shape of the map

- Every selected entry gains `widened_by`: `None` for a primary file; for a
  widened file

```python
{'via': ['decision', 'caller'],          # the reasons that apply, in this order
 'record_ids': ['…'],                    # the decisions naming it, at most 5
 'symbols': ['build_filter'],            # the primary symbols it calls, at most 6, sorted
 'references': 3,                        # its caller references to primary symbols
 'how': ['parsed', 'textual'],           # sorted, distinct
 'reason': 'a current decision names this file by a textual path match; '
           'it holds 3 static references to selected symbols'}
```

  and `reason` (the selection reason) set to `'a current decision names this
  file'` or `'the file calls a selected symbol'` (decision wins when both), and
  `score` set to `0`.
- The map gains a top-level `selection` block:

```python
{'primary': 3, 'widened': 2, 'widened_by_decision': 1, 'widened_by_caller': 1,
 'candidates': 5, 'left_out': [{'path': '…', 'via': ['caller'], 'reason': '…'}],
 'left_out_count': 3, 'left_out_truncated': False,
 'secrets_left_out': 0,
 'reason': None}   # or the bound sentence when anything was left out
```

  `widened` equals the number of entries in `selected` whose `widened_by` is
  not `None`; `widened_by_decision + widened_by_caller` counts each widened file
  once, by its tier; `primary + widened == len(selected)`;
  `candidates == widened + left_out_count`.

### 5. How it reaches the attempt

- **Digest** (`summary`): a widened file's header line keeps its form and its
  reason reads `widened: a current decision 1a2b3c4d names this file` or
  `widened: calls build_filter (3 references)`. When `left_out_count` is
  nonzero, add one tail line `selection: N files widened, M candidates left
  out (<reason>)`, kept within the limit by the same tail-room logic the memory
  line uses; the digest never exceeds its limit.
- **Environment**: add `OVERSEER_CODEBASE_WIDENED`, the number of widened
  files. `OVERSEER_CODEBASE_SELECTED` keeps its meaning (all selected files).
- **Manifest**: each `codebase.selected` item gains `widened_by`; the
  `codebase` block gains `selection` (the block of section 4); the
  `relevant_code_and_interfaces` source string gains `, %d of the selected
  files widened from a current decision or a caller` and keeps every substring
  existing tests assert (`file tree`, `code excerpt`, `caller`,
  `test reference`, `recalled memory records`). The wording claims context
  supplied, not enforcement.
- `codebase.json` carries all of it.

### 6. What stays true

- A widened file is context, not a judgement: no verifier, gate, or state
  transition reads `widened_by` or `selection`.
- A not-usable record never widens. A secret file is never opened.
- Determinism: the same scan, primary selection, references, and records give
  the same `selection` and `widened_by`, byte for byte under
  `json.dumps(sort_keys=True)`; no set iteration decides an order.
- The existing selection rules (`select`) are unchanged.

### 7. Existing tests

Run the suite after the change before adding tests. An existing test may now
see an extra, widened file (for example the relation tests, where `app.py`
calls `build_filter` and the objective does not name `app`). If an existing
assertion fails **only** because of an intended widening, you may make it more
specific (assert the file is present with `widened_by['via'] == ['caller']`),
never looser, never deleted; list every such test, before and after, in the
WORK_LOG entry. Any other failure is a defect of the change.

### 8. The tests, and the mutations they must kill

Add tests to `class ContextTests`, after the memory tests. Use `command_spec`,
`manifest_of`, `codebase_of`, `write_source`, and the plain `record(...)`
helper.

1. **A caller file is widened.** `widget.py` defines `build_filter`;
   `app.py` (no term match) calls it; objective `repair the widget filter`.
   `app.py` is selected with `widened_by.via == ['caller']`, `symbols ==
   ['build_filter']`, `references == 1`, `how == ['parsed']`, score `0`; its
   own symbols have relations; `selection.widened == 1`.
2. **A test file is not widened as a caller.** `tests/test_widget.py` calls
   `build_filter`: it is not in `selected` and appears nowhere in
   `selection.left_out`.
3. **A current decision widens the file it names.** A current decision with
   `affected_component='pkg/store.py'` (no term match, no caller): `pkg/store.py`
   is selected with `via == ['decision']`, its record id, `how == ['textual']`,
   and the decision is attached to it as file memory.
4. **A not-usable record never widens.** A superseded decision, a current
   verified fact, an invalidated fact, a hypothesis, and a historical attempt,
   each naming a different unselected path: none of the paths is selected and
   none is a candidate.
5. **The widening never displaces and respects its bounds.** (a) 12
   term-matched files plus a caller file: the 12 are unchanged, nothing is
   widened, the caller is left out with the selection-bound reason. (b) 2
   primary files and 6 caller files: exactly 4 are widened, chosen by reference
   count then path, 2 are left out with the widening-bound reason, and
   `candidates == widened + left_out_count`.
6. **One round only.** `a.py` (primary) is called by `b.py`, which is called by
   `c.py`: `b.py` is widened, `c.py` is not selected and not a candidate.
7. **A secret is never widened.** A decision naming `config/secrets.json` and a
   secret-named file calling the symbol: neither is selected, neither file's
   content is in `codebase.json`, `selection.secrets_left_out` counts them.
8. **Path boundaries hold.** A decision naming `pkg/store.py.bak` or
   `xpkg/store.py` does not widen `pkg/store.py`.
9. **The attempt sees it.** `OVERSEER_CODEBASE_SUMMARY` carries
   `widened: calls build_filter`; `OVERSEER_CODEBASE_WIDENED` is `1`; the
   manifest's `codebase.selection` and the item's `widened_by` match the map;
   the supplied string names the widened count.
10. **Pure and deterministic.** `widen(...)` called directly with hand-built
    entries and plain dicts twice gives equal output; `assemble` twice gives
    equal `selection` and `selected`.
11. **The primary excerpts are unchanged.** With and without a caller file in
    the workspace, the primary file's `excerpt` and the primary excerpt bytes
    are identical.

Mutations to apply one at a time, each of which must make the suite fail
(report the failing test for each, then revert):

- M1 widening displaces the lowest-scored primary file instead of filling free
  slots;
- M2 any decision status widens (drop the `current`/`informs_decision` check);
- M3 a verified fact widens like a decision;
- M4 test files widen as callers;
- M5 widening is transitive (a second round over widened files);
- M6 `MAX_WIDENED_FILES` is ignored;
- M7 `widened` counts candidates instead of added files;
- M8 caller candidates are ordered by path only, or by set iteration;
- M9 widened files are processed before primary ones (excerpt budget);
- M10 path matched by substring instead of `_path_pattern`;
- M11 a secret-named file is admitted as a candidate;
- M12 widened files get no relations or no memory attachment.

### 9. The documentation

Re-derive every `path:line` after the last edit; the reference checker only
proves the line exists.

- `docs/HARNESS_FRAMEWORK.md:32` — add citations for `widen`, the changed
  `assemble` order, the selection digest line, `OVERSEER_CODEBASE_WIDENED`,
  and the manifest `selection`; re-derive every existing citation in the row
  and in any other row whose factory or codemap lines moved. Extend the
  verdict: the selection is widened one round, by a current decision's textual
  path match and by a caller's static reference, at most 4 files, never past
  12 and never displacing the task's own selection; a symbol named by a
  decision but no path does not widen; verified facts, superseded decisions,
  hypotheses, and historical attempts never widen; what the bounds left out is
  recorded. Keep "partial". Replace the "Next increment" cell with: **"read
  `factory/skills-provenance.json` into the context: validate it, and record in
  the manifest which skills were supplied to the attempt and why, or record
  that none was."**
- `docs/HARNESS_FRAMEWORK.md:41` — the process-order CONTEXT sentences gain
  the widening.
- `docs/HARNESS_FRAMEWORK.md:103` — the does-not-claim bullet: a widened file
  was selected by a static reference or a textual path match, not by proof
  that it is relevant.
- `README.md:57`–`99` — the codebase paragraph: the widening, its bounds, and
  `OVERSEER_CODEBASE_WIDENED`.
- `WORK_LOG.md` — a new `###` section after line 2336: what was asked, the
  commands and results, the new test count, the widening rules and bounds,
  the honest limits, any existing test made more specific (section 7), the
  mutation results (M1–M12, the failing test for each), and that every citation
  was re-derived. It records that the prompt was written by the dedicated
  prompt-writing agent and executed by the primary agent.

## Acceptance criteria (observable)

1. `python3 scripts/check` passes: 250 existing tests pass (none loosened or
   deleted; any made more specific is listed), new tests pass (expected at
   least 261). The new count is reported.
2. `python3 scripts/check-doc-references` reports every reference resolving,
   at least 138.
3. Each of M1–M12 makes the suite fail; the failing test is named for each in
   the WORK_LOG.
4. A caller file and a current-decision-named file are selected with
   `widened_by` stating `via`, `how`, and the evidence; test files, secret
   files, and files named only by not-usable records are not.
5. The task's own selection is never displaced; at most 4 files are widened;
   what is left out is in `selection.left_out` with its reason.
6. `primary + widened == len(selected)` and `candidates == widened +
   left_out_count` in every test that builds a map.
7. The digest, `OVERSEER_CODEBASE_WIDENED`, and the manifest carry the
   widening, and the digest stays within its limit.
8. `grep -n "^from overseer\|^import overseer" overseer/codemap.py` prints
   nothing.
9. The CONTEXT row, the process paragraph, the does-not-claim bullet,
   `README.md`, and `WORK_LOG.md` carry the increment, with citations checked
   by hand after the last edit.

## Constraints / compatibility contracts

- Python 3 standard library only. No new dependency.
- `select`, the relation search, the excerpt and relation bounds, the memory
  attachment rules, the recall, and the ledger schema are unchanged.
- No second relation search; the bytes and files the search reads are
  unchanged.
- Map and manifest stay `version` `1`; existing variable names keep their
  meanings.
- One primary editor: the primary agent edits. No other pillar row, no new
  objective, no change to the monitor, scheduler, model choice, policy,
  verifiers, or ledger.
- File this increment against exactly the CONTEXT row.
- Do not invent benchmark results, token counts, costs, or savings.

## Baseline check and known failures

Reported to the prompt-writing agent by the primary agent at the starting
commit (the writer did not rerun them):

- `python3 scripts/check` — **250 tests, OK**.
- `python3 scripts/check-doc-references` — **138 references resolve**.

No failure is known at the baseline.

## Verification commands

```text
python3 scripts/check
python3 scripts/check-doc-references
grep -n "^from overseer\|^import overseer" overseer/codemap.py
git diff --stat
```

## Allowed work and stopping condition

Allowed: `overseer/codemap.py`; `overseer/factory.py` (`_codebase_environment`
and `_context_manifest` only); `tests/test_factory.py` (new tests, and
existing assertions made more specific under section 7 only);
`docs/HARNESS_FRAMEWORK.md` (the CONTEXT row, the process-order CONTEXT
sentences, the context-manifest bullet, and citations in other rows that the
line moves broke); `README.md`; `WORK_LOG.md`.

Stop after this one increment: the selection is widened by current decisions
and callers within the bounds, never displacing the task's own selection, the
counts describe what is shown, the attempt sees the widening, M1–M12 each fail
the suite, the documentation is current with re-derived citations, and the
verification commands pass. Report the diff summary, the command outputs, the
new test and reference counts, the mutation results, and the limits that
remain. Do not start the next increment. If the same failure recurs twice with
no new evidence, stop and report it instead of retrying.
