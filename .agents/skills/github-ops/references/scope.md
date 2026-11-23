# Scope

Companion reference for the [github-ops](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

Everything in this skill defaults to reading and proposing, and every action that changes repository state or dispatches CI waits for the user to approve it. The skill applies when:

- Triaging issues: classifying, labelling, deduplicating, responding
- Reviewing pull request status, CI checks, age and merge readiness
- Investigating a failing workflow run and finding the root cause
- Preparing a release: changelog, tag, release notes
- Reviewing Dependabot alerts, secret scanning alerts and dependency bumps
- Managing contributor experience on an open repository
- The user says check GitHub, triage issues, review PRs, merge, release, or CI is broken
- The user says "triage these issues", "which PRs are ready to merge", "CI is red, find out why", "prepare the next release" or "check our security alerts"

---

### When not to activate

- Branching, committing, rebasing or resolving conflicts locally, use `git-workflow`
- Deciding whether a work item should exist and how it should be written, use `project-tracking`
- Reading or writing tickets in Jira rather than GitHub issues, use `jira-integration`
- Reviewing the content of a diff for correctness, use `code-reviewer`
- Wording a review comment, a reply to one or an approval, use `review-comments`
- Designing the pipeline the workflow runs, use `deployment-patterns`
- Surveying every automation surface in the project, not just this one, use `automation-inventory`

---

### Related skills

- `git-workflow` owns branching, commit messages, merge versus rebase and conflict resolution on the local side
- `project-tracking` owns whether a work item should exist, how it is sized and what its acceptance criteria are
- `jira-integration` owns the same operational work when the tracker is Jira rather than GitHub issues
- `code-reviewer` owns the correctness review of a pull request diff
- `review-comments` owns the wording of review comments, replies and approvals posted on a pull request
- `deployment-patterns` owns designing the pipeline that a workflow run executes
- `automation-inventory` owns surveying every automation surface, of which CI is one
