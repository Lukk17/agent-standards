---
name: review-duplication
description: 'Investigates a change for duplicated logic, reinvented utilities and missed reuse of existing helpers and installed libraries, and leaves coincidental lookalikes alone. Use when the user says "check this PR for duplication", "did we already have a function for this", or "is this reinventing something". Not for a full multi-pillar review pass, use `code-reviewer`.'
---

# Review Duplication

Investigate a codebase during review to find logic the project already has, utilities that were reinvented, and
established patterns the change walked past. The conventions you check reuse against, and the DRY principle behind this
skill, live in the `coding-standards` hub.

| Task | Open |
|---|---|
| Running a step in full: the location table, the subagent names per runtime, and the pass and fail forms | [worked-steps.md](references/worked-steps.md) |

---

### When to activate

- Reviewing a change that introduces a helper, formatter, validator, client wrapper, or generic component.
- A new third-party dependency or a new import of an existing one appears in the diff.
- The user asks whether something already exists in the project, or why two similar things now exist.
- A reviewer's instinct says "we have this somewhere", and the location needs to be found before the review is
  finalised.
- The user says "why is there a second date formatter" or "review this for reuse before I approve it".

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

### Steps

1. Extract the core logic. Look past the business wrapper to the algorithm, utility, data structure or component underneath, because reuse is found by shape, not by feature name.
2. Hypothesise where it would already live. Name candidate locations from the project's real layout before searching: shared utilities, UI components, domain services, configuration, cross-cutting logic. Trace a newly imported library to its existing usage and wrapper, and check the manifest for an installed library that already provides a hand-written algorithm.
3. Delegate the investigation with a specific objective built from step 1. `code-archaeologist` answers structural questions and how to refactor onto what it finds, a fast read-only search subagent narrows candidates, and a general subagent does turn-intensive semantic comparison. A single-fact check, such as one package name in the manifest, is done directly.
4. Evaluate against project conventions. Bypassing an established pattern duplicates the decision behind it: error types and logging, state stores, styling tokens, the config object. Name a genuinely new pattern explicitly. Before proposing a merge, show the two copies encode the same rule and change for the same reason; coincidental lookalikes stay separate.
5. Report what should have been reused. Cite the project-relative path and the exact symbol, show the replacement call, and state the value in one clause: consistency, maintenance, or edge cases the existing code already handles.

---

### Related skills

- `code-reviewer` is the parent review workflow. This skill is its reuse step and findings feed back into that report.
- `coding-standards` holds the DRY principle and the conventions reuse is judged against.
- `build-dependency-management` owns whether a newly imported library should be there at all.
- `hexagonal-architecture` helps when the duplication is a boundary problem rather than a copied function.

---

### Checklist

- [ ] The underlying mechanic was named, not just the feature.
- [ ] Candidate locations were hypothesised from the project's real layout before searching.
- [ ] Any newly imported library was traced to its existing usage and wrapper.
- [ ] The manifest was checked for an installed library that already solves the problem.
- [ ] Open-ended searching was delegated to `code-archaeologist`, a read-only search subagent, or a general subagent.
- [ ] Convention bypasses were checked, not only copied code.
- [ ] Every proposed merge shows the two copies encode the same rule and change for the same reason.
- [ ] Every finding names the reusable symbol, its path, and how to call it.
- [ ] Findings were folded back into the `code-reviewer` report.
