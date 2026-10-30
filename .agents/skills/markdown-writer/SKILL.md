---
name: markdown-writer
description: 'Human-facing markdown: README structure, an honest voice with no AI tells, Mermaid diagrams, badges, audit passes over stale docs, and translated copies. Use when the user says "fix my README", "write a README for this repo", "this reads like AI wrote it" or "add an architecture diagram to the docs". Not for architecture decision records, use `architecture-decision-records`.'
---

# Markdown Writer

Rules for writing and repairing markdown a human reads: README files, docs landing pages, contributor guides,
technical posts. Machine-facing markdown keeps its own conventions and is out of scope, so check the exclusion list
before rewriting anything.

| Task | Open |
|---|---|
| The reasoning and examples behind ground truth, exclusions, README order, voice, the dash check commands, diagrams, badges, docs map, and audits | [readme-and-voice.md](references/readme-and-voice.md) |
| Applying a formatting rule: code blocks, links, headings, counts, list markers, wrapping | [formatting-rules.md](references/formatting-rules.md) |
| Spotting and removing AI-tell phrasing in prose | [ai-tells.md](references/ai-tells.md) |
| Adding or refreshing a translated copy of a document | [multilingual.md](references/multilingual.md) |

---

### When to activate

- Writing a README from scratch for a new repository
- Auditing or restructuring an existing README that has gone stale
- Rewriting prose that reads as machine-generated
- Adding a Mermaid architecture or request-flow diagram to a document
- Polishing any document under a `docs/` directory that a person reads
- Producing or refreshing a locale-suffixed copy of an existing document
- The user says "polish docs/INGESTION.md"

---

### When not to activate

- Recording a design decision in the Context, Decision, Consequences form, use `architecture-decision-records`
- Writing or reviewing a work item description or acceptance criteria, use `project-tracking`
- Writing doc comments or docstrings inside source files, use `coding-standards`
- Writing or editing a skill manifest or a subagent definition, which are agent-to-agent files with their own format
- Editing `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, OpenSpec documents or a license, which follow external conventions

---

### Ask before rewriting

When asked to fix all markdown in a repository, list the files you would skip and why before touching anything. If
the user overrides the exclusion for a specific file, follow the user. When polishing rather than writing, walk the
document once and report the findings as a diff plan before rewriting, so the user can veto a section.

---

### Rules

1. Read the ground truth first: `AGENTS.md`, `CLAUDE.md`, architecture notes and `docs/`, then build files for real versions and ports. Never infer facts from directory names.
2. Skip the voice rules, and make only factual corrections, on machine-facing or externally governed files: `AGENTS.md`, `CLAUDE.md`, ADRs, OpenSpec documents, `CHANGELOG.md`, diagram-only files, skill manifests, subagent definitions and licenses. The no-dash and factual-accuracy rules apply everywhere.
3. README order: title with tagline and badges, what it is and why, quick start, architecture with a diagram, features, an honest comparison, configuration and ports for a service, documentation map, license. Drop a section that does not apply rather than padding it.
4. Write plain, direct, imperative sentences. Replace every marketing adjective with the number or behaviour it stood for, or delete it.
5. Never use an em dash or an en dash. Use a comma, a period, a colon or parentheses, and verify with the dash check command rather than by reading the edit.
6. One runnable command per fenced block, with a language tag and no comment lines inside.
7. Link every concrete path on every mention, with plain link text.
8. Level 1 is the title, level 2 is unused, sections start at level 3, and a horizontal rule sits before every section heading.
9. A count that moves with project content lives in a badge only.
10. Ordered lists use Arabic digits, sub-steps lowercase letters with a closing parenthesis.
11. Do not hard-wrap, unless the project's own lint enforces a line cap.
12. Draw diagrams in Mermaid: `graph TB` with subgraphs under a dozen nodes for an overview, `sequenceDiagram` for one happy-path request, and `accTitle` and `accDescr` in a portfolio-facing document.
13. Badges come from shields.io only: build, license, language version, last commit, and the moving counts. No vanity badges, and only the top repository in a monorepo.
14. End every README with a documentation map table listing every document the project ships, split into shipped and local where the repository distinguishes them.

---

### Related skills

- `architecture-decision-records` owns the Context, Decision, Consequences template and the decision log
- `project-tracking` owns work item descriptions, acceptance criteria and backlog hygiene
- `coding-standards` owns comments and doc comments inside source files
- `seo` owns keyword strategy and metadata for published web content
- `github-ops` owns release notes and changelog generation from merged pull requests

---

### Checklist

- [ ] Ground truth read from existing project documents before writing
- [ ] Machine-facing and externally-governed files listed and skipped
- [ ] Section order followed, empty sections dropped rather than padded
- [ ] No em dash or en dash anywhere, verified by running the dash check rather than by reading the edit
- [ ] No marketing adjective without a concrete fact behind it
- [ ] One runnable command per fence, language tagged, no comments inside
- [ ] Every real path linked, plain link text, on every mention
- [ ] Sections at level 3, one level 1 title, a rule before each section
- [ ] Changing counts left in badges only
- [ ] Diagram present and matching reality
- [ ] Comparison section names where the project loses
- [ ] Documentation map present and listing every project document
