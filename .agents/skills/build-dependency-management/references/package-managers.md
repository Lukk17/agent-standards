# Package Managers and Bump Bots

The setting each package manager and each bump bot gives for the dependency admission rule in SKILL.md: the release-age cooldown, the hash check, the range a library declares, and the bots that open bump pull requests. The reasoning behind the rule is in [rules-and-examples.md](rules-and-examples.md).

---

### pnpm

Refuse versions younger than the release-age cooldown with pnpm `minimumReleaseAge`, so a freshly published malicious version has time to be caught before it reaches the build.

---

### uv

The release-age cooldown in uv is `exclude-newer`.

---

### pip and Python packaging

Verify artifact hashes from the lock file with `pip --require-hashes`, so the artifact installed is the one that was reviewed.

A published library declares a range and leaves pinning to the application. The PyPA guidance says the same of `install_requires`: pinning there "is overly-restrictive, and prevents the user from gaining the benefit of dependency upgrades".

---

### Dependabot and Renovate

Do not add a `.github/dependabot.yml` with version updates, a Renovate configuration or any other bot that opens bump pull requests, unless the project owner explicitly asks for one, and never enable auto-merge. Reading security alerts, such as Dependabot alerts, is a separate matter and stays on: an alert names a vulnerable version, and the fix still lands as a manual bump.

Fail: a `dependabot.yml` with `package-ecosystem: npm`, `github-actions` and `docker` on a weekly schedule, opening a dozen pull requests a week that are merged on a green check.

Where the owner did ask for Renovate, its release-age cooldown is `minimumReleaseAge`.
