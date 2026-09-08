---
name: markdown-writer
description: "Human-facing markdown: README structure, an honest voice with no AI tells, Mermaid diagrams, badges, audit passes over stale docs, and translated copies. Use when you say \"fix my README\", \"write a README for this repo\", \"this reads like AI wrote it\", \"add an architecture diagram to the docs\", or \"polish docs/INGESTION.md\". Not for architecture decision records, which keep their own template, use `architecture-decision-records`."
---

# Markdown Writer

Rules for writing and repairing markdown a human reads: README files, docs landing pages, contributor guides,
technical posts. Machine-facing markdown keeps its own conventions and is out of scope, so check the exclusion list
before rewriting anything.

| Task | Open |
|---|---|
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

---

### When not to activate

- Recording a design decision in the Context, Decision, Consequences form, use `architecture-decision-records`
- Writing or reviewing a work item description or acceptance criteria, use `project-tracking`
- Writing doc comments or docstrings inside source files, use `coding-standards`
- Writing or editing a skill manifest or a subagent definition, which are agent-to-agent files with their own format
- Editing `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, OpenSpec documents or a license, which follow external conventions

---

### Read the ground truth before writing

Pull facts from what the repository already states rather than inferring them from directory names. Check any
`AGENTS.md`, `CLAUDE.md`, architecture notes and existing `docs/` pages first, then the build files for real versions
and ports.

Pass:

```text
Read AGENTS.md and docs/, found the service runs on 8080 with Postgres 16, wrote those numbers into Quick start.
```

Fail:

```text
Saw a Dockerfile, wrote "runs on port 3000" because most services do.
```

---

### Apply the voice rules only to human-facing files

The voice rules make some files worse. Skip them, and make only factual corrections, on machine-facing or
externally-governed files: `AGENTS.md` and `CLAUDE.md`, architecture decision records, OpenSpec proposals and specs,
`CHANGELOG.md`, diagram-only files, skill manifests, subagent definitions, and license files. The no-dash rule and
the factual-accuracy rule still apply everywhere, because humans edit those files too.

When asked to fix all markdown in a repository, list the files you would skip and why before touching anything. If
the user overrides the exclusion for a specific file, follow the user.

Pass:

```text
Rewriting README.md and docs/SETUP.md. Skipping CHANGELOG.md (Keep a Changelog) and openspec/changes/**. Proceed?
```

Fail:

```text
Rewrote every .md file in the repo, including the ADRs, into README voice.
```

---

### Follow one README section order

Write in this order and drop a section that does not apply rather than padding it: title with a one-line tagline and
a tight badge row, what it is and why it exists, quick start, architecture with a diagram, features, an honest
comparison with alternatives, configuration and ports for a service, a documentation map, license.

Pass:

```text
# ordo
Job queue for Postgres.
[badges]
### What it is
### Quick start
### Architecture
### Docs map
```

Fail:

```text
# ordo
### Installation
### API reference for all 40 endpoints
### Contributing
### What it is
```

---

### Write like a tired senior engineer

Use plain, direct sentences in the imperative. Contractions and technical jargon are fine when the audience is
technical. Marketing adjectives with no fact behind them are not: replace each one with the concrete number or
behaviour it was standing in for, or delete it. The full catalogue of machine-writing tells and how to fix each one
is in [ai-tells.md](references/ai-tells.md).

Pass:

```text
Handles about 4,000 jobs per second on one Postgres 16 node. Retries use exponential backoff capped at 30 seconds.
```

Fail:

```text
A robust, comprehensive solution that seamlessly leverages your existing infrastructure at scale.
```

---

### Never use an em dash or an en dash

These are the most reliable machine-writing tell in a technical document, and human engineers rarely reach for them.
Replace one with a comma for a mid-sentence pause, a period for a full break, a colon before an explanation, or
parentheses for an aside. ASCII hyphens inside compound words are fine. Verify after editing rather than trusting the
edit.

Pass:

```bash
grep -P "[\x{2013}\x{2014}]" README.md
```

Fail:

```text
The queue is fast, reliable, and simple to run.
```

That failing line is fine as written. It fails only when the commas are replaced by dashes, which is the shape this
rule exists to prevent.

---

### Formatting mechanics

Six mechanical rules carry most of the difference between a document that reads as maintained and one that does not.
Each is stated in full, with a passing and a failing form, in [formatting-rules.md](references/formatting-rules.md).

| Rule | What it requires |
|---|---|
| One command per fenced block | One runnable command, a language tag, no comment lines inside, no chained commands unless the chain is the command |
| Link every real path | Every concrete file or directory path is a link, on every mention, with plain link text rather than backticked link text |
| Sections at level 3, with dividers | Level 1 is the title, level 2 is unused, and a horizontal rule sits before every section heading including the first |
| Counts live in badges only | A number that moves with project content appears in a badge and nowhere else in prose or in tree comments |
| Digits, never Roman numerals | Ordered lists use Arabic digits, sub-steps use lowercase letters with a closing parenthesis |
| Do not hard-wrap | One physical line per paragraph, list item and table row, except in a project whose own lint enforces a line cap |

---

### Draw diagrams in Mermaid

Prefer Mermaid over an image, because it renders natively on most hosts and it diffs. Use `graph TB` with subgraphs
for a system overview and keep it under a dozen nodes, splitting into two diagrams rather than growing one. Use
`sequenceDiagram` for the happy path of one canonical request, with dashed arrows for async hops, and leave error
branches to `docs/`. Add `accTitle` and `accDescr` to any diagram in a portfolio-facing document.

Pass:

```text
graph TB
  Client --> API
  API --> DB[(Postgres)]
```

Fail:

```text
![architecture](docs/img/architecture-v3-final.png)
```

---

### Keep the badge row tight

Use shields.io as the only badge source, and limit the row to build status, license, primary language version and
last commit. Drop vanity badges: star counts under a few hundred, download counts, made-with hearts. Badge the top
repository only in a monorepo, never each module.

Pass:

```text
[![build](...)](...) [![license](...)](...) [![python](...)](...)
```

Fail:

```text
[![stars](...)](...) [![made with love](...)](...) [![awesome](...)](...)
```

---

### End every README with a documentation map

Close with a table linking every documentation file the project ships, so a first-time visitor finds everything from
one place. Where a repository distinguishes documents it ships downstream from documents that stay local, use two
tables. A file already linked earlier still appears in the map, because the map is the index rather than an addendum.

Pass:

```text
| Document | What it covers |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Local install and first run |
```

Fail:

```text
See the docs folder for more information.
```

---

### Audit an existing document against this list

When polishing rather than writing, walk the document once and report the findings as a diff plan before rewriting,
so the user can veto a section. Look for stale versions in install commands and badges, dead relative links and
broken anchors, backticked link text, em dashes and en dashes, AI-tell phrasing, marketing copy with no claim behind
it, unexplained jargon in the opening paragraphs, comments teaching inside code blocks, Roman numeral markers,
hard-wrapped prose in an unlinted project, counts duplicated out of the badges, missing section rules, level 2
headings, chained commands in one fence, unlinked paths, and a missing documentation map.

Pass:

```text
Found 6 issues in README.md: 2 dead links, 4 em dashes, no docs map. Fix all three groups? Sections 1 and 4 unchanged.
```

Fail:

```text
Rewrote the README.
```

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
- [ ] No em dash or en dash anywhere, verified with a grep
- [ ] No marketing adjective without a concrete fact behind it
- [ ] One runnable command per fence, language tagged, no comments inside
- [ ] Every real path linked, plain link text, on every mention
- [ ] Sections at level 3, one level 1 title, a rule before each section
- [ ] Changing counts left in badges only
- [ ] Diagram present and matching reality
- [ ] Comparison section names where the project loses
- [ ] Documentation map present and listing every project document
