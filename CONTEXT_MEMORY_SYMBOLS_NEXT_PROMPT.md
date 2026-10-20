# Attach the recalled memory records to the symbols they name

Status: **ready to execute**. This prompt was written by the dedicated
prompt-writing agent of the Overseer project. The primary agent executes it;
writing it is not completion.

Its file and line references describe the repository at the starting commit
below. The increment will move lines of `overseer/codemap.py`,
`overseer/factory.py`, and `tests/test_factory.py`. The lesson of the last
review holds: **line citations drift.** The references in this prompt are not
updated after the change; every citation in the documentation must be
re-derived by hand against the code after the last edit, not copied from here.

This prompt files exactly one increment against the **CONTEXT** row of the
harness pillar map (`docs/HARNESS_FRAMEWORK.md:32`). It does not plan work for
the CONTRACT, TOOLS, POLICY, STATE, PERMISSIONS, or EVIDENCE rows.

## Outcome

The codebase map that every attempt receives attaches each recalled memory
record to the selected symbol it names, so a decision or a verified fact about
`WidgetFilter.apply` appears under `WidgetFilter.apply` in the map, and not
only in the separate recall list. The attachment is a **textual match**, it
says so on every entry, it carries the record's status, and a superseded
decision or an invalidated fact is attached but marked not usable, never
presented as settled. It is bounded, deterministic, and it reaches the
attempt through the worker-facing summary and the context manifest, not only
the evidence file. A record that names no selected symbol stays in the recall
and is counted in the map as unattached, with the reason.

## Repository and starting commit

- Repository: `/home/kali/Programming/Projects/Overseer` (git root, branch
  `main`).
- Starting commit: `5134e6307dffa33ae5ccdb99b21c5fc66c0080f3`
  ("Relate the selected symbols to their callers and their tests").
- Working tree clean at the time of writing.
- Python 3 standard library only. No new dependency. The repository has no
  lockfile and installs nothing.

## Relevant paths and existing example

| Path and line | What it is now |
| --- | --- |
| `overseer/codemap.py:28` | the module-level bounds, `MAX_FILES` through `MAX_SUMMARY_SYMBOL_LINES` (line 50) |
| `overseer/codemap.py:60` | `IDENTIFIER`, the identifier pattern the map already uses |
| `overseer/codemap.py:222` | `_python_symbols(text)`: symbols are `{'name','kind','line','end'}`; a method's name is `Class.method`; a parse failure yields one symbol of kind `error` |
| `overseer/codemap.py:248` | `_declared_symbols(text)`: the declared symbols of a file that is not Python |
| `overseer/codemap.py:457` | `symbol_relations(entry, references, searched_files)`: one relation entry per symbol |
| `overseer/codemap.py:652` | `assemble(workspace, spec)`: builds `selected`, the top-level `relations` block, and the `limits` dict |
| `overseer/codemap.py:726` | `summary(context, limit=SUMMARY_LIMIT)`: the bounded worker digest |
| `overseer/codemap.py:768` | `_relation_line(relation, searched)`: one digest line per symbol |
| `overseer/factory.py:5` | the factory's imports of `assemble` and `summary` from `overseer.codemap` |
| `overseer/factory.py:817` | `record_memory`: free-text `entry`, `source`, `affected_component`, `invalidation_condition`, plus kind-specific fields |
| `overseer/factory.py:869` | `memory(job_id, kind)`: adds `superseded_by` and `current` to decisions |
| `overseer/factory.py:922` | `_record_status`: current / superseded / invalidated / unverified / historical |
| `overseer/factory.py:935` | `recall(spec)`: the recalled records, most recent first, each with `status` and `informs_decision`, and `not_usable` |
| `overseer/factory.py:998` | `_recall_summary`: the recall digest (unchanged by this increment) |
| `overseer/factory.py:1021` | `_codebase_environment`: the `OVERSEER_CODEBASE_*` variables |
| `overseer/factory.py:1033` | `_context_manifest`: the manifest writer |
| `overseer/factory.py:1078` | the `relevant_code_and_interfaces` entry of `supplied` |
| `overseer/factory.py:1097` | the `applicable_decisions` entry of `supplied` |
| `overseer/factory.py:1145` | the `codebase` block of the manifest; its `relations` sub-block at 1161 |
| `overseer/factory.py:1864` | the recall, computed **before** the map |
| `overseer/factory.py:1874` | `assemble_codebase(spec.get('workspace'), spec)`, the call this increment extends |
| `overseer/factory.py:1942` | the manifest call; `context.json` is written at 1945 |
| `tests/test_factory.py:1272` | `class ContextTests`; `setUp` at 1275 makes `self.root` the workspace |
| `tests/test_factory.py:1283` | `command_spec` (workspace is `self.root`) |
| `tests/test_factory.py:1330` | `manifest_of(result)` |
| `tests/test_factory.py:1612` | `recall_of(result)` |
| `tests/test_factory.py:1662` | the superseded-decision recall test, the example for a superseded record |
| `tests/test_factory.py:1677` | the invalidated-fact recall test, the example for a git workspace with an old revision |
| `tests/test_factory.py:1758` | the assertions on `applicable_decisions` (`current decision records`, `consulted`) that must keep passing |
| `tests/test_factory.py:1802` | `codebase_of(result)`; `write_source` at 1805 |
| `tests/test_factory.py:2251` | `test_the_attempt_sees_the_relation`, the example for an environment-carrying test |
| `tests/test_factory.py:2289` | `test_the_relation_is_deterministic` |
| `README.md:57` | the paragraph that describes the manifest, the recall, and the codebase context (to line 88) |
| `docs/HARNESS_FRAMEWORK.md:32` | the CONTEXT row of the pillar map |
| `docs/HARNESS_FRAMEWORK.md:41` | the process-order paragraph's CONTEXT sentences; its citation `overseer/codemap.py:649` at line 47 has **already drifted** (`assemble` is at 652; 649 is `return chosen[:MAX_SELECTED]`) |
| `docs/HARNESS_FRAMEWORK.md:102` | the context-manifest bullet under "What this framework does not claim" |
| `WORK_LOG.md:2182` | the last entry (the review correction); the new entry goes after the end of the file, line 2225 |

