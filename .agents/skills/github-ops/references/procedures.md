# Procedures

Contents:

- [Stay read-only until approved](#stay-read-only-until-approved)
- [Requirements](#requirements)
- [Triage every issue to a type and a priority](#triage-every-issue-to-a-type-and-a-priority)
- [Check merge readiness from evidence, not from the diff alone](#check-merge-readiness-from-evidence-not-from-the-diff-alone)
- [Apply the stale policy on a clock, not a feeling](#apply-the-stale-policy-on-a-clock-not-a-feeling)
- [Investigate a CI failure before re-running it](#investigate-a-ci-failure-before-re-running-it)
- [Prepare a release, then stop](#prepare-a-release-then-stop)
- [Read security alerts freely, change nothing without approval](#read-security-alerts-freely-change-nothing-without-approval)

Companion reference for the [github-ops](../SKILL.md) skill. Load it for the exact gh commands and the pass and fail examples behind the approval gate, authentication, triage, merge readiness, the stale policy, CI investigation, releases and security alerts.

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
