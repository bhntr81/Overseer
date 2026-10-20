# Record the skill provenance in the context of every attempt

Status: **ready to execute once the widen increment is committed**. This
prompt was written by the dedicated prompt-writing agent of the Overseer
project. The primary agent executes it; writing it is not completion.

The user's request, verbatim:

> Focus exclusively on the Overseer project in this current workspace.
> Implement skills provenance integration for the CONTEXT pillar in the
> factory: 1. Update the manifest builder and run execution pipeline so that
> `factory/skills-provenance.json` is read and recorded in the context manifest
> for every attempt, identifying which skills were active or provided.
> 2. Expose the skill provenance details via environment variables or manifest
> records in the run evidence directory. 3. Add comprehensive unit tests in
> tests/test_factory.py covering skill provenance parsing and manifest
> integration. 4. Run python3 scripts/check and python3 scripts/check-doc-references
> to ensure 100% test pass rates and valid citations, update WORK_LOG.md, and
> commit clean.

It is also the CONTEXT row's named next increment: "read
`factory/skills-provenance.json` into the context: validate it, and record in
the manifest which skills were supplied to the attempt and why, or record that
none was."

## Precondition: start from the widen commit

This prompt was written against the **uncommitted** working tree of the widen
increment (291 tests OK, 155 doc references), which is still under review.
Do not start until that increment is committed. Then:

1. `git status --short` prints nothing except `?? CONTEXT_SKILLS_PROVENANCE_NEXT_PROMPT.md`
   (this prompt itself), and `HEAD` is the widen commit the coordinator names
   (`dba883a`). If the tree is dirty or `HEAD` is not that commit, stop
   and report `needs_input`; do not fold the widen changes into this commit.
2. Re-run both baseline commands and use their counts in place of 291 / 155.
3. **Re-measure every line reference below** against that commit. They were
   measured on the uncommitted tree and the review may move them.

Review lessons carried forward, part of the acceptance:

1. **Line citations drift.** Re-derive every citation by hand after the last
   edit, in every row and passage it touches.
2. **A test is evidence only if a plausible wrong implementation fails it.**
   Run the mutations of section 8 one at a time; show the suite failing for
   each; revert.
3. **Counts describe what is shown.** A count of declared skills is the count
   of entries in the manifest's list; rejected entries are counted apart, with
   their reason.
4. **Evidence is scoped to this attempt, and words claim only what the code
   observed.** The monitor's last review found stops overridden by reports of
   an earlier turn. Here: the facts recorded are read at this attempt's start
   from the file as it is now. No skill is ever recorded as active, loaded, or
   used, because nothing in the factory can observe that.

This prompt files exactly one increment against the **CONTEXT** row of the
harness pillar map (`docs/HARNESS_FRAMEWORK.md:32`). It does not plan work for
the CONTRACT, TOOLS, STATE, PERMISSIONS, or EVIDENCE rows; their citations are
re-derived only where lines move.

## What the file is, and what "active or provided" can truthfully mean

`factory/skills-provenance.json` (2229 bytes, read by no code today) declares
`schema_version: 1`, the upstream `repository`, a 40-hex `revision`, `license`,
`recorded_at`, a `blueprint` block, and three `skills`
(`better-prompt`, `goal-loop`, `effective-agent-skills`). Each skill has
`name`, `source_path`, `installed_path` (under `/home/kali/.codex/skills`),
`upstream_files_sha256` (`{"SKILL.md": <64 hex>}`), `license_sha256`,
`status: "installed_bytes_verified"`, `runtime_activation: "not_tested"`, and
`runtime_discovery: "observed_in_acceptance_reviewer_catalog"`.
`docs/FACTORY_SKILLS.md:53` already says: "The current local runner does not
automatically load or enforce these skills."

The factory runs trusted argument-vector commands. It does not start a Codex
session, does not pass a skill to a command, and cannot see whether a CLI
loaded a skill body. So the manifest records exactly three layers and never a
fourth:

