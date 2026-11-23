---
name: github-ops
description: 'GitHub operations with the gh CLI: triage, PR readiness, CI failures, releases, security alerts. Use when the user says "triage these issues" or "CI is red, find out why". Not for local commits, use `git-workflow`.'
metadata:
  version: "1.1.0"
---

# GitHub Operations

Operating procedures for a GitHub repository through the gh CLI, covering the work that happens after code leaves a developer's machine.

| Task | Open |
|---|---|
| The gh commands for auth, triage, PR checks, stale queries, failed logs, releases and security alerts, with pass and fail examples | [procedures.md](references/procedures.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before reporting the work done | [checklist.md](references/checklist.md) |

---

### When not to activate

- Branching, committing, rebasing or resolving conflicts locally, use `git-workflow`
- Wording a review comment, a reply to one or an approval, use `review-comments`
- Reading or writing tickets in Jira rather than GitHub issues, use `jira-integration`

---

### Stay read-only until approved

Reading is free. Merging, closing, creating a release, re-running a workflow or enabling automation changes state or dispatches CI, and each of those needs explicit approval for that specific action. Prepare the exact command and stop.

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
