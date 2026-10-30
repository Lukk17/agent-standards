---
name: architecture-decision-records
description: 'Capturing an architectural decision as a numbered ADR with context, the decision, rejected alternatives and honest consequences, plus the index and the status lifecycle. Use when the user says "record this decision", "ADR this", "we decided Postgres over Mongo" or "why did we choose this framework". Not for the implementation plan that follows the decision, use `project-tracking`.'
---

# Architecture Decision Records

How to turn a design decision made in a working session into a short document that lives beside the code. Without
one, the rationale survives only in a chat log or somebody's memory, and the next person to touch that area has to
reconstruct it or repeat the argument.

---

### When to activate

- The user says to record a decision, or asks for an ADR by name
- A choice is made between significant alternatives: framework, library, pattern, database, API shape
- The user states a rationale out loud, in the form of a reason for doing X instead of Y
- The user asks why a past choice was made, which means reading the existing records
- Trade-offs are being weighed during planning, before anything is built
- The user says "write up the trade-off we just settled"

---

### When not to activate

- Writing the plan, phases, rollback and risk table for carrying the decision out, use `project-tracking`
- Writing a README or docs page for humans, use `markdown-writer`
- Recording a work item, its sizing or its acceptance criteria, use `project-tracking`
- Choosing what the code inside the decision should look like, use `coding-standards`
- Reviewing a diff that implements a decision already recorded, use `code-reviewer`

---

### Reference files

| Task | Open |
|---|---|
| The full ADR template, the `docs/adr/` layout, the index table, and pass and fail examples for every rule | [references/adr-format-and-examples.md](references/adr-format-and-examples.md) |

---

### Ask before creating anything

An ADR directory and an ADR file are both new files in someone else's repository, so both need consent. On the first
run, if the ADR directory does not exist, ask before creating it along with its index and a blank template. For every
record, present the draft first and write it only after approval. If the user declines, discard the draft and write
nothing.

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

### Related skills

- `project-tracking` owns the implementation plan that follows a decision, including phases, rollback and risk
- `coding-standards` defers here for recording significant design decisions and keeping rationale out of source files
- `markdown-writer` owns human-facing docs, and skips these records deliberately because they have their own template
- `code-reviewer` flags a change that introduces an architectural shift with no record behind it
- `hexagonal-architecture` and `backend-patterns` own the content of the architectural options being weighed

---

### Checklist

- [ ] The directory and every file were created only after the user approved
- [ ] The record names a specific thing, not a category
- [ ] Context is under ten lines and states the forcing constraint
- [ ] At least two alternatives appear, each with a concrete reason it lost
- [ ] Consequences include the negative ones
- [ ] The number follows the highest existing record and the index was updated
- [ ] Status reflects reality, and a superseded record names its replacement
- [ ] A backfilled record carries the original decision date
