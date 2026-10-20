# The LLM Wiki pattern

**Status:** exploratory project note  
**Updated:** 2026-10-19  
**Sources:** F21–F25 in [`research/sources.json`](../../sources.json)

## Source-backed claims

Karpathy describes an LLM Wiki as a persistent set of interlinked Markdown
pages that an LLM incrementally builds from source material. His proposed
structure separates original sources, derived wiki pages, and a schema or
instruction file; the described workflows include ingesting one source,
querying relevant notes, and checking for contradictions, stale claims, or
missing links. The gist presents this as an idea and design pattern, not a
finished product or a measured performance result. See [F21](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
“The core idea” (lines 67–80), “Architecture” (lines 81–87), “Operations”
(lines 88–93), and “Indexing and logging” (lines 94–102).

The Bober_smart guide recommends a short routing file, semantic folders, and
topic-sized Markdown notes with source-oriented answering rules. It is a
secondary how-to article; its operational or performance claims are not
independent evidence that the workflow is accurate or faster. See [F25](https://www.maxed.wiki/posts/claude-second-brain-folder-workflow-the-complete-guide/),
sections on folder layout, the index, and the answer protocol.

Anthropic documents CLAUDE.md as persistent project instructions and states
that instruction files and auto memory are loaded as context, not enforced
configuration. The docs say a PreToolUse hook is needed to block an action
regardless of the model's decision. See [F22](https://code.claude.com/docs/en/memory),
“CLAUDE.md vs auto memory” and “Write effective instructions” (lines 142–152
and 201–207).

Obsidian stores notes as local Markdown files, and its documentation describes
both Obsidian-style and standard Markdown links. This means the notes can remain
plain files and use portable Markdown links while Obsidian is optional. See
[F23](https://obsidian.md/help/Files%2Band%2Bfolders/How%2BObsidian%2Bstores%2Bdata),
the description of vault files, and
[F24](https://obsidian.md/help/Linking%2Bnotes%2Band%2Bfiles/Internal%2Blinks),
the section on Markdown links.

## Recommendation for Overseer

**Inference and recommendation:** a small project-scoped wiki is worth trying
as documentation because Overseer already has a [shared source registry](../../sources.json)
and a [factory execution record](../../../docs/FACTORY_EXECUTION.md). Keeping a
concept note beside those records can make decisions and technical ideas easier
to revisit without adding provider calls, agent swarms, plugins, or code. This
prototype reuses `research/sources.json` and starts with one concept note; it
is not a personal knowledge vault.

The current pilot is deliberately manual. A useful next evaluation would be to
answer one real Overseer design question from these notes, then inspect whether
each claim has an appropriate citation and whether gaps or conflicts were
reported. No retrieval accuracy, speed, or cost benefit has been measured.

## Limits and review needs

The design depends on careful source records and human maintenance. A Markdown
schema, Claude Code memory file, or other LLM instruction is guidance, not an
enforcement mechanism. **Inference from F22:** because project memory provides
context instead of enforceable fact checks, an instruction to cite sources
cannot prove a cited claim is correct. Follow the [schema's evidence rules](../SCHEMA.md):
label absent evidence `unknown`, retain conflicting sources with citations,
label inferences, and independently check high-integrity claims.
