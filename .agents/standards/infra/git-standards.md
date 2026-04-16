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