| Layer | What it means | How it is known |
| --- | --- | --- |
| `declared` | the provenance file lists the skill | read and validated at this attempt's start |
| `installed_verified` | at this attempt's start, each file named in `upstream_files_sha256` exists under `installed_path` and its SHA-256 matches | bounded read and hash, section 3 |
| `supplied_to_attempt` | Overseer passed the skill to the attempt | always `false` today, because no code passes one; the reason says so |
| (not recorded) active / loaded / used | — | **not observable; never claimed**. `activation_observed` is `false` for every skill, and the file's own `runtime_activation` and `runtime_discovery` are copied as `declared_runtime_activation` / `declared_runtime_discovery`, labelled as the file's statement |

The answer to "which skills were active or provided" is therefore recorded as
"these were declared, these were installed with matching bytes at the start of
the attempt, none was supplied by Overseer, and activation was not observed".
The manifest note says this in those words.

## Repository and paths

- Repository: `/home/kali/Programming/Projects/Overseer`, branch `main`.
- Python 3 standard library only. No new dependency.

Measured on the uncommitted widen tree; re-measure (precondition 3):

| Path and line | What it is now |
| --- | --- |
| `factory/skills-provenance.json:1` | the file |
| `docs/FACTORY_SKILLS.md:53` | "does not automatically load or enforce these skills" (stays true) |
| `overseer/factory.py:5` | the imports from `overseer.codemap` (`is_secret` lives at `overseer/codemap.py:166`) |
| `overseer/factory.py:20` | `DEFAULT_DB` |
| `overseer/factory.py:395` | `Factory.__init__(self, path=DEFAULT_DB)` |
| `overseer/factory.py:1011` | `_recall_environment`, the pattern for an environment helper |
| `overseer/factory.py:1022` | `_codebase_environment` |
| `overseer/factory.py:1038` | `_context_manifest(..., recall=None, codebase=None)` |
| `overseer/factory.py:1150` | `'supplied': supplied` in the manifest |
| `overseer/factory.py:1242` | `'unmeasured'` in the manifest |
| `overseer/factory.py:1880` | `run_one` |
| `overseer/factory.py:1928` | the map, then `codebase.json`, then `child_env.update(...)` at 1935 |
| `overseer/factory.py:1938` | the `running` / `recall` / `codebase` events |
| `overseer/factory.py:1997` | the `_context_manifest(...)` call; `context.json` at 2000 |
| `tests/test_factory.py:1274` | `class ContextTests`; `setUp` 1277; `command_spec` 1285; `manifest_of` 1332 |
| `tests/test_factory.py:1435` | the test that asserts the **exact** list of `supplied` items |
| `README.md:50` | the skills sentence; the codebase paragraph ends at 111 |
| `docs/HARNESS_FRAMEWORK.md:32` | the CONTEXT row (cites `factory/skills-provenance.json:1`; verdict ends "the skill provenance file is still read by no code") |
| `docs/HARNESS_FRAMEWORK.md:123` | the bullet "`factory/skills-provenance.json:1` is read by no code at all." |
| `WORK_LOG.md:2478` | the widen entry; the file ends at 2555 |

## Required behavior

### 1. A pure reader in its own module

Add `overseer/skills.py`, in the style of `overseer/codemap.py` (module
constants for every bound, small functions whose docstrings state the reason,
dict results, a `reason` wherever something could not be done):

```python
def provenance(path):
    """Read, validate, and check the skill provenance file at the start of an attempt. ..."""
```

It returns one dict (section 4). It never raises for a missing, unreadable,
oversized, or malformed file: it returns `valid: False` with the reason. It
never writes, executes, or imports anything it reads. It may import
`is_secret` from `overseer.codemap`; it imports nothing from
`overseer.factory`.

