### AI Git and Version Control Standards

---

### Core Execution Directives

- Treat all LLM generated Git commands, branching logic, and commit messages as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every repository operation.
- Append a Zero-Trust directive demanding mandatory web searches for current Git documentation and platform-specific CLI tooling.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every CLI flag, merge strategy, and Git hook configuration provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### Commit Message Formatting

- Enforce the Conventional Commits specification for all repository changes to enable automated SemVer versioning and changelog generation. [Confidence: 100%]
  - Link: https://www.conventionalcommits.org/en/v1.0.0/
  - Quote: "is"
- Prefix every commit message strictly with a structural type: feat, fix, chore, docs, style, refactor, perf, or test. [Confidence: 100%]
- Require an empty line between the short commit description and the detailed body. [Confidence: 100%]
- Explicitly denote breaking changes by appending an exclamation mark before the colon in the type prefix or by starting the footer with BREAKING CHANGE:. [Confidence: 100%]

---

### Branching and Integration Logic

- Mandate the use of short-lived feature branches cut directly from the main or master branch. [Confidence: 100%]
- Require the agent to keep feature branches up to date using git rebase instead of git merge. This prevents merge commits from polluting the history when catching up with upstream changes. [Confidence: 100%]
  - Link: https://git-scm.com/docs/git-rebase
  - Quote: "commits"
- Prohibit the use of git push --force on shared integration branches. Require git push --force-with-lease when pushing a locally rebased feature branch to a remote. [Confidence: 100%]
- Squash feature branch commits into a single cohesive commit when merging the pull request into the main integration branch. [Confidence: 100%]

---

### Security and Commit Verification

- Require cryptographically verified signatures for all commits and tags pushed to remote repositories. [Confidence: 100%]
  - Link: https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification
  - Quote: "S/MIME,"
- Prefer SSH keys for signing commits over legacy GPG keys due to simpler generation and management workflows. [Confidence: 100%]
- Configure Git to sign all commits automatically by setting commit.gpgsign to true globally. [Confidence: 100%]
- Instruct the agent to avoid checking in sensitive data by validating changes against a strict .gitignore file and running a pre-commit hook like git-secrets before every commit. [Confidence: 100%]

---

### Branch Protection Rules

- Require a minimum of **two approving reviews** on all PRs targeting `main` / `master`. [Confidence: 100%]
- Require all configured CI status checks to pass before merging.
- Prevent direct pushes to `main` / `master`; all changes must go through a pull request.
- Require branches to be up to date before merging (no merging stale branches).
- Enable "Dismiss stale reviews" so that new commits invalidate existing approvals.

---

### Pull Request Template

Every repository must include a `.github/PULL_REQUEST_TEMPLATE.md` (or GitLab equivalent) with the following mandatory sections:

```markdown
## What
<!-- A concise description of what this PR does. -->

## Why
<!-- The motivation, linked issue, or business requirement. -->

## How
<!-- Key implementation decisions or non-obvious choices. -->

## Testing Done
<!-- How was this tested? Unit tests, integration tests, manual verification steps. -->

## Checklist
- [ ] Tests added / updated
- [ ] Documentation updated (if applicable)
- [ ] No secrets committed
- [ ] Breaking changes documented
```

---

### Code Review Standards

- Reviews must verify: correctness, test coverage, standards compliance, security, and performance impact — not only style. [Confidence: 100%]
- Review SLA: reviewers must respond within **1 business day** of being assigned.
- A comment marked `blocking:` must be resolved and re-approved before merge.
- A comment marked `nit:` is non-blocking; the author may address it at their discretion.
- The PR author must never self-merge; at least one external approval is always required.

---

### Merge Strategy

| Scenario | Strategy | Reason |
|---|---|---|
| Feature branch → main | **Squash merge** | Clean linear history on main |
| Hotfix → main | **Merge commit (no-FF)** | Preserves hotfix context |
| Dependency update | **Squash merge** | Single commit per update |
| Release branch → main | **Merge commit (no-FF)** | Marks the release point |

---

### Release Process

- Tag every production release with a SemVer tag: `v1.2.3`. [Confidence: 100%]
- Generate a changelog automatically from Conventional Commits using **git-cliff** or **conventional-changelog**.
- Create a GitHub/GitLab Release for every tag with the generated changelog and attached artefacts (binaries, SBOMs).
- Never delete or reuse a release tag; if a release is bad, create a patch release.

---

### Git LFS

- Track all binary files > 1 MB with Git LFS to prevent repository size bloat. [Confidence: 100%]
- Standard tracked extensions: `*.png`, `*.jpg`, `*.gif`, `*.mp4`, `*.pdf`, `*.zip`, `*.jar`, `*.wasm`, `*.fbx`, `*.wav`, `*.mp3`.
- Document the LFS configuration in the repository `README.md` and include `git lfs install` in the project setup guide.

---

### Stale Branch Cleanup

- Automatically delete branches after they are merged into `main` (enable in GitHub/GitLab repository settings). [Confidence: 100%]
- Any branch not updated in **30 days** and not merged should be deleted or tagged for archival.
- Do not accumulate long-lived branches for ongoing work; use feature flags and short-lived branches instead.

---

### Monorepo Handling

- Use **CODEOWNERS** to assign review responsibility to sub-directory owners; CODEOWNERS approval is required for changes in owned paths. [Confidence: 100%]
- Configure path-based CI triggers so that only the affected packages/services run their pipelines on a given PR.
- Use `pnpm workspaces` (JS), Gradle multi-project builds (Java), or Pants/Bazel for large monorepos requiring selective builds and tests.