Existing example to follow: `symbol_relations` and its digest line in
`overseer/codemap.py` — module-level constants for every bound, small pure
functions whose docstrings state the reason, dictionary results, a `reason`
field wherever something could not be done, and the honesty about what a
match is (`how`).

## Required behavior

### 1. Where the attachment lives: codemap stays free of the ledger

Add one pure function to `overseer/codemap.py`:

```python
def attach_memory(selected, records):
    """Attach recalled memory records to the selected symbols they name. ..."""
```

It takes the `selected` list that `assemble` built and a list of **plain
record dicts**, and it returns the top-level `memory` block (section 5) after
adding a `memory` list to each relation entry and to each selected file entry.
It reads only these keys of a record: `record_id`, `kind`, `status`,
`informs_decision`, `entry`, `affected_component`, `superseded_by`. A missing
key is treated as absent, not as an error. It imports nothing from
`overseer.factory`, opens no file, and touches no database.

Extend `assemble(workspace, spec)` to `assemble(workspace, spec, memory=None)`.
When `memory` is `None` the map is exactly as it is now plus a `memory` block
that says no record was supplied. When `memory` is a list, `assemble` calls
`attach_memory` after the relation search. The three failure shapes of
`assemble` (no workspace, no readable directory, no readable file) stay as
they are; they gain nothing.

In `overseer/factory.py` at the call at line 1874, pass the recall:
`assemble_codebase(spec.get('workspace'), spec, memory=recalled['records'])`.
The recall itself, `recall.json`, `_recall_summary`, and the
`OVERSEER_RECALL_*` variables do not change: the recall stays the complete
list, the map adds the attachment.

### 2. How a record is judged to name a symbol

The match is **textual** and is stated as textual on every attachment. It
does not prove that the record is about the symbol.

- The candidate names of a symbol are its `name` exactly as the map records it
  (`build_filter`, `WidgetFilter`, `WidgetFilter.apply`). Symbols of kind
  `error` are never matched. Names shorter than 3 characters are never
  matched.
- A name matches a text when it occurs on **identifier boundaries**: the
  character before is not `[A-Za-z0-9_]` and the character after is not
  `[A-Za-z0-9_]`. Build the pattern with `re.escape(name)` and lookarounds
  `(?<![A-Za-z0-9_])` and `(?![A-Za-z0-9_])`. So `build_filter` does not match
  `build_filter_v2` and `apply` does not match `apply_filter`. The match is
  case-sensitive.
