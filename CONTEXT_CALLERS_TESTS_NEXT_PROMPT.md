# Relate the selected symbols to their callers and their tests

Status: **ready to execute**. This prompt was written by the dedicated
prompt-writing agent of the Overseer project. The primary agent executes it;
writing it is not completion.

Its file and line references describe the repository at the starting commit
below. The increment moved the lines of `overseer/codemap.py` and
`overseer/factory.py`; the references were kept as they were written, and the
pillar map carries the citations that hold after the change.

This prompt files exactly one increment against the **CONTEXT** row of the
harness pillar map (`docs/HARNESS_FRAMEWORK.md:32`). It does not plan work for
the CONTRACT, TOOLS, POLICY, STATE, PERMISSIONS, or EVIDENCE rows.

## Outcome

The codebase map that every attempt receives relates each selected symbol to
the code that calls it and to the test files that cover it. The relation is
bounded, deterministic, evidence-shaped, and it reaches the attempt — through
the worker-facing summary and the context manifest — not only the evidence
file.

## Repository and starting commit

- Repository: `/home/kali/Programming/Projects/Overseer` (git root, branch
  `main`).
- Starting commit: `024fd30f443fdf156f6d5100fd76889d451cac2d`
  ("Never read a secret named file for the codebase context").
- Working tree clean at the time of writing.
- Python 3 standard library only. No new dependency. The repository has no
  lockfile and installs nothing.

## Relevant paths and existing example

| Path and line | What it is now |
| --- | --- |
| `overseer/codemap.py:87` | `scan(workspace)`: the bounded file tree walk, no content read |
| `overseer/codemap.py:115` | `structure(path)`: the structural symbols of one file |
| `overseer/codemap.py:138` | `is_secret(path)`: the name rule that keeps a secret file unopened |
| `overseer/codemap.py:148` | `excerpt(path, symbols, budget)`: the bounded excerpt of a symbol's code |
| `overseer/codemap.py:208` | `_python_symbols(text)`: the `ast` parse that yields a Python file's symbols |
| `overseer/codemap.py:233` | `_declared_symbols(text)`: the declared forms for a file that is not Python |
| `overseer/codemap.py:317` | `select(files, terms, named, root)`: the selection of at most 12 files |
| `overseer/codemap.py:347` | `assemble(workspace, spec)`: the map, and the `limits` dict it records |
| `overseer/codemap.py:399` | `summary(context, limit=4000)`: the bounded digest the worker receives |
| `overseer/codemap.py:26` | the module-level bounds, `MAX_FILES` through `MAX_EXCERPT_TOTAL_BYTES` |
| `overseer/factory.py:5` | the factory's imports of `assemble` and `summary` from `overseer.codemap` |
| `overseer/factory.py:1021` | `_codebase_environment`: the four `OVERSEER_CODEBASE_*` variables |
| `overseer/factory.py:1030` | `_context_manifest`: the manifest writer |
| `overseer/factory.py:1072` | the `relevant_code_and_interfaces` entry of `supplied` |
| `overseer/factory.py:1137` | the `codebase` block of the manifest |
| `overseer/factory.py:1842` | the call that assembles the map before the attempt runs |
| `overseer/factory.py:1843` | the write of `codebase.json` into the run evidence directory |
| `overseer/factory.py:1853` | the `codebase` event of the attempt |
| `overseer/factory.py:1910` | the write of `context.json` into the run evidence directory |
| `tests/test_factory.py:1270` | `class ContextTests`, where the codebase tests live |
| `tests/test_factory.py:1800` | `codebase_of(result)`, the helper that reads `codebase.json` |
| `tests/test_factory.py:1809` | the test that the manifest populates `relevant_code_and_interfaces` |
| `tests/test_factory.py:1924` | the test that the worker receives the codebase context in its environment |
| `tests/test_factory.py:1946` | the test that the context carries no file content |
| `tests/test_factory.py:2016` | the test that a secret named file is never excerpted |
| `tests/test_factory.py:2048` | the test that the worker can read the excerpt from the map |
| `README.md:67` | the paragraph that describes the codebase context to a reader |
| `docs/HARNESS_FRAMEWORK.md:32` | the CONTEXT row of the pillar map |
| `docs/HARNESS_FRAMEWORK.md:40` | the process-order paragraph, whose CONTEXT sentences are now false |
| `docs/HARNESS_FRAMEWORK.md:99` | the bullet under "What this framework does not claim" that is now false |
| `WORK_LOG.md:2024` | the last increment's entry, whose voice the new entry follows |

