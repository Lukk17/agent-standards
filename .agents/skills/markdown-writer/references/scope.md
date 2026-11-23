# Scope

Companion reference for the [markdown-writer](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing a README from scratch for a new repository
- Auditing or restructuring an existing README that has gone stale
- Rewriting prose that reads as machine-generated
- Adding a Mermaid architecture or request-flow diagram to a document
- Polishing any document under a `docs/` directory that a person reads
- Producing or refreshing a locale-suffixed copy of an existing document
- The user says "fix my README", "write a README for this repo", "this reads like AI wrote it", "add an architecture diagram to the docs" or "polish docs/INGESTION.md"

---

### When not to activate

- Recording a design decision in the Context, Decision, Consequences form, use `architecture-decision-records`
- Writing or reviewing a work item description or acceptance criteria, use `project-tracking`
- Writing doc comments or docstrings inside source files, use `coding-standards`
- Writing or editing a skill manifest or a subagent definition, which are agent-to-agent files with their own format
- Editing `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, OpenSpec documents or a license, which follow external conventions

---

### Related skills

- `architecture-decision-records` owns the Context, Decision, Consequences template and the decision log
- `project-tracking` owns work item descriptions, acceptance criteria and backlog hygiene
- `coding-standards` owns comments and doc comments inside source files
- `seo` owns keyword strategy and metadata for published web content
- `github-ops` owns release notes and changelog generation from merged pull requests
