---
name: github-ops
description: 'Operating a GitHub repository with the gh CLI: issue triage, pull request and stale-item management, CI failure investigation, release preparation and security alerts, read-only by default. Use when the user says "triage these issues", "which PRs are ready to merge", "CI is red, find out why" or "prepare the next release". Not for local branching and commits, use `git-workflow`.'
---

# GitHub Operations

Operating procedures for a GitHub repository through the gh CLI, covering the work that happens after code leaves a
developer's machine. Everything here defaults to reading and proposing, and every action that changes repository
state or dispatches CI waits for the user to approve it.

---

### When to activate

- Triaging issues: classifying, labelling, deduplicating, responding
- Reviewing pull request status, CI checks, age and merge readiness
- Investigating a failing workflow run and finding the root cause
- Preparing a release: changelog, tag, release notes
- Reviewing Dependabot alerts, secret scanning alerts and dependency bumps
- Managing contributor experience on an open repository
- The user says check GitHub, triage issues, review PRs, merge, release, or CI is broken
- The user says "check our security alerts"

---

### When not to activate

- Branching, committing, rebasing or resolving conflicts locally, use `git-workflow`
- Deciding whether a work item should exist and how it should be written, use `project-tracking`
- Reading or writing tickets in Jira rather than GitHub issues, use `jira-integration`
- Reviewing the content of a diff for correctness, use `code-reviewer`
- Designing the pipeline the workflow runs, use `deployment-patterns`
- Surveying every automation surface in the project, not just this one, use `automation-inventory`

---

### Reference files

| Task | Open |
|---|---|
| The gh commands for auth, triage, PR checks, stale queries, failed logs, releases and security alerts, with pass and fail examples | [references/procedures.md](references/procedures.md) |

---

### Stay read-only until approved

Reading is free. Merging, closing, creating a release, re-running a workflow or enabling automation changes state or
dispatches CI, and each of those needs explicit approval for that specific action. Prepare the exact command and
stop.

---

### Rules

1. Check `gh auth status` before the first call rather than diagnosing a 404 later.
2. Give each issue one type (bug, feature-request, question, documentation, enhancement, duplicate, invalid, good-first-issue) and one priority (critical for breaking or security, high, medium, low). Read title, body and comments, search for a duplicate, label, then respond.
3. Call a pull request ready only from evidence: CI conclusion, GitHub's mergeable state, and review age. Flag anything past five days with no review, and hold community contributions to the internal bar.
4. Stale policy: an issue idle fourteen days gets a stale label and a comment, a pull request idle seven days gets a comment, and an issue stale thirty days is proposed for closing, closing only on explicit instruction or a pre-approved stale rule.
5. Compute every cutoff date from today. Never hardcode a literal date.
6. Investigate a CI failure before re-running it: read the failed logs, name the root cause and propose a fix, or record the flaky pattern. A re-run is a CI dispatch and needs approval.
7. A release is prepared here, never in `git-workflow`: confirm CI green on the default branch, list what merged since the last tag, draft the changelog, hand over the exact create command, and stop. It never runs autonomously.
8. Read Dependabot and secret-scanning alerts freely and flag critical and high findings immediately. Enabling Dependabot or other scanning automation, or merging a dependency bump, needs explicit approval.

---

### Related skills

- `git-workflow` owns branching, commit messages, merge versus rebase and conflict resolution on the local side
- `project-tracking` owns whether a work item should exist, how it is sized and what its acceptance criteria are
- `jira-integration` owns the same operational work when the tracker is Jira rather than GitHub issues
- `code-reviewer` owns the correctness review of a pull request diff
- `deployment-patterns` owns designing the pipeline that a workflow run executes
- `automation-inventory` owns surveying every automation surface, of which CI is one

---

### Checklist

- [ ] Every triaged issue carries a type and a priority label
- [ ] No pull request past five days without a review, and none idle seven days without a stale comment
- [ ] Every CI failure was investigated to a named cause, not just re-run
- [ ] Release notes reflect what actually merged since the last tag
- [ ] Security alerts are acknowledged and tracked, criticals raised immediately
- [ ] Every state-changing or CI-dispatching command was approved before it ran
- [ ] No literal date is hardcoded where a computed cutoff belongs
