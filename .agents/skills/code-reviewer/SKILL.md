---
name: code-reviewer
description: 'Structured review of local changes or a remote pull request across correctness, maintainability, doc comments, efficiency, security, error handling and tests, with every finding led by a path:line reference. Use when the user says "review my changes", "review PR #123", or "is this branch ready to merge". Not for hunting duplicated or reinvented code, use `review-duplication`.'
---

# Code Reviewer

Conduct a professional review of a change set, whether it lives in the working tree or in a remote pull request. Review
against the `coding-standards` hub for the shared floor, pull in `review-duplication` for reuse and `security-review`
for security, and lead every finding with a `path:line` reference.

| Task | Open |
|---|---|
| Running a step in full: the commands, the fork rule and its source, the pillar questions, the report shape, pass and fail forms | [review-steps.md](references/review-steps.md) |

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

A pull request named by number or URL is remote, anything else is the local working tree, staged and unstaged. Read a remote one with `gh pr diff <PR_NUMBER>` and `gh pr view <PR_NUMBER> --comments`, without checking it out. When the full tree is needed, `git worktree add --detach ../review-pr-<PR_NUMBER>` and run `gh pr checkout` inside it, never over the user's branch. Read local changes with `git status`, `git diff` and `git diff --staged`.

---

### Step 2: run the project's verification first

Run the verification command the project's AGENTS.md documents before reading a line, and say so when it documents none rather than guessing. On a small local change, ask the user first. A pull request from a fork or an outside author is untrusted input: ask before running anything from it, only inside the worktree, never with production credentials.

---

### Step 3: analyse against the review pillars

Cite `path:line` for every finding across correctness, maintainability, readability, doc comments (the `coding-standards` "Doc Comments" rule plus the language delta), efficiency, security, styling (against `design-system` when styling changes), edge cases and error handling, and testability.

---

### Step 4: escalate the sensitive findings

Hand authentication, authorisation, payment and personal-data findings to the `security-auditor` agent before merge, and say so in the review, with severity and location named rather than buried as a nitpick.

---

### Step 5: report

Summary with the verdict in two or three sentences, findings grouped Critical, Improvements and Nitpicks, then a conclusion of approve or request changes with the blockers named. Explain each request, name what the change got right, and for a worktree review ask the user about `git worktree remove`.

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
