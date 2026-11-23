# Team Policy on GitHub

Where GitHub reads the files the team policy asks for. Open this when the repository is hosted on GitHub. The policy itself is in [team-policy.md](team-policy.md), and operating the repository on GitHub, with issues, pull requests, CI and releases, belongs to `github-ops`.

---

### Pull request template

GitHub fills a new pull request from `.github/PULL_REQUEST_TEMPLATE.md`, so every repository must have that file. Its content is under Pull Request Template in [team-policy.md](team-policy.md#pull-request-template).

---

### Code ownership

GitHub reads path-based ownership from `.github/CODEOWNERS`:

```
# .github/CODEOWNERS
/packages/auth/   @team-security
/apps/frontend/   @team-frontend
/infra/           @team-platform
```
