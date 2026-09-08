---
name: code-reviewer
description: Structured review of local changes or a remote pull request across correctness, maintainability, doc comments, efficiency, security, error handling and test coverage, with every finding led by a path:line reference. Use when you say "review my changes", "review PR #123", "look over this diff before I merge", "is this branch ready to merge", or "review what I have staged". Not for hunting duplicated or reinvented code specifically, use `review-duplication`.
---

# Code Reviewer

Conduct a professional review of a change set, whether it lives in the working tree or in a remote pull request. Review
against the `coding-standards` hub for the shared floor, pull in `review-duplication` for reuse and `security-review`
for security, and lead every finding with a `path:line` reference.

---

### When to activate

- The user asks to review their changes, their staged files, or a diff before merging.
- The user names a pull request by number or URL and wants it reviewed.
- A branch is finished and the user wants to know whether it is ready to merge.
- Another agent has produced an implementation and the change needs a second pair of eyes before it lands.

---

### When not to activate

- Writing the fix rather than reporting it. Hand the findings to the implementing skill or agent, or to the `debugger`
  agent for a root-cause failure.
- A dedicated hunt for duplicated logic or a reinvented utility. Use `review-duplication`.
- A deep security assessment or threat model rather than a review pass. Use `security-review`, and escalate to the
  `security-auditor` agent.
- Profiling and optimising a slow path. Use `performance-optimization`.
- Reviewing prose, a README, or docs. Use `markdown-writer`.

---

### Step 1: determine the review target

A remote pull request is named by number or URL. Anything else, including "review my changes", means the local working
tree, staged and unstaged.

For a remote pull request, check it out first.

```bash
gh pr checkout <PR_NUMBER>
```

Then read the pull request description and existing comments, so the review judges the change against its stated goal
rather than an invented one.

For local changes, read the state directly.

```bash
git status
```

```bash
git diff
```

```bash
git diff --staged
```

---

### Step 2: run the project's verification first

Run the project's verification command as documented in its AGENTS.md before reading a single line, so mechanical
failures are caught mechanically and the review spends its attention on judgement. On a local review of a small change,
ask the user whether to run it. On a pull request, always run it.

Fail: a hardcoded command that does not exist in this project.

```text
Ran npm run preflight. Command not found, skipping verification.
```

Pass: the command the project itself documents.

```text
AGENTS.md documents `./gradlew check` as the verification command. Ran it: 2 test failures in OrderServiceTest.
```

If the project's AGENTS.md documents no verification command, say so in the review rather than guessing at one.

---

### Step 3: analyse against the review pillars

Work through each pillar and cite `path:line` for every finding.

- Correctness. Does the code do what it claims, without logic errors or unhandled states?
- Maintainability. Is the structure clear, single-purpose, and consistent with the patterns already in the project?
- Readability. Does the code read on its own, formatted the way the project formats code, without a comment propping it
  up?
- Doc comments. Javadoc, docstrings, JSDoc, `///` and Go doc comments default to none, because code should explain
  itself through extraction and precise naming. Flag every doc comment that a well-named function or a tighter type
  would have made unnecessary, and flag any that merely restates the signature. Where one is genuinely needed the prose
  caps at five lines and is usually one, `@param` earns its place only for units, nullability, a valid range, or who
  owns the argument afterwards, `@return` only when non-obvious, and `@throws` is required for every exception a caller
  can act on because unchecked exceptions never appear in the signature. Every tag line is capped at one physical line,
  so a `@param` that wraps onto a second line is itself a finding: shorten it or delete it.
- Efficiency. Any query in a loop, unbounded fetch, or sequential await of independent calls introduced here?
- Security. Any injection, missing authorisation check, leaked secret, or unvalidated input?
- Edge cases and error handling. Null, empty, boundary, concurrent, and failure paths.
- Testability. Is the new behaviour actually covered, and which cases are missing?

---

### Step 4: escalate the sensitive findings

Authentication, authorisation, payment, and personal-data findings do not stop at a review comment. Hand them to the
`security-auditor` agent for a dedicated pass before the change merges, and say in the review that you did.

Fail: a serious finding buried as a nitpick.

```text
Nitpick: might be worth checking the caller is the owner here.
```

Pass: named severity, cited location, and escalation.

```text
Critical, src/api/orders.ts:88. The handler deletes any order by id with no ownership check, so any authenticated user can delete another user's order. Escalated to the security-auditor agent for an authorisation review of the whole orders route.
```

---

### Step 5: report

Structure the report the same way every time.

- Summary. What the change does and the overall verdict in two or three sentences.
- Findings, grouped by severity.
  - Critical: bugs, security issues, breaking changes.
  - Improvements: quality, structure, and performance suggestions.
  - Nitpicks: formatting and minor style, optional.
- Conclusion. Approved, or request changes, with the specific blockers named.

Be constructive and specific. Explain why a change is requested, and on an approval name the thing the contribution
actually got right rather than a generic compliment.

For a remote pull request, ask the user at the end whether to switch back to the default branch.

---

### Related skills

- `coding-standards` is the baseline every finding is measured against.
- `review-duplication` finds reinvented utilities and missed reuse.
- `security-review` supplies the security checklist behind the security pillar.
- `performance-optimization` supplies the detail behind the efficiency pillar.
- `tdd-workflow` supplies the coverage bar behind the testability pillar.
- `git-workflow` covers branch, commit and merge hygiene when the review turns up problems there.

---

### Checklist

- [ ] Review target identified: named pull request, or the local working tree.
- [ ] The project's documented verification command was run, or its absence was reported.
- [ ] Every pillar was considered, including doc comments.
- [ ] Every finding cites `path:line`.
- [ ] Findings are grouped by severity, not listed flat.
- [ ] Auth, payment, and sensitive-data findings were escalated to the `security-auditor` agent.
- [ ] The conclusion states approve or request changes, and names the blockers.
- [ ] For a remote pull request, the user was asked about returning to the default branch.