- **The most specific name wins.** When a text matches `WidgetFilter.apply`,
  the record attaches to the method and not, for that occurrence, to the class
  `WidgetFilter`. A class is attached only when its name occurs in the text
  without being immediately followed by `.` and the name of one of its
  methods that is a selected symbol.
- Two fields are searched, in this order, and the attachment records which
  one matched (`field`):
  - `affected_component` — every eligible name is matched here.
  - `entry` — only **identifier-shaped** names are matched here: a name that
    contains `_` or `.`, or has an uppercase letter after its first character.
    A plain lowercase word such as `build` or `run` is matched in
    `affected_component` only, because in free text it is far more often an
    English word than a symbol. The docstring states this rule and its reason.
- When both fields match, the attachment records `affected_component`.
- A record may name several symbols; it is attached to every one it names
  (within the bounds of section 4) and counted once as attached.
- **File path match.** When a record's `affected_component` or `entry`
  contains the workspace-relative POSIX path of a selected file on path
  boundaries (the character before is not `[A-Za-z0-9_./-]`, the character
  after is not `[A-Za-z0-9_/-]`; a trailing `.` or `,` of a sentence is not part
  of the path) and names **no symbol of that file**, the record is attached to
  the file entry's own `memory` list with `matched` set to the path. A record
  that names a symbol of the file is attached to the symbol, not also to the
  file.

### 3. Which statuses attach and how they are shown

Every status attaches: `current`, `superseded`, `invalidated`, `unverified`,
`historical`. Hiding a superseded decision would hide that it was overturned;
showing it as settled would be false. Each attachment carries `usable`, which
is `True` only when the record's `informs_decision` is `True` (a current
decision or a current verified fact) and `False` otherwise. The attachment
shape is:

```python
{'record_id': '…', 'kind': 'decision', 'status': 'superseded', 'usable': False,
 'superseded_by': '…',            # decisions only, else None
 'matched': 'WidgetFilter.apply', 'field': 'affected_component', 'how': 'textual',
 'entry': 'keep the old behaviour',   # whitespace-collapsed, at most MAX_MEMORY_ENTRY_CHARS
 'reason': 'the record names the symbol by its text; a textual match does not '
           'prove the record is about this symbol; the decision was superseded '
           'and is not usable'}
```

