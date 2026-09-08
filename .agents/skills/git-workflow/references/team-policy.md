# Team Git Policy

Policy a team adopts once and applies across every repository: commit signing, secret scanning, the pull request
template, review turnaround, merge strategy, changelog generation, large files, branch lifecycle and code ownership.
Load this file when setting up a repository or when a policy question comes up, rather than on every commit.

---

### Commit Signing

All commits and tags must be cryptographically signed. SSH keys are preferred over GPG:

```bash
git config --global commit.gpgsign true
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
# Verify: git log --show-signature
```

---

### Secret Scanning Pre-commit Hook

Install `git-secrets` and configure it as a pre-commit hook to prevent credentials from being committed:

```bash
git secrets --install
git secrets --register-aws  # or custom patterns
```

---

### Pull Request Template

Every repository must have `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## What
<!-- Describe what changed and why -->

## Why
<!-- Link to issue/ticket; explain the motivation -->

## How
<!-- Summarize the technical approach -->

## Testing Done
<!-- What tests were run? What scenarios were verified? -->

## Checklist
- [ ] Tests pass (`CI green`)
- [ ] No new lint warnings
- [ ] Documentation updated if needed
- [ ] Migration scripts reviewed (if DB changes)
```

---

### Code Review Standards

SLA: Reviewers must respond within 1 business day of review request.

Comment prefixes (enforce consistent semantics):
- `blocking:`: must be resolved before merge
- `nit:`: optional style preference, the author may ignore it
- `question:`: seeking understanding, no action required unless the author chooses

Branch protection (required settings):
- Minimum 2 approving reviews before merge
- Dismiss stale reviews when new commits are pushed
- Require branch to be up-to-date with base before merge

---

### Merge Strategy by Scenario

| Scenario | Strategy |
|---|---|
| Feature branch → main | Squash merge, clean history, one commit per feature |
| Hotfix → main | Merge commit (no-FF), preserves hotfix context |
| Release branch → main | Merge commit (no-FF), preserves release history |
| Rebase | Only on local, un-pushed commits, never rewrite shared history |

---

### Automated Changelog

Use `git-cliff` or `conventional-changelog` on every release:

```bash
git-cliff --tag v1.2.0 -o CHANGELOG.md
```

Requires [Conventional Commits](https://www.conventionalcommits.org/) format: `feat:`, `fix:`, `chore:`, `docs:`, etc.

---

### Git LFS

Track binary assets in Git LFS:

```bash
git lfs track "*.png" "*.jpg" "*.gif" "*.mp4" "*.pdf" "*.zip" "*.jar" "*.wasm" "*.fbx" "*.wav" "*.mp3"
git add .gitattributes
```

---

### Branch Lifecycle Policy

- Auto-delete merged branches immediately after merge (enable in GitHub/GitLab settings)
- Stale branch review: any unmerged branch older than 30 days must be reviewed: either rebased and merged, or deleted
- Never leave `WIP`/`draft` branches open indefinitely

---

### Monorepo Configuration

For monorepos:
- Use CODEOWNERS with path-based ownership: `.github/CODEOWNERS`
- Configure path-based CI triggers so only affected packages re-run
- Consider Turborepo, Pants, or Bazel for incremental build graphs

```
# .github/CODEOWNERS
/packages/auth/   @team-security
/apps/frontend/   @team-frontend
/infra/           @team-platform
```