Existing example to follow: `overseer/codemap.py` is the model for this
increment — module-level constants for the bounds, small functions whose
docstrings state the reason, dictionaries as results, and a `reason` field
wherever something could not be done.

## Required behavior

### 1. What a relation is

A relation is a **static reference**, not a proven call. Say so in the code,
in the map, and in the documentation. The map relates a selected symbol to:

- its **callers**: the places in the workspace that reference it outside a
  test file, each with the file path and the line; and
- its **tests**: the places in test files that reference it, each with the
  file path and the line.

Every relation entry carries:

- `file` — the workspace-relative POSIX path of the referencing file;
- `line` — the line of the reference;
- `kind` — one of `call` (the reference is the callee of a call), `attribute`
  (an attribute reference), `name` (a bare identifier reference), `mention`
  (a textual match in a language the map does not parse);
- `how` — `parsed` (Python, through the standard library `ast` parser) or
  `textual` (every other language).

For a method, the `attribute` kind is a reference to an attribute of that
name; the map cannot resolve the object it belongs to, and the entry's reason
must say so. For a `textual` entry the reason must say that the match is a
mention and may be a comment, a string, or an unrelated identifier.

Every symbol of every selected file gets a relation entry, including the
symbols nothing references. A symbol with no caller is recorded with an empty
`callers` list and a reason that names the number of searched files, for
example: "no reference to the symbol was found in the 137 searched files".
Absence is a fact, not a gap.

### 2. How a caller is found

The search corpus is built from the file tree that `scan` already returns, and
it is ordered deterministically:

1. the selected files, in selection order;
2. the remaining workspace files that match the test convention of section 3,
   sorted by path;
3. the remaining workspace source files, sorted by path.

The corpus is capped (section 4). When the cap truncates it, the map records
the number of candidate files, the number of files actually searched, and that
the relation outside the searched set is not represented.

**Python files are parsed, not grepped.** Use `ast`, the same parser the map
already uses at `overseer/codemap.py:208`:

- a module-level symbol (`function` or `class`) is referenced by an
  `ast.Name` node whose `id` equals the symbol name and whose context is a
  load; when that node is the `func` of an `ast.Call`, the kind is `call`,
  otherwise `name`;
- a method symbol `Class.method` is referenced by an `ast.Attribute` node
  whose `attr` equals the method's bare name; when that node is the `func`
  of an `ast.Call`, the kind is `call`, otherwise `attribute`;
- a reference that lies inside the symbol's own definition line range is not a
  caller: it is the definition. Exclude it, and say in the docstring that the
  definition range is excluded.

A Python file whose parse fails falls back to the textual method, and the
fallback is recorded in the entry's reason rather than hidden.

**Other languages are matched textually.** The identifier is matched with word
boundaries, so `apply` does not match `apply_filter`. For a method the
qualified name `Class.method` is matched. A line whose first non-space
characters are a comment marker (`#`, `//`, `--`, `/*`, `*`) is skipped. The
kind is `mention` and `how` is `textual`; the map must not present a textual
match as a call.

### 3. How a test is identified, and tied to a symbol

A file is a test file when its workspace-relative POSIX path matches any of
these conventions:

- a path component is named `test` or `tests`;
- the basename starts with `test_`;
- the basename ends with `_test`;
- the basename ends with `Test`;
- the basename contains `.test.` or `.spec.`.

The same convention decides whether a reference is a `test` relation or a
`caller` relation: a reference in a test file is a test, any other reference
is a caller.

A test file is tied to a symbol when it **references that symbol** under the
rules of section 2. The relation records the file and the line of that
reference. A symbol that no test file references is recorded with an empty
`tests` list and the reason that no test file references it.

The map also records the **inventory of test files in the workspace**, taken
from the file tree alone (path convention only, no content read), so a reader
can see how many test files exist even when the search did not reach them.