`Factory.__init__` gains a keyword `skills_provenance=None`. `None` means the
repository's own file, `Path(__file__).resolve().parent.parent / 'factory' /
'skills-provenance.json'`, held in a module constant `SKILLS_PROVENANCE`. Tests
pass their own temporary path. No CLI flag is added.

### 2. Validation

Bounds, as module constants, all recorded in the result's `limits`:
`MAX_PROVENANCE_BYTES = 64 * 1024` (checked with `stat` before the file is
opened), `MAX_SKILLS = 32`, `MAX_SKILL_FILES = 16` (per skill),
`MAX_FIELD_CHARS = 256`, `MAX_SKILL_FILE_BYTES = 256 * 1024`, `MAX_REJECTED = 32`.

File level — any failure gives `valid: False`, `skills: []`, and the reason:
missing; not a regular file; larger than the bound; not UTF-8; not JSON; not an
object; `schema_version` not the integer `1`; `skills` not a list; more than
`MAX_SKILLS` entries (the reason names the count; no entry is kept, so a
truncated list is never presented as the whole).

Top level, copied only when valid: `repository` (string), `revision` (40 lower
hex, else `None` with a note), `license`, `recorded_at` (string, copied as the
file's statement, not parsed). Unknown top-level keys are not copied; their
names are listed, sorted, in `other_keys`. The `blueprint` block is not copied
(its `original_path` is a host path outside the repository); its presence is
noted in `other_keys`.

Entry level — an entry that fails goes to `rejected` with its index and reason,
and the others are kept:

- `name`: matches `^[a-z0-9][a-z0-9-]{0,63}$`; duplicates rejected (the later
  one);
- `source_path`, `status`, `runtime_activation`, `runtime_discovery`:
  nonempty strings ≤ `MAX_FIELD_CHARS`, no control characters;
- `installed_path`: an absolute path string ≤ `MAX_FIELD_CHARS`;
- `upstream_files_sha256`: a nonempty object of ≤ `MAX_SKILL_FILES` entries;
  each key matches `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$` (so no `/`, no `..`, no
  leading dot); each value 64 lower hex;
- `license_sha256`: 64 lower hex.

Only these fields are copied. No other field of an entry reaches the manifest.

### 3. The installed check

For each kept skill and each file named in its `upstream_files_sha256`, at the
start of the attempt:

- target = `Path(installed_path) / name`; if `is_secret(target)`, the file is
  not opened (`secret_name`);
- `os.path.realpath(target)` must lie inside `os.path.realpath(installed_path)`,
  else `outside` (a symlink cannot lead the read elsewhere);
- missing → `missing`; not a regular file → `not_a_file`; larger than
  `MAX_SKILL_FILE_BYTES` (checked before opening) → `too_large`; read error →
  `unreadable`;
- otherwise hash the bytes: `match` or `mismatch`.

The skill's `installed_verified` is `True` only when every named file is
`match`. The license file is not checked (the provenance names no license
path); say so in the docstring. No file content is copied anywhere: only the
outcome word and, for `mismatch`, the observed digest.

### 4. The shape

```python
{'version': 1, 'path': '…/factory/skills-provenance.json', 'present': True,
 'bytes': 2229, 'sha256': '<of the file bytes>', 'valid': True, 'reason': None,
 'schema_version': 1, 'repository': '…', 'revision': '27e2…', 'license': 'MIT',
 'recorded_at': '…', 'other_keys': ['blueprint'],
 'skills': [{'name': 'better-prompt', 'source_path': '…', 'installed_path': '…',
             'declared_status': 'installed_bytes_verified',
             'declared_runtime_activation': 'not_tested',
             'declared_runtime_discovery': 'observed_in_acceptance_reviewer_catalog',
             'license_sha256': '…',
             'files': [{'name': 'SKILL.md', 'expected': '…', 'outcome': 'match',
                        'observed': None}],
             'installed_verified': True,
             'supplied_to_attempt': False,
             'activation_observed': False,
             'reason': 'declared by the provenance file; installed bytes checked at '
                       'the start of this attempt; Overseer supplies no skill to an '
                       'attempt; activation is not observable here'}],
 'declared_count': 3, 'installed_verified_count': 3, 'supplied_count': 0,
 'activation_observed_count': 0,
 'rejected': [], 'rejected_count': 0, 'rejected_truncated': False,
 'note': 'the provenance file declares these skills and their installed bytes '
         'were checked at the start of this attempt; the factory runs '
         'argument-vector commands and supplies no skill to them; whether a '
         'client loaded a skill is not observed',
 'limits': {...}}
