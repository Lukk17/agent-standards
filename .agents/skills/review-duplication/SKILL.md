---
name: review-duplication
description: 'Finds duplicated logic, reinvented utilities and missed reuse. Use when the user says "check this PR for duplication" or "did we already have a function for this". Not for a full review, use `code-reviewer`.'
metadata:
  version: "1.1.0"
---

# Review Duplication

Investigate a codebase during review to find logic the project already has, utilities that were reinvented, and established patterns the change walked past, and leave coincidental lookalikes alone.

| Task | Open |
|---|---|
| Running a step in full: the location table, the subagent names per runtime, the pass and fail forms | [worked-steps.md](references/worked-steps.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before folding the findings into the review | [checklist.md](references/checklist.md) |

---

### When not to activate

- The full review pass across correctness, security, performance and tests, use `code-reviewer`, which invokes this skill as its reuse step.
- Deciding whether a new dependency is admissible and where its version is pinned, use `build-dependency-management`.
- Restructuring the duplicated code once it is found, use the language skill that owns it, such as `python-patterns`, `golang-patterns` or `java-coding-standards`.

---

### Steps

1. Extract the core logic. Look past the business wrapper to the algorithm, utility, data structure or component underneath, because reuse is found by shape, not by feature name.
2. Hypothesise where it would already live. Name candidate locations from the project's real layout before searching. Trace a newly imported library to its existing usage and wrapper, and check the manifest for an installed library that already provides a hand-written algorithm, a blank check or format sniffing included.
3. Delegate the investigation with a specific objective built from step 1, to `code-archaeologist`, a fast read-only search subagent or a general subagent. A single-fact check is done directly. A subagent with no tool to spawn another searches directly from the candidates of step 2 and names the open-ended delegation as a next step for its caller.
4. Evaluate against project conventions. Bypassing an established pattern duplicates the decision behind it. Name a genuinely new pattern explicitly. Before proposing a merge, show the two copies encode the same rule and change for the same reason, and keep coincidental lookalikes separate.
5. Report what should have been reused. Cite the project-relative path and the exact symbol, show the replacement call, and state the value in one clause: consistency, maintenance, or edge cases the existing code already handles.
