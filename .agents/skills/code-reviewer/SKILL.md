---
name: code-reviewer
description: 'Structured review of local changes or a remote pull request across correctness, maintainability, doc comments, efficiency, security, error handling and tests, with every finding led by a path:line reference. Use when the user says "review my changes", "review PR #123", or "is this branch ready to merge". Not for hunting duplicated or reinvented code, use `review-duplication`.'
---

# Code Reviewer

Conduct a professional review of a change set, whether it lives in the working tree or in a remote pull request. Review
against the `coding-standards` hub for the shared floor, pull in `review-duplication` for reuse and `security-review`
for security, and lead every finding with a `path:line` reference.

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
  `security-review` for the security checklist pass.
- Profiling and optimising a slow path. Use `performance-optimization`.
- Reviewing prose, a README, or docs. Use `markdown-writer`.

---

### When run as a subagent

A read-only subagent, such as the `code-reviewer` agent with its few git commands or the `security-auditor` agent with
no shell at all, cannot run the steps below that check code out, execute code, or ask the user. It changes them so:

- Review the diff the caller supplies. With no diff in the prompt and a shell that allows it, read `git diff`,
  `git diff --staged`, `git show`, or `gh pr diff` and `gh pr view`. With neither, return the question to the caller.
- Skip the worktree and every command that builds, tests or runs the change, and report the verification as
  `not run`, naming the command the project's AGENTS.md documents so the caller can run it.
- Return every question to the caller instead of asking the user, including whether to run anything from a fork.
- Hand the security escalation of Step 4 to the caller as a named next step, since neither agent has a tool to spawn another.

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

---

### Related skills

- `coding-standards` is the baseline every finding is measured against.
- `review-duplication` finds reinvented utilities and missed reuse.
- `security-review` supplies the security checklist behind the security pillar.
- `performance-optimization` supplies the detail behind the efficiency pillar.
- `tdd-workflow` supplies the coverage bar behind the testability pillar.
- `design-system` supplies the styling-drift criteria when a change touches styling.
- `git-workflow` covers branch, commit and merge hygiene when the review turns up problems there.

---

### Checklist

- [ ] Review target identified: named pull request, or the local working tree.
- [ ] A remote pull request was read with `gh pr diff`, and checked out only into a separate worktree.
- [ ] The project's documented verification command was run, or its absence was reported, or as a subagent it was
  reported as `not run`.
- [ ] Nothing from a fork or an outside author ran without the user's approval.
- [ ] Every pillar was considered, including doc comments.
- [ ] Every finding cites `path:line`.
- [ ] Findings are grouped by severity, not listed flat.
- [ ] Auth, payment, and sensitive-data findings were escalated to the `security-auditor` agent.
- [ ] The conclusion states approve or request changes, and names the blockers.
- [ ] For a remote pull request reviewed in a worktree, the user was asked about removing it.
