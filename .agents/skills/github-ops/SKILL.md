---
name: github-ops
description: 'Operating a GitHub repository with the gh CLI: issue triage, pull request and stale-item management, CI failure investigation, release preparation, and security alert review, read-only by default with state changes gated on approval. Use when you say "triage these issues", "which PRs are ready to merge", "CI is red, find out why", "prepare the 1.4.0 release", or "check our security alerts". Not for local branching and commits, use `git-workflow`.'
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

---

### When not to activate

- Branching, committing, rebasing or resolving conflicts locally, use `git-workflow`
- Deciding whether a work item should exist and how it should be written, use `project-tracking`
- Reading or writing tickets in Jira rather than GitHub issues, use `jira-integration`
- Reviewing the content of a diff for correctness, use `code-reviewer`
- Designing the pipeline the workflow runs, use `deployment-patterns`
- Surveying every automation surface in the project, not just this one, use `automation-inventory`

---

### Stay read-only until approved

Reading is free. Merging, closing, creating a release, re-running a workflow or enabling automation changes state or
dispatches CI, and each of those needs explicit approval for that specific action. Prepare the exact command and
stop.

Pass:

```text
Ready to publish. Run this when you approve: gh release create v1.4.0 --title "v1.4.0" --generate-notes
```

Fail:

```text
CI was red so I re-ran the failed jobs to see if it was flaky.
```

---

### Requirements

The gh CLI handles every operation here, authenticated against the repository with `gh auth login`. Verify
authentication before the first call rather than diagnosing a 404 later.

```bash
gh auth status
```

---

### Triage every issue to a type and a priority

Give each issue one type and one priority, so a filter returns a usable set. Types: bug, feature-request, question,
documentation, enhancement, duplicate, invalid, good-first-issue. Priorities: critical for breaking or security,
high for significant impact, medium for nice to have, low for cosmetic.

Work the issue in order: read the title, body and comments, search for a duplicate, apply labels, then respond. A
question gets a drafted answer, a bug missing detail gets a request for reproduction steps, a duplicate gets a
comment linking the original plus the duplicate label.

Pass:

```bash
gh issue list --search "connection pool exhausted" --state all --limit 20
```

Fail:

```text
Labelled it "bug, high-priority, needs-triage, help-wanted, discussion" without reading the comments.
```

---

### Check merge readiness from evidence, not from the diff alone

Before calling a pull request ready, check the CI conclusion, whether GitHub reports it mergeable, and how long it
has sat without a review. Flag anything past five days with no review. Hold a community contribution to the same
test and convention bar as an internal one.

Pass:

```bash
gh pr checks 412
```

Fail:

```text
The diff looks fine, so it is ready to merge.
```

---

### Apply the stale policy on a clock, not a feeling

An issue with no activity for fourteen days gets a stale label and a comment asking for an update. A pull request
with no activity for seven days gets a comment asking whether it is still active. An issue stale for thirty days with
no response is proposed for closing, and closes only on explicit instruction or under a stale rule the user has
already pre-approved.

Pass:

```bash
gh pr list --json number,title,updatedAt --jq '.[] | select(.updatedAt < "<ISO_DATE>")'
```

Fail:

```text
This issue has been quiet for a while, closing it as stale.
```

Substitute a real cutoff date computed from today for `<ISO_DATE>`. A date hardcoded into the skill would silently
select the wrong set the moment it aged.

---

### Investigate a CI failure before re-running it

Pull the failing logs, find the failing step, and decide whether the failure is real or flaky. A real failure gets a
named root cause and a proposed fix. A flaky one gets its pattern recorded so the flake can be tracked rather than
absorbed. Re-running is a CI dispatch and needs approval, so it is never the first move.

Pass:

```bash
gh run view <run-id> --log-failed
```

Fail:

```text
Re-ran it three times until it went green.
```

---

### Prepare a release, then stop

Release management lives here rather than in `git-workflow`, so this is the single procedure for cutting one. Confirm
CI is green on the default branch, list what has merged since the last release, draft the changelog from those pull
request titles, then prepare the exact create command and hand it over. Creating a release publishes artifacts and
dispatches workflows, so it never runs autonomously.

List what shipped since the last tag:

```bash
gh pr list --state merged --base main --search "merged:><ISO_DATE_OF_LAST_RELEASE>"
```

Prepare, and hold for approval:

```bash
gh release create v1.4.0 --title "v1.4.0" --generate-notes
```

For a pre-release:

```bash
gh release create v1.5.0-rc1 --prerelease --title "v1.5.0 Release Candidate 1"
```

Pass:

```text
CI green on main. 14 PRs merged since v1.3.0. Changelog drafted below. Approve and I will hand you the create command.
```

Fail:

```text
Cut and published v1.4.0.
```

---

### Read security alerts freely, change nothing without approval

Reading Dependabot and secret-scanning alerts is a read operation and needs no gate. Enabling Dependabot, turning on
any self-scanning automation, or merging a dependency bump is a state change that dispatches CI and needs explicit
approval. Flag critical and high severity findings immediately rather than batching them into a report.

```bash
gh api repos/{owner}/{repo}/dependabot/alerts --jq '.[].security_advisory.summary'
```

```bash
gh api repos/{owner}/{repo}/secret-scanning/alerts --jq '.[].state'
```

Pass:

```text
2 critical alerts. Both fixed by bumping one transitive dep. Bump PR #58 is open, ready for your approval to merge.
```

Fail:

```text
Enabled Dependabot and auto-merge for patch updates so this stops happening.
```

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
- [ ] No pull request older than seven days without a review or a comment
- [ ] Every CI failure was investigated to a named cause, not just re-run
- [ ] Release notes reflect what actually merged since the last tag
- [ ] Security alerts are acknowledged and tracked, criticals raised immediately
- [ ] Every state-changing or CI-dispatching command was approved before it ran
- [ ] No literal date is hardcoded where a computed cutoff belongs
