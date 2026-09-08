---
name: architecture-decision-records
description: "Capturing an architectural decision as a numbered ADR with context, the decision, rejected alternatives and honest consequences, plus the directory layout, the index, the status lifecycle and how to detect a decision moment in a working session. Use when you say \"record this decision\", \"ADR this\", \"we decided Postgres over Mongo\", \"why did we choose this framework\", or \"write up the trade-off we just settled\". Not for the implementation plan that follows the decision, use `project-tracking`."
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

---

### When not to activate

- Writing the plan, phases, rollback and risk table for carrying the decision out, use `project-tracking`
- Writing a README or docs page for humans, use `markdown-writer`
- Recording a work item, its sizing or its acceptance criteria, use `project-tracking`
- Choosing what the code inside the decision should look like, use `coding-standards`
- Reviewing a diff that implements a decision already recorded, use `code-reviewer`

---

### Use the lightweight ADR format

One file per decision, in the Nygard shape: a title, metadata, context, the decision, the alternatives that lost, and
the consequences including the bad ones.

```markdown
# ADR-NNNN: [Decision Title]

Date: YYYY-MM-DD
Status: proposed | accepted | deprecated | superseded by ADR-NNNN
Deciders: [who was involved]

## Context

What situation is motivating this decision? Two to five sentences on the constraints and the forces at play.

## Decision

What we are doing, in one to three sentences.

## Alternatives Considered

### Alternative 1: [Name]

- Pros: [benefits]
- Cons: [drawbacks]
- Why not: [the specific reason this lost]

### Alternative 2: [Name]

- Pros: [benefits]
- Cons: [drawbacks]
- Why not: [the specific reason this lost]

## Consequences

What gets easier and what gets harder because of this.

### Positive

- [benefit]

### Negative

- [trade-off]

### Risks

- [risk, and how it is mitigated]
```

---

### Ask before creating anything

An ADR directory and an ADR file are both new files in someone else's repository, so both need consent. On the first
run, if the ADR directory does not exist, ask before creating it along with its index and a blank template. For every
record, present the draft first and write it only after approval. If the user declines, discard the draft and write
nothing.

Pass:

```text
No docs/adr/ here yet. Create it with a README index and template.md, then add ADR-0001 for the Postgres choice?
```

Fail:

```text
Created docs/adr/, the index, the template and ADR-0001 so the decision would not get lost.
```

---

### Capture a decision in a fixed order

Extract the architectural choice, gather the context that forced it, document the alternatives and why each one lost,
state the consequences on both sides, take the next number by scanning the existing records, present the draft, then
on approval write the file and append to the index.

The layout that produces:

```text
docs/
  adr/
    README.md
    0001-use-nextjs.md
    0002-postgres-over-mongo.md
    0003-rest-over-graphql.md
    template.md
```

The index is one table, newest appended at the bottom:

```markdown
| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-use-nextjs.md) | Use Next.js as the frontend framework | accepted | 2026-01-15 |
| [0002](0002-postgres-over-mongo.md) | PostgreSQL over MongoDB for the primary datastore | accepted | 2026-01-20 |
```

---

### Answer a why question from the records, not from inference

When asked why a past choice was made, read the index and the matching file and quote its context and decision. If
the directory or the record does not exist, say so and offer to record one now, rather than reconstructing a
plausible rationale that nobody actually held.

Pass:

```text
ADR-0002 says Mongo lost on the reporting queries, which needed joins across four collections. Full text in docs/adr/0002-postgres-over-mongo.md.
```

Fail:

```text
Probably Postgres was chosen for transactional guarantees and ecosystem maturity.
```

---

### Detect the decision moment

Explicit signals are direct: let us go with X, we should use X instead of Y, the trade-off is worth it because,
record this. Act on those.

Implicit signals are weaker: two frameworks compared to a conclusion, a schema choice made with a stated reason, a
pattern picked over another, an authentication strategy settled, infrastructure selected after evaluation. On an
implicit signal, suggest the record and wait, rather than creating one unasked.

Pass:

```text
That looks like a decision worth recording: REST over GraphQL, with the reason you gave about client caching. Draft an ADR?
```

Fail:

```text
Detected a decision and wrote ADR-0004.
```

---

### Be specific, short and honest

Name the actual thing, record the reason rather than the outcome, and keep the whole record readable in about two
minutes. Write in present tense, because the decision is in force now. A context section longer than ten lines is an
essay and needs cutting.

Pass:

```text
# ADR-0007: Use Prisma as the ORM
Context: three services already generate types from the same schema, and hand-written query builders drifted twice.
```

Fail:

```text
# ADR-0007: Use an ORM
Context: ORMs are a widely adopted approach for working with relational data in modern applications, and after considerable evaluation of the landscape the team came to a consensus.
```

---

### Never omit the alternatives

The rejected options are the part a future reader cannot reconstruct. A record with no alternatives says a choice was
made and nothing about why it beat anything else, which leaves the next person free to relitigate it from scratch.

Pass:

```text
Alternative: Mongo. Pros: schema flexibility for the event payloads. Cons: reporting needs four-way joins. Why not: reporting is a launch requirement.
```

Fail:

```text
Alternatives considered: we just picked it.
```

---

### Do not record trivia

Variable naming, formatting choices and library patch bumps do not get records. An ADR directory full of trivia stops
being read, and the significant decisions get buried with the noise.

Categories that do earn a record: technology choice, architecture pattern, API design, data modelling, deployment and
infrastructure, security strategy, testing strategy, and team process such as branching or release cadence.

Pass:

```text
Recording the move from a single service to two, with the boundary and why. Not recording the switch to 4-space indent.
```

Fail:

```text
ADR-0011: Use camelCase for TypeScript variables.
```

---

### Keep the status honest

The lifecycle runs proposed, then accepted, then either deprecated or superseded. A proposed record is still under
discussion. An accepted one is in force. A deprecated one no longer applies because the thing it governed is gone. A
superseded one always names the record that replaced it, so a reader who lands on the old one is sent forward.

When backfilling a past decision, note the original date rather than presenting today's date as when it was made.

Pass:

```text
Status: superseded by ADR-0009
```

Fail:

```text
Status: accepted
```

That failing line is only wrong on a record whose decision has already been replaced. A stale accepted status is
worse than no record, because it is confidently wrong.

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