### 4. The bounds

Add module-level constants to `overseer/codemap.py`, beside the existing ones
at `overseer/codemap.py:26`, and record every one of them in the map's
`limits` dict, as `assemble` already does:

- `MAX_REFERENCE_FILES = 400` — the files that may be opened for the relation
  search;
- `MAX_REFERENCE_BYTES = 2 * 1024 * 1024` — the total bytes that may be read
  for the relation search;
- `MAX_CALLERS_PER_SYMBOL = 20` — the callers recorded per symbol;
- `MAX_TESTS_PER_SYMBOL = 10` — the tests recorded per symbol;
- `MAX_SKIPPED_REFERENCE_FILES = 20` — the skipped-file records kept.

The existing excerpt bounds are **not** changed: 8 KiB and 60 lines and 12
ranges per file, 32 KiB for the whole attempt
(`overseer/codemap.py:35`). The relation search has its own byte budget, it
is counted separately, and the map records the bytes it read. The relation
adds no file content to the map: it adds paths and line numbers only.

### 5. The shape of the map

`codebase.json` gains, per selected file, a `relations` list — one entry per
symbol of that file:

```python
{'symbol': 'WidgetFilter.apply',
 'callers': [{'file': 'pkg/app.py', 'line': 42, 'kind': 'call', 'how': 'parsed'}],
 'tests': [{'file': 'tests/test_widget.py', 'line': 17, 'kind': 'call', 'how': 'parsed'}],
 'reason': None}
```

and the map gains a top-level `relations` block with the facts of the search:
the candidate file count, the searched file count, whether the corpus was
truncated, the bytes read, the caller count, the test count, the inventory of
test files, the number of secret-named files that were kept unopened, and a
bounded list of the files that were skipped with the reason each was skipped.

The failure shapes of `assemble` (no workspace, no readable directory, no
readable file) stay as they are and keep their `reason`. The map's `version`
stays `1`: the shape is extended, not replaced. The manifest's `version` also
stays `1` — it is asserted at `tests/test_factory.py:1346`.

### 6. The manifest and the worker-facing summary

The attempt must see the relation, not only the evidence file.

- `overseer/codemap.py:399` (`summary`): the digest gains the relation. Keep
  the existing one-line-per-file entry, and add, per selected file, at most
  six symbol lines of the form
  `WidgetFilter.apply <- caller pkg/app.py:42 (call, parsed), test tests/test_widget.py:17 (call, parsed)`
  and
  `build_filter <- no caller and no test found in the 137 searched files`.
  When a file has more symbols than those six lines, print how many symbols
  are not shown. When the digest is truncated, keep the existing truncation
  marker and state how many files' relations were dropped.
- `overseer/factory.py:1072`: the `source` string of the
  `relevant_code_and_interfaces` entry names the relation counts. It must
  keep the substrings `file tree` and `code excerpt`, which the existing tests
  assert (`tests/test_factory.py:1817`, `tests/test_factory.py:2046`).
- `overseer/factory.py:1137`: the `codebase` block of the manifest gains a
  `relations` sub-block with the counts and the per-symbol relation entries
  (path, symbol, caller paths with lines, test paths with lines, reason).
- `overseer/factory.py:1021`: the environment keeps its four variables. The
  relation travels in `OVERSEER_CODEBASE_SUMMARY`, which is built from
  `summary`. An extra count variable is allowed but not required.

### 7. What stays forbidden

- A file whose name marks it as a secret is **never opened** — not for its
  structure, not for its excerpt, and not for the relation search. A secret
  file contributes no caller and no test, and its content is absent from the
  map.
- A file that is binary, too large, or not text is left alone, and the reason
  is recorded.
- The map never writes to, executes, or imports workspace code. The relation
  search reads bytes and nothing else.
- The map carries no file content beyond the existing bounded excerpt
  discipline.
- The relation changes what an attempt is informed by, not what it is judged
  by.

### 8. The tests that prove the behavior

