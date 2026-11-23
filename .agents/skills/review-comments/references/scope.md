# Scope

Companion reference for the [review-comments](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Drafting review comments on somebody else's pull request
- Drafting replies to the review comments on our own pull request
- Writing an approval or a request for changes
- Working through the comments other people left on our code and deciding a response to each
- Posting comments or replies once the user has approved them
- The user says "draft review comments for PR #123", "reply to the review on my PR", "go through the comments on my pull request" or "approve PR #456"

---

### When not to activate

- Writing or editing a pull request description, use `git-workflow`
- Finding what is wrong in the diff, use `code-reviewer`
- Merging, triaging, investigating CI or cutting a release, use `github-ops`
- Writing the ticket a reply points to, use `project-tracking`
- Recording the decision a reply points to, use `architecture-decision-records`

---

### Related skills

- `code-reviewer` owns finding what is wrong in a diff, and this skill words the findings that get posted
- `git-workflow` owns the pull request description and the commit and branch conventions
- `github-ops` owns merging, triage, CI and releases on the hosting platform
- `project-tracking` owns the ticket a reply names when work moves to later
- `architecture-decision-records` owns the decision record a reply points to
