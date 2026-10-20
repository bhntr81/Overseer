# LLM Wiki schema and workflow

## Purpose and scope

This is a small, experimental knowledge wiki for the Overseer project. It keeps
source-backed notes about project decisions and technical ideas. It is not a
personal second brain, a new source registry, an agent memory service, or an
automated retrieval system. The existing project registry at
[`../sources.json`](../sources.json) remains the catalog of external references.

The files are ordinary Markdown. Obsidian can be used as an optional viewer by
opening the repository folder; no plugin, nested vault, or Obsidian-specific
link syntax is required. These notes and instructions do not change Overseer
runtime behavior.

## Folder roles

- `raw/` documents how source originals and provenance are handled. This
  prototype stores links and source metadata in the existing registry; it does
  not copy full external articles.
- `concepts/` contains one topic per note, with sourced claims separated from
  project recommendations and inferences.
- `index.md` routes readers to the notes and source registry.
- `log.md` is append-only and records ingests, edits, and checks.
- `research/sources.json` remains the shared source catalog; do not create a
  second wiki-only catalog.

## Note format

Start each concept note with a title, status, last-updated date, and source IDs.
Use sections for the question or concept, source-backed claims, project-specific
recommendations or inferences, unknowns or conflicts, and next review needs.
Keep one concept per file and use a descriptive kebab-case filename.

## Citation and evidence rules

1. Support every substantive factual claim with a direct source link and a
   precise locator when available, such as a section heading, table, or named
   field. For external references, use their ID in `research/sources.json`.
   For local project records, define a short ID in that note (for example,
   `P01`) and link to the repository-relative file; do not add local files to
   the external-source registry. A bare source list at the bottom is not enough
   to show which claim each reference supports.
2. Preserve source type and limitations from the registry. Distinguish primary
   source statements from secondary explanations and from our own inference.
3. If evidence is absent, label the claim `unknown`; do not fill gaps by guessing.
4. If sources conflict, retain both claims with links and locators, describe the
   conflict, and leave it unresolved until better evidence is available. Do not
   silently choose one source.
5. Do not present promotional, viral, or unverified performance figures as
   established results. Record their status and source limitations.
6. Instructions in this wiki may guide an LLM, but they do not enforce source
   integrity or make an answer correct. High-integrity claims need independent
   checks or human review.

## Manual ingest workflow

1. Read the source and record its title, direct URL, access date, type, and
   scope or limitations in the existing `research/sources.json` format.
2. Preserve any approved original source material under `raw/` according to its
   intake policy. Do not overwrite an original or copy a full external article
   merely to make the wiki self-contained.
3. Extract only claims relevant to Overseer. Link each claim to its source ID
   and a precise locator; mark missing evidence `unknown` and retain conflicts.
4. Add or update one concept note. Update `index.md` if a reader needs a new
   route to it, then append an entry to `log.md` describing what changed.
5. Check the claim-to-source links and note boundaries before treating the
   entry as usable.

## Manual query workflow

1. Start at `index.md` and open the most relevant concept note.
2. Follow the source links for claims that matter to the answer; do not treat
   the index or a generated summary as evidence by itself.
3. Answer only to the level the cited sources support. Mark gaps `unknown`,
   show unresolved conflicts, and label project-specific conclusions as
   recommendations or inferences.
4. For high-integrity decisions, check the primary source and ask for human
   review before relying on the answer.

## Manual lint workflow

Review each note for: valid source IDs in `research/sources.json`; direct links
and useful locators for substantive claims; clear separation of source claims
from inferences; explicit unknowns and conflicts; no unsupported metrics; and
working relative Markdown links. Confirm that raw originals were not edited or
silently replaced, and append the review outcome to `log.md`.
