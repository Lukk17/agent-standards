# Review Steps

Contents:

- [Step 1: determine the review target](#step-1-determine-the-review-target)
- [Step 2: run the project's verification first](#step-2-run-the-projects-verification-first)
- [Step 3: analyse against the review pillars](#step-3-analyse-against-the-review-pillars)
- [Step 4: escalate the sensitive findings](#step-4-escalate-the-sensitive-findings)
- [Step 5: report](#step-5-report)

Each review step in full, with the exact commands, the reasoning behind the fork rule, the pillar questions, and the pass and fail forms. Load this file when running a step and the one-line summary in SKILL.md is not enough.

---

### Step 1: determine the review target

A remote pull request is named by number or URL. Anything else, including "review my changes", means the local working
tree, staged and unstaged.

For a remote pull request, read it without checking it out. The diff:

```bash
gh pr diff <PR_NUMBER>
```

The description and the existing comments, so the review judges the change against its stated goal rather than an
invented one:

```bash
gh pr view <PR_NUMBER> --comments
```

When the review needs the full tree, check the pull request out only into a separate worktree, never over the user's
current branch, where `gh pr checkout` would switch branches under their uncommitted work:

```bash
git worktree add --detach ../review-pr-<PR_NUMBER>
```

Then run `gh pr checkout <PR_NUMBER>` from inside that worktree.

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
ask the user whether to run it.

A pull request from a fork or from an author outside the team is untrusted input. Its build scripts, test files and
package manifest can carry a payload that runs the moment the verification command does, with the user's credentials
and shell. Ask the user before running anything from it, run it only inside the separate worktree, and never with
production credentials in the environment. GitHub Security Lab gives the same rule for CI: "Any automated processing of
PRs from an external fork is potentially dangerous and such PRs should be treated like untrusted input"
(https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/).

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
- Doc comments. Apply the `coding-standards` "Doc Comments" rule and the language skill's delta. Flag one that
  restates the signature, a wrapped tag line, and a missing throws or `Raises:` entry for an error the caller can act
  on.
- Efficiency. Any query in a loop, unbounded fetch, or sequential await of independent calls introduced here?
- Security. Any injection, missing authorisation check, leaked secret, or unvalidated input?
- Styling. When the change touches styling, check it against the styling-drift criteria in `design-system`.
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

For a remote pull request reviewed in a worktree, ask the user at the end whether to remove it with
`git worktree remove`.
