# Scope

Companion reference for the [architecture-decision-records](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- The user says to record a decision, or asks for an ADR by name
- A choice is made between significant alternatives: framework, library, pattern, database, API shape
- The user states a rationale out loud, in the form of a reason for doing X instead of Y
- The user asks why a past choice was made, which means reading the existing records
- Trade-offs are being weighed during planning, before anything is built
- The user says "record this decision", "ADR this", "we decided Postgres over Mongo", "why did we choose this framework" or "write up the trade-off we just settled"

Without a record, the rationale survives only in a chat log or somebody's memory, and the next person to touch that area has to reconstruct it or repeat the argument.

---

### When not to activate

- Writing the plan, phases, rollback and risk table for carrying the decision out, use `project-tracking`
- Writing a README or docs page for humans, use `markdown-writer`
- Recording a work item, its sizing or its acceptance criteria, use `project-tracking`
- Choosing what the code inside the decision should look like, use `coding-standards`
- Reviewing a diff that implements a decision already recorded, use `code-reviewer`

---

### Related skills

- `project-tracking` owns the implementation plan that follows a decision, including phases, rollback and risk
- `coding-standards` defers here for recording significant design decisions and keeping rationale out of source files
- `markdown-writer` owns human-facing docs, and skips these records deliberately because they have their own template
- `code-reviewer` flags a change that introduces an architectural shift with no record behind it
- `hexagonal-architecture` and `backend-patterns` own the content of the architectural options being weighed