```

`skills` is sorted by `name`; `files` by `name`; `rejected` by index. The same
file and the same installed bytes give the same dict, byte for byte under
`json.dumps(sort_keys=True)`. `declared_count == len(skills)`;
`installed_verified_count` counts the listed skills with `installed_verified`;
`rejected_count` counts every rejected entry, and `rejected` lists at most
`MAX_REJECTED`.

### 5. How it reaches the attempt

In `run_one`, after the codebase map and before the `running` events
(re-measure: `overseer/factory.py:1928`–`1938`):

- `skills = provenance(self.skills_provenance)`;
- write it to `evidence / 'skills.json'` and take its SHA-256, as
  `codebase.json` is written;
- `child_env.update(self._skills_environment(skills, path))`, which sets only
  true facts: `OVERSEER_SKILLS_PATH` (the `skills.json` evidence path),
  `OVERSEER_SKILLS_PROVENANCE_SHA256` (the source file's digest, empty when
  absent), `OVERSEER_SKILLS_DECLARED`, `OVERSEER_SKILLS_VERIFIED`. No variable
  names a skill as active or supplied;
- one event `skills`: `'%d skills declared, %d installed bytes verified, none supplied'`,
  or `'skill provenance not recorded: <reason>'`;
- pass `skills_info = {'record': skills, 'path': …, 'sha256': …}` to
  `_context_manifest` as a new keyword `skills=None`.

A missing or malformed provenance file **does not fail or block the attempt**:
the skills are context, not a gate, and the attempt is judged by its checks.
The reason is recorded in `skills.json`, the event, and the manifest.

The manifest gains a top-level `skills` block: `path`, `sha256` (of
`skills.json`), `provenance_path`, `provenance_sha256`, `present`, `valid`,
`reason`, the four counts, `rejected_count`, per-skill
`{name, installed_verified, supplied_to_attempt, activation_observed}`, and the
`note`. The `supplied` list is **unchanged**: it mirrors the blueprint's
context-builder inputs and `tests/test_factory.py:1435` asserts its exact
items; no skill is supplied, so adding a `supplied` item would be false. The
manifest `version` stays `1`, and `'unmeasured'` is unchanged.

### 6. What stays true

- No skill is ever recorded as active, loaded, or used.
- `supplied_to_attempt` is `False` because no code supplies one; a test proves
  it does not depend on the file's `status` text.
- The provenance file is not modified. The installed files are read, never
  written.
- No content of a skill file, and no field outside section 2, reaches the
  manifest, `skills.json`, the environment, or an event.
- The recall, the map, the monitor, and the ledger schema are unchanged.

### 7. Tests

Add tests to `class ContextTests` in `tests/test_factory.py`. Every test that
asserts skill facts builds its own provenance file and installed directory
under `self.root` and constructs `Factory(self.db, skills_provenance=…)`; no
test depends on `/home/kali/.codex` or on the repository's file except one
that only asserts the repository file parses as `valid` with three declared
skills (its installed outcomes are not asserted, so it passes on any host).

1. A valid file with two skills whose installed bytes match: `valid`,
   `declared_count == 2`, `installed_verified_count == 2`,
   `supplied_count == 0`, `activation_observed_count == 0`, every skill
   `supplied_to_attempt` and `activation_observed` `False`.
2. A mismatched file → `mismatch` with the observed digest, `installed_verified`
   `False`, the count drops to what is shown.
3. Missing installed file → `missing`; a symlink pointing outside
   `installed_path` → `outside`, and the outside file's content is not in
   `skills.json`.
4. File-level failures each give `valid: False` with a distinct reason and the
   attempt still `passed`: missing file, invalid JSON, non-object,
   `schema_version: 2`, `skills` not a list, more than `MAX_SKILLS` entries, a
   file larger than `MAX_PROVENANCE_BYTES` (and it is not read: assert by
   `stat`-before-read with a file that is large but valid-looking JSON).
5. Entry-level rejections, each with its reason, while valid siblings are
   kept: bad name, duplicate name, file key `../x`, file key `.env`, short
   hash, relative `installed_path`, missing field, control character.
6. Only whitelisted fields are copied: an extra entry field `"token":
   "UNIQUE_SECRET"` and a top-level `"api_key": "UNIQUE_SECRET2"` never appear
   in `skills.json`, `context.json`, or the child environment; `api_key` is
   listed in `other_keys`.
7. A file whose `status` says `"active"` and `runtime_activation` says
   `"loaded"` still yields `supplied_to_attempt` and `activation_observed`
   `False`, and the declared text appears only under the `declared_` keys.
8. The attempt sees it: the worker writes `OVERSEER_SKILLS_PATH`,
   `OVERSEER_SKILLS_DECLARED`, `OVERSEER_SKILLS_VERIFIED`, and
   `OVERSEER_SKILLS_PROVENANCE_SHA256`; they match `skills.json` and the
   manifest; `skills.json`'s digest matches `manifest['skills']['sha256']`.
9. Determinism: `provenance(path)` twice gives equal dicts under
   `json.dumps(sort_keys=True)`; entries listed out of order come back sorted.
10. The manifest's `supplied` list is unchanged (the existing test at
    `tests/test_factory.py:1435` keeps passing unchanged) and the manifest
    carries the `skills` block with every field of section 5.
11. The provenance file and the installed files are byte-identical after a run.

Mutations — one at a time, show the suite failing, name the failing test,
revert:

- M1 `supplied_to_attempt` derived from the file's `status`;
- M2 `activation_observed` copied from `runtime_activation`;
- M3 the whole entry copied instead of the whitelist (leaks extra fields);
- M4 size checked after reading;
- M5 a symlink followed outside `installed_path`;
- M6 `..` or a leading-dot file key accepted;
- M7 a malformed file raises and fails the attempt;
- M8 `declared_count` counts rejected entries too;
- M9 the `MAX_SKILLS` overflow keeps the first 32 instead of rejecting the
  file;
- M10 `installed_verified` true when any (not every) file matches;
- M11 skills not sorted (input order kept);
- M12 a `supplied` item added for skills;
- M13 the environment carries a skill name as active
  (`OVERSEER_SKILLS_ACTIVE` or similar).

Do not weaken, delete, or rewrite existing tests.

### 8. Documentation

Re-derive every `path:line` after the last edit.

- `docs/HARNESS_FRAMEWORK.md:32` — the CONTEXT row: add citations for
  `overseer/skills.py` (`provenance`, the validation, the installed check), the
  `run_one` lines that write `skills.json` and set the environment,
  `_skills_environment`, and the manifest `skills` block; re-derive every
  existing citation. Replace the verdict clause "the skill provenance file is
  still read by no code" with what is now true: the provenance file is read
  and validated at the start of every attempt, its skills are recorded as
  declared, their installed bytes are checked against the recorded hashes, no
  skill is supplied to an attempt, and activation is not observed; a missing
  or malformed file is recorded with its reason and does not block the
  attempt. Keep "partial". Next increment cell: the row's blueprint items
  (context across sessions, the four memory kinds, the durable entry fields,
  the task inputs, the task result) are now each partly implemented, and the
  handoff record of `docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:299` is the named
  remaining gap the manifest still marks unmeasured. Write: **"persist the
  blueprint's handoff record from the run's own evidence — candidate
  revision, completed and failing acceptance IDs, and next eligible action —
  and keep every field the factory cannot observe marked unmeasured."** Verify
  line 299 is that paragraph before citing it.
- `docs/HARNESS_FRAMEWORK.md:123` — replace "read by no code at all" with: the
  factory reads and validates it and records declared and installed-verified
  skills in each attempt's evidence; it supplies no skill and observes no
  activation. Keep the citation to the file.
- `README.md:50` and the codebase paragraph (ends 111) — one paragraph on
  `skills.json`, the four variables, and the three layers, with the honest
  limit.
- `docs/FACTORY_SKILLS.md:53` — append one sentence: the factory now records
  the provenance and checks the installed bytes for each attempt, and still
  loads or supplies none.
- `WORK_LOG.md` — a new `###` section after the last line: the user's request
  quoted, the precondition commit, what is recorded and what is not, the
  bounds, the commands and results, the new test count, M1–M13 with the
  failing test of each, that every citation was re-derived, and that the prompt
  was written by the dedicated prompt-writing agent and executed by the primary
  agent.

