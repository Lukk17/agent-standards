---
name: markdown-writer
description: 'Human-facing markdown: README structure, voice without AI tells, diagrams, badges. Use when the user says "fix my README" or "this reads like AI wrote it". Not for an ADR, use `architecture-decision-records`.'
metadata:
  version: "1.1.0"
---

# Markdown Writer

Rules for writing and repairing markdown a human reads: README files, docs landing pages, contributor guides, technical posts. Machine-facing markdown keeps its own conventions and is out of scope.

---

### When not to activate

- A design decision record, use `architecture-decision-records`
- A work item description or its acceptance criteria, use `project-tracking`
- Doc comments or docstrings inside source files, use `coding-standards`

---

### Ask before rewriting

Asked to fix all markdown in a repository, list the files you would skip and why before touching anything, and follow the user when they override an exclusion. When polishing rather than writing, report the findings as a diff plan before rewriting, so the user can veto a section.

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
12. Draw diagrams in Mermaid, preferred over an image: one system overview and one happy-path request flow.
13. Badges come from shields.io only: build, license, language version, last commit, and the moving counts. No vanity badges, and only the top repository in a monorepo.
14. End every README with a documentation map table listing every document the project ships, split into shipped and local where the repository distinguishes them.

---

### Reference files

| Task | Open |
|---|---|
| Reasoning and examples for rules 1 to 5, 13 and 14, the dash check commands, auditing a document | [readme-and-voice.md](references/readme-and-voice.md) |
| Rules 6 to 11 in full: code blocks, links, headings, counts, list markers, wrapping | [formatting-rules.md](references/formatting-rules.md) |
| Drawing a diagram | [mermaid.md](references/mermaid.md) |
| Prose that reads machine-generated | [ai-tells.md](references/ai-tells.md) |
| A translated copy of a document | [multilingual.md](references/multilingual.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling a document done | [checklist.md](references/checklist.md) |
