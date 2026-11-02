# README Structure, Voice and Audit

Contents:

- [Read the ground truth before writing](#read-the-ground-truth-before-writing)
- [Apply the voice rules only to human-facing files](#apply-the-voice-rules-only-to-human-facing-files)
- [Follow one README section order](#follow-one-readme-section-order)
- [Write like a tired senior engineer](#write-like-a-tired-senior-engineer)
- [Never use an em dash or an en dash](#never-use-an-em-dash-or-an-en-dash)
- [Draw diagrams in Mermaid](#draw-diagrams-in-mermaid)
- [Keep the badge row tight](#keep-the-badge-row-tight)
- [End every README with a documentation map](#end-every-readme-with-a-documentation-map)
- [Audit an existing document against this list](#audit-an-existing-document-against-this-list)

Companion reference for the [markdown-writer](../SKILL.md) skill. Load it for the reasoning and the pass and fail examples behind reading ground truth, the file exclusion list, the README section order, the voice rules, the dash check commands, Mermaid diagrams, the badge row, the documentation map, and auditing an existing document.

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
is in [ai-tells.md](ai-tells.md).

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

Both checks below print every offending line with its number and print nothing at all for a clean file. The grep form
also exits 0 when a dash is found and 1 when the file is clean, so it can gate a script. `Select-String` exits 0
either way, so read its output rather than its code. Unix shells:

```bash
grep -nE "$(printf '\342\200\224|\342\200\223')" README.md
```

PowerShell:

```powershell
Select-String -Path README.md -Pattern '[\u2014\u2013]'
```

The Unix pattern spells the two characters as their UTF-8 bytes in octal instead of using `grep -P "\x{2014}"`,
because that older form fails two ways. BSD grep, which is what macOS ships, has no `-P` option at all. And PCRE caps
`\x{}` at 0xff outside UTF-8 mode, so in a shell with no UTF-8 locale set (Git Bash on Windows, by default) it exits 2
with `character value in \x{} or \o{} is too large`, matches nothing, and reports a clean file on a file full of
dashes. Do not simplify the pattern back to a `\x{}` escape.

Fail:

```text
A line that joins two clauses with an em dash where a comma or a period belongs.
```

The failing form is described in words rather than printed, because this file itself has to pass the dash lint.

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

Use shields.io as the only badge source, and limit the row to build status, license, primary language version, last
commit, and a badge for each count that moves with project content, because that count lives in a badge and nowhere
else. Drop vanity badges: star counts under a few hundred, download counts, made-with hearts. Badge the top
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