The `reason` always carries the textual-match sentence, and, for a record that
is not usable, a clause naming why: superseded (and by which record),
invalidated (its bound revision is not the workspace's base commit),
unverified (a hypothesis), or historical (a past attempt, a result and not
current state).

Order within one symbol's list, deterministic: usable records first, then the
rest; inside each group, the recall's order (most recent first); ties broken by
`record_id`. A usable record is never crowded out by a not-usable one, and a
not-usable one is still shown while there is room.

### 4. The bounds

Add module-level constants beside the existing ones at
`overseer/codemap.py:28`, and record every one in the map's `limits` dict:

- `MAX_MEMORY_RECORDS_PER_SYMBOL = 5` — attachments kept per symbol;
- `MAX_MEMORY_RECORDS_PER_FILE = 5` — file-level attachments kept per file;
- `MAX_MEMORY_ENTRY_CHARS = 160` — the characters of a record's entry kept in
  an attachment;
- `MAX_UNATTACHED_MEMORY_RECORDS = 32` — the unattached records listed (the
  recall's own limit is 32);
- `MAX_SUMMARY_MEMORY_LINES = 6` — the memory lines one file contributes to
  the digest.

When a cap drops an attachment, the symbol's (or file's) relation entry
records `memory_dropped` with the count, and its reason says the cap was
reached. The existing excerpt and relation bounds are **not** changed.

### 5. The shape of the map

- Each relation entry (`selected[i]['relations'][j]`) gains `memory` (a list
  of attachments, empty when none) and `memory_dropped` (an integer, `0` when
  none).
- Each selected file entry gains `memory` and `memory_dropped` for the
  file-level attachments.
- The map gains a top-level `memory` block:

```python
{'supplied': 7, 'attached': 4, 'attached_to_symbols': 3, 'attached_to_files': 1,
 'attachments': 5, 'not_usable_attached': 2,
 'unattached': [{'record_id': '…', 'kind': 'hypothesis', 'status': 'unverified',
                 'reason': 'the record names no selected symbol and no selected file'}],
 'unattached_count': 3, 'unattached_truncated': False,
 'how': 'textual',
 'reason': None}   # or 'no memory record was supplied' when memory is None or empty
```

A record is counted in `attached` once however many symbols it names. The
map's `version` stays `1`, and the manifest's `version` stays `1`
(`tests/test_factory.py:1348`).

### 6. How it reaches the attempt

- **Digest** (`summary`, `overseer/codemap.py:726`): under each symbol's
  relation line, add one line per attachment, indented four spaces, of the form
  `    memory decision/current 1a2b3c4d: keep the filter semantics (textual match on affected_component)`
  and, for a record that is not usable,
  `    memory decision/superseded 5e6f7a8b NOT USABLE (superseded): keep the old behaviour (textual match on affected_component)`.
  The id shown is the first 8 characters of `record_id`. File-level
  attachments are printed under the file's header line in the same form,
  prefixed `  file memory`. At most `MAX_SUMMARY_MEMORY_LINES` memory lines
  per file; when more exist, print `  (N more memory records of this file are
  not shown)`. The existing truncation marker and the dropped-files note stay
  as they are. When the map's `memory.unattached_count` is nonzero, end the
  digest (before any truncation marker) with one line
  `memory: N recalled records name no selected symbol; see OVERSEER_RECALL_SUMMARY`.
- **Environment** (`_codebase_environment`, `overseer/factory.py:1021`): the
  existing variables keep their names and meanings. Add
  `OVERSEER_CODEBASE_MEMORY`, the number of attached records.
- **Manifest** (`_context_manifest`):
  - the `codebase` block gains a `memory` sub-block with the counts of
    section 5, the unattached list, and per-symbol entries
    `{'path', 'symbol', 'record_ids', 'not_usable'}` plus per-file entries
    `{'path', 'record_ids', 'not_usable'}`;
  - the `relevant_code_and_interfaces` source string gains
    `, and %d recalled memory records attached by a textual match to the symbols or files they name`.
    It must keep the substrings `file tree`, `code excerpt`, `caller`, and
    `test reference`, which existing tests assert;
  - the `applicable_decisions` source string, when there are current
    decisions, gains `, %d of them attached to a selected symbol or file by a textual match`.
    It must keep `current decision records`, and the `why` must keep
    `consulted` (`tests/test_factory.py:1758`). The wording must not claim
    that an attached decision was followed or enforced: it was supplied.
- `codebase.json` carries the whole attachment, as it already carries the map.

### 7. What stays true and what stays forbidden

- The attachment changes what an attempt is informed by, not what it is
  judged by. No verifier, gate, or state transition reads it.
- A not-usable record is never presented as usable: not in the map, not in
  the digest, not in the manifest.
- The map still never opens a secret-named file, never writes to, executes,
  or imports workspace code. The attachment reads no file at all.
- Determinism: the same `selected` list and the same record list yield the
  same attachment, byte for byte in `json.dumps(..., sort_keys=True)`.
- `record_memory`'s docstring (`overseer/factory.py:817`) says "Nothing reads
  them to change a decision" and `memory`'s says "Nothing consumes them".
  The first remains true; the second has been false since the recall
  increment. Correct the second to say that the recall reads them and the map
  attaches them, and touch nothing else in those functions.

### 8. The tests that prove the behavior

Add tests to `class ContextTests` in `tests/test_factory.py`, after the
relation tests (`tests/test_factory.py:2289` onward). Use the existing helpers
`command_spec`, `manifest_of`, `recall_of`, `codebase_of`, and `write_source`.
A record must be recorded after `submit` and before `run_one`, as the recall
tests do. Each test must fail if the attachment were removed.

1. **A current decision attaches to the method it names.** `widget.py` with
   `class WidgetFilter` and method `apply`; objective that selects it; a
   decision with `affected_component='WidgetFilter.apply'`. The relation entry
   of `WidgetFilter.apply` carries the record id with `status` `current`,
   `usable` `True`, `how` `textual`, `field` `affected_component`; the entry of
   `WidgetFilter` does not carry it.
2. **A superseded decision is attached and marked not usable.** Two decisions
   on `WidgetFilter.apply`, the second superseding the first. Both attach to
   the symbol; the first has `status` `superseded`, `usable` `False`, its
   `superseded_by` is the second's id, and its reason says it was superseded;
   the second is `current` and listed first. The digest written by the worker
   (environment test pattern of `tests/test_factory.py:2251`) contains
   `NOT USABLE (superseded)` on the first record's line, and the manifest's
   per-symbol `not_usable` contains the first id.
3. **An invalidated fact is attached and marked not usable.** A git workspace
   as in `tests/test_factory.py:1677`, with a committed `widget.py` defining
   `build_filter`; a verified fact with `revision='oldcommit'` whose `entry`
   names `build_filter` and whose `affected_component` does not. It attaches
   to `build_filter` with `field` `entry`, `status` `invalidated`, `usable`
   `False`, and a reason that names the revision.
4. **A record naming no symbol stays unattached, with the reason.** A
   hypothesis whose fields name nothing selected: it is in `recall.json`, it
   is in the map's `memory.unattached` with the reason, `unattached_count` is
   1, no relation entry carries it, and the digest has the `memory: 1 recalled
   records name no selected symbol` line.
5. **The match is on identifier boundaries and the entry rule holds.** With
   symbols `build` and `build_filter`: a record whose `affected_component` is
   `build_filter_v2` attaches to neither; a record whose `entry` says
   `run the build again` and whose component names nothing attaches to
   neither; a record whose `affected_component` is `build` attaches to
   `build` and not to `build_filter`.
6. **A file path match attaches to the file.** A record whose
   `affected_component` is `pkg/widget.py` and names no symbol attaches to
   that file entry's `memory` with `matched` `pkg/widget.py`, and not to any
   symbol.
7. **The bounds hold.** Eight decisions naming the same symbol: at most
   `limits.max_memory_records_per_symbol` attach, `memory_dropped` is the
   rest, and every limit of section 4 is present in `limits`. The digest has
   at most `MAX_SUMMARY_MEMORY_LINES` memory lines for that file and the
   `more memory records` line.
8. **The attachment is pure and deterministic.** Call
   `overseer.codemap.assemble(str(self.root), spec, memory=records)` directly
   with hand-built plain dicts (no factory, no ledger) twice: the two results'
   `memory` blocks and relation entries are equal under
   `json.dumps(sort_keys=True)`, and `assemble(..., memory=None)` yields a
   `memory` block whose reason says no record was supplied.

Do not weaken, delete, or rewrite any existing test. All 234 existing tests
must keep passing unchanged.

### 9. The documentation

Re-derive **every** `path:line` you write or keep after the last code edit.
`scripts/check-doc-references` only proves that the path exists and the line
is inside the file; it does not prove that the line still makes the claim.
The last review found eleven drifted citations; do not repeat it.

- `docs/HARNESS_FRAMEWORK.md:32` — the CONTEXT row. Add citations for
  `attach_memory`, the memory digest lines, the changed `assemble_codebase`
  call, the manifest `memory` sub-block, and `OVERSEER_CODEBASE_MEMORY`;
  re-derive every existing citation in the row (the factory citations will
  move). Extend the verdict: the recalled records are attached to the selected
  symbols and files they name by a textual, identifier-boundary match, which
  does not prove a record is about the symbol; every status attaches and a
  superseded, invalidated, unverified, or historical record is marked not
  usable; the bounds (5 per symbol, 5 per file, 160 characters of entry, 32
  unattached listed, 6 digest lines per file); a record naming nothing
  selected is counted as unattached. Keep "partial". Replace the "Next
  increment" cell with: **"widen the selection with the relation and the
  memory: select a file that a current decision or a caller of a selected
  symbol names even when the task terms do not match it, within the existing
  selection bound."**
- `docs/HARNESS_FRAMEWORK.md:41`–`47` — the process-order CONTEXT sentences:
  add that the recalled records are attached to the symbols they name, and
  fix the drifted `overseer/codemap.py:649` citation.
- `docs/HARNESS_FRAMEWORK.md:102` — the does-not-claim bullet: add that a
  record is attached to a symbol by a textual match of its name, which does
  not prove the record is about that symbol, and that an attached decision is
  supplied, not enforced.
- `README.md:57`–`88` — extend the codebase-context paragraph: the map attaches
  the recalled records to the symbols they name, textually, with their status,
  marks the unusable ones, and its bounds; name `OVERSEER_CODEBASE_MEMORY`.
- `WORK_LOG.md` — a new `###` section after the last line (2225), in the voice
  of the entries around it: what was asked, the two commands and their
  results, the new test count, what the map now attaches and how the match is
  made, the bounds, the honest limits, and that every citation was re-derived.
  It must record that the prompt was written by the dedicated prompt-writing
  agent and executed by the primary agent.

## Acceptance criteria (observable)

1. `python3 scripts/check` passes: the 234 existing tests pass unchanged and
   the new tests pass (expected at least 242). The new count is reported.
2. `python3 scripts/check-doc-references` reports every reference resolving,
   with at least 134 references.
3. A current decision naming `WidgetFilter.apply` appears in that symbol's
   relation entry in `codebase.json` with `how` `textual`, `usable` `True`,
   and not under `WidgetFilter`.
4. A superseded decision and an invalidated fact are attached to the symbols
   they name with `usable` `False` and a reason that names the status; the
   worker digest prints `NOT USABLE` on their lines; the manifest lists them in
   `not_usable`.
5. A record naming no selected symbol or file is in `recall.json`, in the map's
   `memory.unattached` with a reason, and counted in `unattached_count`.
6. `build_filter_v2` does not match `build_filter`; a lowercase word in an
   entry does not match a symbol.
7. Every bound of section 4 is in `limits` and holds in a test built to exceed
   it.
8. `attach_memory` and `assemble(..., memory=...)` work on plain dicts with no
   factory, and twice give identical output.
9. `OVERSEER_CODEBASE_SUMMARY` carries the memory lines; `OVERSEER_CODEBASE_MEMORY`
   carries the attached count; the manifest's `codebase.memory` carries the
   counts and the per-symbol record ids; the supplied strings keep their
   asserted substrings and claim no enforcement.
10. `grep -n "^from overseer\|^import overseer" overseer/codemap.py` prints
    nothing (codemap stays free of the factory).
11. The CONTEXT row, the process paragraph, the does-not-claim bullet,
    `README.md`, and `WORK_LOG.md` carry the increment, and every citation in
    the CONTEXT row and in the two other passages was checked by hand against
    the code after the last edit.

## Constraints / compatibility contracts

- Python 3 standard library only. No new dependency. Nothing is installed.
- `overseer/codemap.py` does not import the factory and reads no ledger; the
  records arrive as plain dicts.
- The recall, its file, its digest, its variables, and the ledger schema are
  unchanged.
- The map and the manifest keep `version` `1`; the failure shapes of
  `assemble` are unchanged; the existing variable names keep their meanings.
- The excerpt and relation bounds are unchanged.
- Existing tests are not weakened, deleted, or rewritten.
- One primary editor: the primary agent edits. This prompt does not authorize
  work on another pillar row, a new objective, a change to the monitor, the
  scheduler, the model choice, the policy, the verifiers, or the ledger
  schema.
- File this increment against exactly the CONTEXT row.
- Do not invent benchmark results, token counts, costs, or savings. The token
  and cost fields stay null.

## Baseline check and known failures

Reported to the prompt-writing agent by the primary agent at the starting
commit (the writer did not rerun them):

- `python3 scripts/check` — **234 tests, OK**.
- `python3 scripts/check-doc-references` — **134 references resolve**.

Known drift at the baseline: `docs/HARNESS_FRAMEWORK.md:47` cites
`overseer/codemap.py:649`, which is no longer the line of `assemble` (652).
Fix it as part of section 9. No test failure is known.

## Verification commands

```text
python3 scripts/check
python3 scripts/check-doc-references
grep -n "^from overseer\|^import overseer" overseer/codemap.py
git diff --stat
```

The first two must pass; the grep must print nothing. Report the new test
count and the new reference count.

## Allowed work and stopping condition

Allowed: `overseer/codemap.py`; `overseer/factory.py` (the
`assemble_codebase` call, `_codebase_environment`, `_context_manifest`, and the
`memory` docstring only); `tests/test_factory.py` (new tests only);
`docs/HARNESS_FRAMEWORK.md` (the CONTEXT row, the process-order CONTEXT
sentences, and the context-manifest does-not-claim bullet); `README.md`;
`WORK_LOG.md`.

Stop after this one increment: the recalled records are attached to the
symbols and files they name, the statuses are honest, the bounds hold, the
attempt sees the attachment, the documentation is current with re-derived
citations, and the verification commands pass. Report the diff summary, the
command outputs, the new test count, the new reference count, and the limits
that remain. Do not start the next increment, do not widen the selection, do
not refactor the existing map, and do not touch another pillar row. If the
same failure recurs twice with no new evidence, stop and report it instead of
retrying.
