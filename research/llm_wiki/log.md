# LLM Wiki activity log

Append entries; do not rewrite or remove earlier entries.

## 2026-10-19 — initial documentation pilot

- Researched the LLM Wiki design note, official Claude Code memory guidance,
  official Obsidian Markdown and link behavior, and the previously reviewed
  Bober_smart folder workflow article. Source titles, URLs, access date, and
  limitations are recorded as F21–F25 in the shared `research/sources.json`.
- Created the schema, navigation index, raw-source intake policy, and one
  source-backed concept note scoped to Overseer. No full external articles were
  copied; the existing `ideas/` images were not duplicated.
- Kept the pilot documentation-only and manual. No provider calls, inference,
  plugins, automation, personal data, code, or tests were added or run.

## 2026-10-19 — verification

- Read back the five wiki Markdown files, source registry additions, and the
  related work-log entry. All wiki-relative Markdown links resolve.
- Parsed `research/sources.json`; JSON is valid, IDs are unique, and F21–F25
  are present.
- `git diff --check` exited 0. No tests were run because this pilot changes
  documentation only and the task excludes tests.

## 2026-10-19 — unattended dispatch question trial

- Question: what must be done before enabling unattended provider dispatch?
- Consulted the factory execution record, Grok support readiness note, routing
  policy proposal, and Software Factory Blueprint v2. Local project sources use
  note-local IDs P01–P04 and relative links; no external-source registry entries
  were added.
- Added the answer note, linked it from the index, and clarified the schema's
  local-source citation rule. The note recommends finishing M1 with a fake
  provider before considering an authorized M2 provider trial. It distinguishes
  recorded status from proposed gates and records auth/budget unknowns.
- Traceability/usefulness assessment: the answer and its recommendation map to
  named local records and locators. The records do not prove the gates passed.
  This is a manual review, not a measured retrieval or accuracy result.
- Verification: pending read-back, link/source checks, JSON parse, and
  `git diff --check`.

## 2026-10-19 — dispatch-trial verification

- Read back the changed schema, index, answer note, activity log, and work-log
  entry. The P01–P04 IDs are defined and cited; all local wiki and project
  source links resolve.
- Parsed `research/sources.json` as JSON. This trial added no source-registry
  entries.
- `git diff --check` exited 0. No tests, provider calls, authentication, or
  inference were performed.
