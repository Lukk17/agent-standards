# Scope

Companion reference for the [code-reviewer](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- The user asks to review their changes, their staged files, or a diff before merging, as in "review my changes",
  "look over this diff before I merge", or "review what I have staged".
- The user names a pull request by number or URL and wants it reviewed, as in "review PR #123".
- A branch is finished and the user asks "is this branch ready to merge".
- Another agent has produced an implementation and the change needs a second pair of eyes before it lands.

---

### When not to activate

- Writing the fix rather than reporting it. Hand the findings to the implementing skill or agent, or to the `debugger`
  agent for a root-cause failure.
- A dedicated hunt for duplicated logic or a reinvented utility. Use `review-duplication`.
- A deep security assessment or threat model rather than a review pass. Use the `security-auditor` agent, and keep
  `application-security-review` for the security checklist pass.
- Profiling and optimising a slow path. Use `performance-optimization`.
- Reviewing prose, a README, or docs. Use `markdown-writer`.
- Wording findings as comments to post on the pull request. Use `review-comments`.

---

### Related skills

- `coding-standards` is the baseline every finding is measured against.
- `review-duplication` finds reinvented utilities and missed reuse.
- `application-security-review` supplies the security checklist behind the security pillar.
- `performance-optimization` supplies the detail behind the efficiency pillar.
- `tdd-workflow` supplies the coverage bar behind the testability pillar.
- `design-system` supplies the styling-drift criteria when a change touches styling.
- `git-workflow` covers branch, commit and merge hygiene when the review turns up problems there.
- `review-comments` words the findings that get posted on the pull request.