## Acceptance criteria (observable)

1. Precondition met: started from a clean tree at the named widen commit.
2. `python3 scripts/check` passes: all baseline tests unchanged plus the new
   ones (at least baseline + 11). The count is reported.
3. `python3 scripts/check-doc-references`: every reference resolves, count not
   below the baseline.
4. Every completed attempt's evidence directory holds `skills.json`, and its
   `context.json` holds the `skills` block with matching digest.
5. No artifact, variable, or event says a skill was active, loaded, or
   supplied; `supplied_count` and `activation_observed_count` are `0`.
6. A missing or malformed provenance file leaves the attempt's outcome
   unchanged and records the reason.
7. M1–M13 each fail the suite, recorded in the WORK_LOG.
8. `grep -n "^from overseer.factory\|^import overseer.factory" overseer/skills.py`
   prints nothing.
9. The docs carry the increment with re-derived citations.
10. One commit, clean tree after it: `git status --short` prints nothing. This
    prompt file is committed with the increment, as the earlier prompt files are.

## Constraints

- Python 3 standard library only.
- One primary editor. No other pillar row, no new objective, no change to the
  monitor, recall, codemap behaviour, verifiers, ledger schema, or the
  provenance file itself.
- File this increment against exactly the CONTEXT row.
- Do not invent benchmark results, token counts, costs, or savings.

