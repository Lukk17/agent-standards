---
name: architecture-decision-records
description: 'Recording an architectural decision as a numbered ADR with context, alternatives and consequences. Use when the user says "record this decision" or "ADR this". Not for the implementation plan, use `project-tracking`.'
metadata:
  version: "1.1.0"
---

# Architecture Decision Records

How to turn a design decision made in a working session into a short document that lives beside the code, so the rationale does not survive only in a chat log or somebody's memory.

---

### When not to activate

- Writing the plan, phases, rollback and risk table for carrying the decision out, or a work item with its sizing and acceptance criteria, use `project-tracking`
- Writing a README or docs page for humans, use `markdown-writer`
- Choosing what the code inside the decision should look like, use `coding-standards`

---

### Ask before creating anything

An ADR directory and an ADR file are both new files in someone else's repository, so both need consent. Ask before creating a missing ADR directory with its index and blank template. Present every draft first and write it only after approval. If the user declines, discard the draft and write nothing.

---

### Rules

1. One file per decision in the Nygard shape: title `ADR-NNNN`, metadata (date, status, deciders), context, decision, alternatives considered, and consequences with positive, negative and risks.
2. Capture in order: extract the choice, gather the forcing context, document each alternative and why it lost, state both sides of the consequences, take the next number by scanning the records, present the draft, then on approval write the file and append it to the `docs/adr/README.md` index table.
3. Answer a why question by reading the index and the matching record and quoting its context and decision. When none exists, say so and offer to record one, never reconstruct a plausible rationale.
4. Act on explicit decision signals ("let us go with X", "record this"). On an implicit signal, suggest the record and wait.
5. Name the actual thing, record the reason, write in present tense, keep the record readable in about two minutes, and keep context under ten lines.
6. Never omit the alternatives: each one carries pros, cons and the specific reason it lost.
7. Record only significant decisions (technology, architecture pattern, API design, data modelling, deployment and infrastructure, security, testing strategy, team process), never naming, formatting or patch bumps.
8. Status runs proposed, accepted, then deprecated or superseded. A superseded record names its replacement, and a backfilled record carries the original decision date.

---

### Reference files

| Task | Open |
|---|---|
| Writing a record: the full template, the `docs/adr/` layout, the index table, and the pass and fail example for each rule | [adr-format-and-examples.md](references/adr-format-and-examples.md) |
| Before calling a record done | [checklist.md](references/checklist.md) |
