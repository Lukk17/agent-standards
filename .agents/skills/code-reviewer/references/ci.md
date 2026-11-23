# Standards Checklist: CI, Images and Dependencies

The standards checklist items for a diff that touches a workflow, a composite action, a container image reference or dependency automation. Run them in Step 3, after the items in SKILL.md that every diff gets. Every item names the skill that owns the rule and its reasoning, so a finding can cite it.

---

### CI, images and dependencies

- [ ] Every `uses:` in a workflow or composite action is a full 40-character commit SHA with a `# vX.Y.Z` comment, resolved with `git ls-remote --tags` from the dereferenced `^{}` line. Check a few against the tag rather than trusting them. `deployment-patterns`
- [ ] No `runs-on: ubuntu-latest` or other `-latest` runner label. `deployment-patterns`
- [ ] Every container image, in a Dockerfile, a compose file, a `${VAR:-default}`, a CI `services:` block or a test, is an exact version tag plus `@sha256:` digest, and no release publishes or consumes `:latest`. `docker-patterns`
- [ ] No Dependabot version updates, Renovate configuration or other bump bot was added, unless the owner asked for it. `build-dependency-management`
