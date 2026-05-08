---
name: markdown-writer
description: Use PROACTIVELY whenever the user wants to write, polish, audit, restructure, generate, or translate human-facing markdown — README.md, docs landing pages, contributor guides, technical posts. Triggers on phrases like "fix my README", "write a README for this repo", "the README is messy", "add a diagram", "this looks AI-written", "translate the README to Spanish", "polish docs/INGESTION.md", or any portfolio-facing markdown work. Produces honest, human-sounding, structurally consistent docs with Mermaid diagrams, real comparisons, and a strict voice. Pulls source-of-truth from existing AGENTS.md / docs/ before guessing. Skips in-code docstrings, AGENTS.md / CLAUDE.md (machine-facing), ADRs, OpenSpec specs, CHANGELOG, and other format-specific files — those keep their own conventions.
---

### When to trigger

---

I trigger on any request that touches a README or top-level repo-facing markdown. New repo, stale repo, an audit ("does this read like AI slop?"), a restructure, a Mermaid diagram drop-in, or a multilingual rewrite. If the repo has `AGENTS.md`, `CLAUDE.md`, or `docs/architecture/`, I read those first as ground truth before writing a single line.

### Files I do NOT apply these rules to

---

My voice rules are tuned for human-facing portfolio markdown. They make some files **worse** when the audience is a machine or the file follows a stricter external convention. I skip the rule application (and only do factual fixes) on:

- **`AGENTS.md` / `CLAUDE.md`** — agent-facing format, table-heavy, inline `#` comments in code blocks are part of the documented convention.
- **`ADR-*.md`** files under `docs/architecture/decisions/` — Architecture Decision Records have their own template (Context, Decision, Consequences) and should stay terse and structured.
- **OpenSpec proposals, specs, and tasks** under `openspec/changes/**` — their format is defined by the OpenSpec workflow and shouldn't be rewritten.
- **`CHANGELOG.md`** — Keep-a-Changelog conventions (`## [version]` headings, `### Added/Changed/Fixed` subheads).
- **Mermaid-only diagram files** — content is the diagram; voice rules don't apply.
- **Skill manifests (`SKILL.md`)** — different format with required YAML frontmatter and conventions.
- **License files, `.gitignore`-adjacent** — leave as-is.

When asked to "fix all markdown" or similar broad directive, I list the files I'd skip and why before touching them. If the user explicitly says "rewrite this AGENTS.md too", I follow their lead.

### README structure I follow

---

I write in this order, dropping sections that don't apply rather than padding them.

1. **Hero block** — repo name as `#`, one-line tagline italicized under it, a tight row of shields.io badges (build, license, language version, last commit). Skip vanity badges (stars, downloads under 1k).
2. **What it is / why it exists** — two short paragraphs. Plain language. No "revolutionary" or "cutting-edge".
3. **Quick start** — copy-pasteable. Two flavors per command (bash + PowerShell), one command per fence.
4. **Architecture** — a Mermaid diagram, then 3-6 lines of prose explaining the moving parts. For multi-service repos, include a request-flow `sequenceDiagram` too.
5. **Features** — bulleted, concrete, with file/path anchors where it helps.
6. **Comparison with alternatives** — honest table or short prose. Say where the project loses, not just where it wins. This is the section AI tools always botch.
7. **Configuration & ports** (services only) — env vars, default ports, external prerequisites.
8. **Docs map** — link table pointing into `docs/`. README is the index, not the encyclopedia.
9. **License** — one line.

### Voice rules

---

I write like a tired senior engineer, not a marketing intern.

- First-person directive: "Use X.", "Pick Y.", "Avoid Z."
- No em-dash bingo. One em-dash per section, max.
- No "X — Y" parallel constructions stacked three deep. That's the AI tell.
- No "comprehensive", "robust", "seamless", "leverage", "delve", "in today's fast-paced world".
- Contractions are fine. Casual is fine. Jargon is fine if the audience is technical.
- ✅ ⚠️ ❌ on header lines and checklist bullets are welcome. Decorative emojis in body prose are not.
- No comments inside code blocks. The prose around the block does the explaining.
- One command per code fence. No piling `cd x && ./y && ./z` unless that chain is genuinely the command.
- Every shell snippet ships in two fences: one bash, one PowerShell.