Add tests to `class ContextTests` in `tests/test_factory.py` (from
`tests/test_factory.py:1270`), beside the existing codebase tests. Use the
existing helpers: `command_spec` (`tests/test_factory.py:1281`), `manifest_of`
(`tests/test_factory.py:1328`), `codebase_of` (`tests/test_factory.py:1800`),
and `write_source` (`tests/test_factory.py:1803`).

1. **A caller is found and related.** A workspace with `pkg/widget.py`
   defining `WidgetFilter.apply` and `pkg/app.py` calling it: the relation
   entry of `WidgetFilter.apply` names `pkg/app.py` and the line of the call,
   with the kind `call` and the way `parsed`.
2. **A test file is identified and related.** A workspace with
   `tests/test_widget.py` calling the same symbol: the symbol's `tests` list
   names that file and its line, and the map's test inventory lists the file.
3. **"No caller found" is recorded as a fact.** A symbol nothing references:
   the relation entry exists, its `callers` list is empty, and its reason says
   that no reference was found and how many files were searched.
4. **The bounds hold.** The searched file count is at most
   `limits.max_reference_files`; the bytes read for the relation are at most
   `limits.max_reference_bytes`; the callers of a symbol are at most
   `limits.max_callers_per_symbol`; the tests of a symbol are at most
   `limits.max_tests_per_symbol`; and the excerpt bounds are unchanged
   (`limits.max_excerpt_bytes` is 8192, `limits.max_excerpt_lines` is 60,
   `limits.max_excerpt_total_bytes` is 32768).
5. **A secret named file is still never opened.** A secret-named file that
   references the symbol: the symbol has no caller from that file, the
   secret's content is absent from `codebase.json`, and the map records that
   secret-named files were kept out of the relation search.
6. **The attempt sees the relation.** `OVERSEER_CODEBASE_SUMMARY` names the
   caller file and the test file; the manifest's
   `relevant_code_and_interfaces` source string names the caller and test
   counts; `manifest['codebase']['relations']` carries the counts and the
   per-symbol entries.
7. **The relation is deterministic.** Assembling the map twice over the same
   workspace yields the same relation.
8. **A binary, too large, or not text file is still left alone.** It
   contributes no relation and is recorded with its reason.

Do not weaken, delete, or rewrite any existing test. The existing excerpt
tests (`tests/test_factory.py:1974`, `tests/test_factory.py:1990`,
`tests/test_factory.py:2003`, `tests/test_factory.py:2016`,
`tests/test_factory.py:2033`, `tests/test_factory.py:2048`) must keep
passing unchanged.

### 9. The documentation

- `docs/HARNESS_FRAMEWORK.md:32` — the CONTEXT row. Update the "Current
  implementation (file:line)" cell with the new functions of
  `overseer/codemap.py` and the changed lines of `overseer/factory.py`; keep
  the existing citations that still hold. Update the verdict to state what
  the map now relates and to state the limit honestly: these are static
  references, parsed for Python and textual elsewhere, bounded by an explicit
  cap, and a truncated corpus is recorded. Replace the "Next increment" cell
  with: **"relate the recalled memory records to the symbols they name, so a
  decision or a verified fact about a symbol is attached to that symbol in
  the map instead of listed beside it."** Do not leave the cell stale.
- `docs/HARNESS_FRAMEWORK.md:40` and `docs/HARNESS_FRAMEWORK.md:99` — the
  CONTEXT sentences of the process-order paragraph and of the "What this
  framework does not claim" bullet are now false: context **is** assembled
  from a codebase and memory records **are** consumed. Correct them to match
  the code, and fix the two citations of `overseer/factory.py:1018`, which
  point at the wrong line.
- Every cited `path:line` must be checked by hand after the edit.
  `scripts/check-doc-references` only proves that the path exists and that
  the line is inside the file; it does not prove that the line still makes
  the claim.
- `WORK_LOG.md` — a new section after `WORK_LOG.md:2024`, in the voice of the
  entries around it: what was asked, the two commands and their results, the
  new test count, what the map now relates, the bounds, the honest limits,
  and the live-run output. The entry must record that the prompt was written
  by the dedicated prompt-writing agent and executed by the primary agent.
- `README.md:67` — extend the codebase-context paragraph to say what the map
  now relates and what the relation's bounds are.

## Acceptance criteria (observable)