## Verification commands

```text
git status --short          # before: only this prompt untracked, at dba883a
python3 scripts/check
python3 scripts/check-doc-references
grep -n "^from overseer.factory\|^import overseer.factory" overseer/skills.py
git diff --stat
git status --short          # after the commit: empty
```

## Allowed work and stopping condition

Allowed: new `overseer/skills.py`; `overseer/factory.py` (`__init__`, a new
`_skills_environment`, `_context_manifest`'s `skills` keyword and block, and the
`run_one` lines of section 5); `tests/test_factory.py` (new tests only);
`docs/HARNESS_FRAMEWORK.md` (the CONTEXT row, the line-123 bullet, and
re-derived citations elsewhere); `README.md`; `docs/FACTORY_SKILLS.md` (one
sentence); `WORK_LOG.md`.

Commit with a message in the repository's voice, for example "Record the skill
provenance in the context of every attempt", ending with the attribution lines
the session supplies.

Stop after this one increment and its commit: the provenance is read,
validated, checked, and recorded for every attempt without claiming activation
or supply, the attempt sees it, M1–M13 each fail the suite, the docs are
current with re-derived citations, both commands pass, and the tree is clean.
Report the commit hash, the diff summary, the command outputs, the new test and
reference counts, the mutation results, and the limits that remain. This
stopping condition ends this prompt, not the objective: report `step_done`
with the new "Next increment" of the CONTEXT row in `remaining`. If the same
failure recurs twice with no new evidence, stop and report it instead of
retrying.