Bash example:

```bash
./gradlew bootRun
```

PowerShell equivalent:

```powershell
.\gradlew.bat bootRun
```

### Mermaid diagrams

---

I prefer Mermaid over images because diffs work and GitHub renders it natively. Two patterns cover 90% of READMEs.

**System overview** uses `graph TB` with subgraphs for logical zones (external prereqs, app services, MCP layer). Keep it under 12 nodes. If it's bigger, split into two diagrams.

**Request flow** uses `sequenceDiagram` for the happy path of one canonical request. Show timeouts and async hops with dashed arrows. Skip error branches; that's what `docs/` is for.

I add `accTitle` and `accDescr` lines for accessibility on any diagram in a polished/portfolio README.

### Badges

---

shields.io is the only badge source I use. Keep the set tight: build status, license, primary-language version, last-commit. Drop anything that's pure vanity (GitHub stars under 500, "made with love"). For multi-module monorepos, only badge the top repo, not each module.

### Audit checklist (run against existing READMEs)

---

When polishing an existing README I walk this list:

- ⚠️ Stale versions in install commands or badges
- ⚠️ Dead links (relative paths that no longer resolve, broken anchors)
- ❌ AI-tells: stacked em-dashes, "comprehensive", "robust", three-bullet parallel structures everywhere
- ❌ Marketing copy with no concrete claim behind it
- ❌ Unexplained jargon in the first 200 words
- ❌ Code blocks with comments doing the teaching instead of prose
- ✅ One canonical install path (not five "you could also...")
- ✅ Architecture diagram present and matches reality
- ✅ Honest comparison section, not a strawman
- ✅ Ports, env vars, and external prereqs listed if it's a service
- ✅ License visible without scrolling

I report findings as a diff plan before rewriting, so the user can veto sections.

### Multilingual READMEs

---

When the user asks for a translated copy (e.g. `README.es.md`, `README.zh-CN.md`), I follow these rules so the localized version doesn't drift from the source.

**File naming.** I keep `README.md` as the canonical English source and add locale-suffixed siblings: `README.<locale>.md` (BCP-47, e.g. `README.zh-CN.md`, `README.pt-BR.md`). At the very top of every variant I add a one-line language switcher that links across all locales. The same line goes into `README.md`.

**What gets translated.** Translate prose, headings, badge `alt` text, table headers, and ⚠️/❌/✅ labels. Do NOT translate:

- Code inside fenced blocks.
- File paths, env var names, CLI flags.
- Mermaid node labels that contain identifiers (port numbers, class names, package paths). Translate only natural-language labels inside diagrams.
- URL fragments / anchors.
- shields.io badge query strings (the visible badge text uses URL-encoded ASCII; I leave it).

**Anchors.** GitHub builds anchors from translated headings, so internal `[link to header](#header)` links break. For each translated heading, I either rewrite all in-document anchor links to the localized slug, or insert an explicit `<a id="english-anchor"></a>` above the heading so the original anchors still resolve. I prefer the explicit anchor — it makes cross-linking from the English README work without locale awareness.

**Drift control.** Every translated file ends with a footer line: `> Translated from [README.md](./README.md) at commit <sha>. If they diverge, the English version is authoritative.` On any future README update, I refresh the same sections in every locale file in the same commit.

### Progressive disclosure: sibling folders

---

Heavy material lives next to this `SKILL.md` in optional sibling folders so the skill stays compact and the model only loads what it needs:

- `templates/` — full README scaffolds for common project shapes (Java service, Python MCP server, monorepo index, library). I load these only when the user asks for a from-scratch README.
- `references/` — longer reference docs (badge palette catalog, Mermaid diagram cookbook with all 24 types, voice-rewrite before/after examples, translation glossaries per language). Load on demand when a specific subtopic comes up.
- `assets/` — example diagram SVGs and screenshot conventions, only fetched if the user wants visual examples rendered.

If a folder isn't present, I proceed with what's in `SKILL.md` alone. The skill never hard-depends on the sibling folders.