1. `python3 scripts/check` passes: the 223 existing tests still pass
   unchanged, the new tests pass, and no existing test was weakened or
   deleted. The new test count is reported.
2. `python3 scripts/check-doc-references` reports every reference resolving,
   and the number of references is not lower than 127.
3. A caller is found and related: the relation entry of the symbol names the
   calling file and the line of the call, with `kind` `call` and `how`
   `parsed`.
4. A test file is identified and related: the symbol's `tests` list names the
   test file and its line, and the map's test inventory lists the file.
5. "No caller found" is a recorded fact: the relation entry exists with an
   empty `callers` list and a reason that names the number of searched files.
6. The bounds hold: `limits.max_reference_files`,
   `limits.max_reference_bytes`, `limits.max_callers_per_symbol`,
   `limits.max_tests_per_symbol`, `limits.max_excerpt_bytes` (8192),
   `limits.max_excerpt_lines` (60), and `limits.max_excerpt_total_bytes`
   (32768) are all recorded in the map and all hold in a workspace built to
   exceed them.
7. A secret-named file is still never opened: it contributes no relation, its
   content is absent from `codebase.json`, and the map records the exclusion.
8. The relation is evidence with a reason per entry: every relation entry
   carries `how` and `kind`, and every relation block carries the reason for
   what could not be done.
9. The attempt sees the relation: `OVERSEER_CODEBASE_SUMMARY` names the
   caller and the test, the manifest's `relevant_code_and_interfaces` source
   names the relation counts, and `manifest['codebase']['relations']` carries
   the counts and the per-symbol entries.
10. The documentation is honest and current: the CONTEXT row's verdict, its
    citations, and its "Next increment" cell are updated; the two false
    CONTEXT sentences outside the row are corrected; `WORK_LOG.md` and
    `README.md` carry the increment.
11. The workspace was not modified: the relation search reads and does not
    write, execute, or import workspace code.

## Constraints / compatibility contracts

- Python 3 standard library only. No new dependency. Nothing is installed.
- The map is read-only with respect to the workspace: it never writes to,
  executes, or imports workspace code.
- The excerpt bounds are unchanged, and the relation has its own explicit
  budget.
- The map and the manifest keep `version` `1`.
- The map's failure shapes keep their `reason` and their empty fields.
- The existing `OVERSEER_CODEBASE_*` variable names and their meanings are
  unchanged.
- The existing tests are not weakened or deleted.
- The existing code style of `overseer/codemap.py`: module-level constants
  for the bounds, small functions whose docstrings state the reason,
  dictionary results with a `reason` field where something could not be
  done.
- One primary editor: the primary agent edits. This prompt does not
  authorize work on any other pillar row, any new dependency, any change to
  the monitor, the scheduler, the model choice, the policy, or the factory's
  ledger schema.
- Do not invent benchmark results, token counts, costs, or savings. The
  token and cost fields stay null.

## Baseline check and known failures

Recorded by the prompt-writing agent:

- `python3 scripts/check` — **223 tests, all pass (OK)**. The agent was
  instructed not to run the suite; the primary agent confirms this number
  before the change and reports any difference.
- `python3 scripts/check-doc-references` — **127 references checked in
  HARNESS_FRAMEWORK.md**, all resolve. Verified by the prompt-writing agent.

No failure is known at the baseline.

## Verification commands

```text
python3 scripts/check
python3 scripts/check-doc-references
```

Both must pass. Report the new test count and the new reference count.

## Allowed work and stopping condition

Allowed: `overseer/codemap.py`, `overseer/factory.py` (the manifest writer and
the codebase environment only), `tests/test_factory.py` (new tests only),
`docs/HARNESS_FRAMEWORK.md` (the CONTEXT row, and the two CONTEXT sentences
that are now false), `WORK_LOG.md`, and `README.md`.

Stop after this one increment: the map relates the selected symbols to their
callers and their tests, the bounds hold, the attempt sees the relation, the
documentation is current and honest, and both verification commands pass.
Report the diff, the two command outputs, the new test count, the new
reference count, and the limits that remain. Do not start the next increment;
do not widen the scope to another pillar row; do not refactor the existing
map while adding the relation.
