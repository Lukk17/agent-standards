# Practice Examples

Contents:

- [Pick one branching strategy and hold to it](#pick-one-branching-strategy-and-hold-to-it)
- [Write conventional commit messages](#write-conventional-commit-messages)
- [Merge in public, rebase in private](#merge-in-public-rebase-in-private)
- [Name branches by type and subject](#name-branches-by-type-and-subject)
- [Delete a branch once it has merged](#delete-a-branch-once-it-has-merged)
- [Put what, why, how and testing in every pull request](#put-what-why-how-and-testing-in-every-pull-request)
- [Write the description short and human](#write-the-description-short-and-human)
- [Drafts and posting](#drafts-and-posting)
- [Prevent conflicts rather than resolving them](#prevent-conflicts-rather-than-resolving-them)
- [Stage only what you changed](#stage-only-what-you-changed)
- [Never rewrite public history, and never push unasked](#never-rewrite-public-history-and-never-push-unasked)
- [Release management lives in github-ops](#release-management-lives-in-github-ops)
- [Anti-patterns](#anti-patterns)

Companion reference for the [git-workflow](../SKILL.md) skill. Load it for the reasoning and the pass and fail examples behind each rule: the branching strategy, commit messages, merge versus rebase, branch names and cleanup, pull request content, conflict prevention, staging, public history and where releases live.

---

### Pick one branching strategy and hold to it

GitHub Flow suits continuous deployment and most small to medium teams: `main` stays deployable, work happens on a
branch, and a reviewed branch merges and deploys. Trunk-based suits an experienced team with strong CI and feature
flags, where branches live a day or two at most. GitFlow suits scheduled releases in a regulated setting and pays for
that with a second long-lived branch. Full shape and rules per strategy are in
[branching-strategies.md](branching-strategies.md).

Pass:

```text
GitHub Flow. main protected and always deployable. Branch, PR, review, merge, deploy.
```

Fail:

```text
Mostly GitHub Flow but we also keep a develop branch, and hotfixes go straight to main sometimes.
```

---

### Write conventional commit messages

Use type, optional scope, then a subject in the imperative with no trailing period. Types: feat, fix, docs, style,
refactor, test, chore, perf, ci, revert. The body explains why rather than what, because the diff already shows what.
Keep the subject under about fifty characters and put the issue reference in the footer.

Pass:

```text
fix(api): retry requests on 503 Service Unavailable

The upstream API returns 503 during peak hours. Added exponential backoff with a maximum of three attempts.

Closes #123
```

Fail:

```text
fixed stuff
```

A repository-level template makes the format the default rather than a thing to remember. The template and the config
line that enables it are in [git-config.md](git-config.md).

---

### Merge in public, rebase in private

Merge preserves the true history and is the safe default for anything others have pulled. Rebase produces a linear
history and is for a branch only you have. Never rebase a branch that others have based work on, that is already
merged, or that is shared, because rewriting it invalidates everyone else's copy and the recovery is manual.

Pass:

```bash
git rebase main
```

Fail:

```bash
git push --force origin main
```

The rebase run itself, conflict handling during it, and the safe force-push variant are in
[recipes.md](recipes.md).

---

### Name branches by type and subject

Use a type prefix, a slash, then a short hyphenated subject: `feature/user-auth`, `fix/login-redirect-loop`,
`hotfix/token-refresh-crash`, `release/<version>`, `experiment/new-caching-strategy`. Keep the subject descriptive
enough that the branch list reads without opening anything, and put the issue key in it when the project tracks one.

Pass:

```text
feature/PROJ-1234-order-cancellation
```

Fail:

```text
lukas-branch-2
```

---

### Delete a branch once it has merged

A branch list that still holds every merged branch stops being usable, and stale remote-tracking references make it
worse. Prune after every merge, locally and on the remote.

Pass:

```bash
git branch --merged main | grep -v "^\*\|main" | xargs -n 1 git branch -d
```

Fail:

```text
Left 60 merged branches on the remote because deleting them felt risky.
```

---

### Put what, why, how and testing in every pull request

A pull request description answers four things: what changed, why it was needed, how it was done where that is not
obvious, and how it was tested. Keep the change to one feature or one fix, and under about five hundred lines, so a
reviewer can actually hold it in their head. Self-review before requesting review, and make sure CI is green first.

Pass:

```text
What: cancel an order from the order detail page.
Why: support currently cancels by hand in the database. Closes #482.
How: new endpoint plus a state transition guard on paid orders.
Testing: unit tests on the guard, integration test on the endpoint, manual pass on staging.
```

Fail:

```text
See commits.
```

The full description template, the reviewer checklist and the review turnaround policy are in
[team-policy.md](team-policy.md).

---

### Write the description short and human

A description is read by a person deciding whether to review now. Keep it short, make sure it does not read as written by an AI, and link the related open issues. Name no commit hash and do not walk through many files, because the commit list and the diff already show both. An integration pull request lists the other pull requests it contains, and not the commits added without a pull request.

Pass:

```text
Cancel an order from the order detail page, because support cancels by hand in the database today. Closes #482, related to #470.
Testing: unit tests on the guard, integration test on the endpoint.
```

Fail:

```text
This comprehensive PR introduces a robust cancellation flow. Changes in 3f9c2ab:
- OrderController.java: added endpoint
- OrderService.java: added guard
- OrderRepository.java: added query
- order-detail.component.ts: added button
```

Pass, for an integration pull request:

```text
Release integration for the sprint. Contains #501, #503 and #507.
```

Fail, for an integration pull request:

```text
Contains #501, #503, plus commits a1b2c3d and e4f5a6b that went straight to the branch.
```

---

### Drafts and posting

Every description draft is printed in full in the chat, numbered, so the user can approve or change it by its number, and never stored in a file, because a file outlives the session and reads as project truth. Nothing is posted until the user approves it. The description carries no trace of an agent or tool, no commit hash, no placeholder such as `#XXX`, and no em dash, en dash, semicolon joining two clauses, bold or italic.

---

### Prevent conflicts rather than resolving them

Most conflicts come from a branch living too long next to a file everybody edits. Keep branches small and short,
rebase onto the main line often, tell the team before touching a shared file, use a feature flag instead of a
long-lived branch, and merge reviewed work promptly. When a conflict does happen, read both sides before picking one,
never accept a side just to make the markers go away, and run the tests after resolving.

Pass:

```text
Branch is two days old, rebased onto main this morning, touches four files nobody else has open.
```

Fail:

```text
Branch is six weeks old and the migration index file has conflicted three times.
```

The conflict-resolution commands and the merge-tool options are in [recipes.md](recipes.md).

---

### Stage only what you changed

Stage explicit paths, or review each hunk, rather than sweeping the whole tree. A blind stage-everything commits the
scratch file, the local config edit and the debug print alongside the change, and the next reader cannot tell which
lines were the point.

Pass:

```bash
git add -p
```

Fail:

```bash
git add .
```

---

### Never rewrite public history, and never push unasked

Pushing, force-pushing, opening a pull request and rebasing onto a remote all happen only on an explicit instruction.
For a commit already on a shared branch, revert rather than rewrite: a revert is a new commit everyone can pull, and
a rewrite is a break everyone has to repair by hand.

Pass:

```bash
git revert HEAD
```

Fail:

```bash
git rebase -i origin/main
```

---

### Release management lives in github-ops

Semantic versioning, tagging, changelog generation and publishing a release are one procedure, and it lives in
`github-ops` so there is a single place that owns it. Come back here only for the branch and commit conventions the
release process reads from.

---

### Anti-patterns

| Anti-pattern | Cost | Do instead |
|---|---|---|
| Committing straight to the protected branch | No review, no CI gate before the main line moves | Branch, review, merge |
| Committing a secret | Rotation plus a history rewrite across every clone | Ignore the file, read from the environment |
| A pull request over a thousand lines | Review degrades to a skim | Split into focused changes |
| A commit message that says update | The history stops answering why anything happened | Conventional commits with a body |
| Rewriting a public branch | Everyone who pulled has to repair by hand | Revert on a public branch |
| A feature branch alive for weeks | Conflicts compound and integration is deferred | Short branches plus a feature flag |
| Committing generated output a consumer can rebuild | Every regeneration is a diff nobody can review | Ignore the artifact, build it |
| Committing an agent's review findings or scratch notes | A stale document that reads as project truth | Keep it out of the tree, or in the scratch folder the agent was given |
| A committed lock file or generated type file with no `linguist-generated` mark | Every bump buries the real diff under thousands of lines | Mark it in `.gitattributes` |
