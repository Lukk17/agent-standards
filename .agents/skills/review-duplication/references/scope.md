# Scope

Companion reference for the [review-duplication](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Reviewing a change that introduces a helper, formatter, validator, client wrapper, or generic component.
- A new third-party dependency or a new import of an existing one appears in the diff.
- The user asks whether something already exists in the project, or why two similar things now exist.
- A reviewer's instinct says "we have this somewhere", and the location needs to be found before the review is finalised.
- The user says "check this PR for duplication", "did we already have a function for this", "is this reinventing something", "why is there a second date formatter" or "review this for reuse before I approve it".

---

### When not to activate

- The full review pass across correctness, security, performance and tests. Use `code-reviewer` and invoke this skill as
  its reuse step.
- Mapping an unfamiliar codebase for its own sake rather than for one change. Use the `code-archaeologist` agent
  directly.
- Deciding whether a new dependency is admissible and where its version is pinned. Use `build-dependency-management`.
- Restructuring the duplicated code once it is found. Use the language skill that owns it, such as `python-patterns`,
  `golang-patterns`, or `java-coding-standards`.

---

### Related skills

- `code-reviewer` is the parent review workflow. This skill is its reuse step and findings feed back into that report.
- `coding-standards` holds the DRY principle and the conventions reuse is judged against.
- `build-dependency-management` owns whether a newly imported library should be there at all.
- `hexagonal-architecture` helps when the duplication is a boundary problem rather than a copied function.
