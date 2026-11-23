# Rules and Examples

Contents:

- [One version catalog per project](#one-version-catalog-per-project)
- [Import a bill of materials instead of pinning a family by hand](#import-a-bill-of-materials-instead-of-pinning-a-family-by-hand)
- [Share build configuration](#share-build-configuration)
- [Admit dependencies deliberately](#admit-dependencies-deliberately)
- [Never hand-edit a generated file](#never-hand-edit-a-generated-file)

Each build and dependency rule in SKILL.md in full, with its reasoning and its pass and fail forms in words. Load this file when applying a rule and the one-line summary in SKILL.md is not enough. The Gradle code for each rule is in [gradle.md](gradle.md), and the pnpm, uv, pip, Dependabot and Renovate settings, with the PyPA quote on library pinning, are in [package-managers.md](package-managers.md).

---

### One version catalog per project

Keep every dependency version in one central place, a single version catalog, or the manifest and lock pair the language provides. A module references a catalog alias, so a bump is one edit in one file.

Pass: the version lives in the catalog and the module names the alias.

Fail: the version string is typed into the module, so the next bump has to find every copy, and a code generator has already drifted away from the library it generates against.

An application pins through a committed lock file, so a clean checkout builds the same artifacts tomorrow. A published library declares the compatible range it is tested against and leaves pinning to the application, because a library that pins exact versions forces a resolver conflict on every consumer that needs a different patch.

---

### Import a bill of materials instead of pinning a family by hand

A bill of materials pins a whole family of libraries to versions their maintainers tested together. Import it and declare the members with no version at all. Pinning one member by hand is how version-skew bugs start, because the hand-pinned member and the managed members stop agreeing about a shared transitive dependency.

Pass: import the BOM, name the members without versions.

Fail: three members of one family pinned separately, and one of them has already drifted ahead of the other two.

The BOM coordinate itself is a version like any other, so it belongs in the catalog too.

---

### Share build configuration

Put common build configuration in one place, a convention plugin, a shared build file, or a parent definition, rather than repeating it in every module. Module build files drift exactly the way duplicated code drifts.

Pass: one convention plugin sets the toolchain, the compiler arguments, and the test framework, and each module applies it.

Fail: eight module build files each set the same toolchain, and two of them are a release behind.

A build file is code. The naming, structure, and DRY rules in `coding-standards` apply to it.

---

### Admit dependencies deliberately

Justify every new dependency before adding it, and ask first. A dependency is a permanent maintenance and security liability rather than a free function. Prefer the standard library and boring, well-understood libraries over novelty, because the exciting library is the one abandoned in two years.

Pass: the pull request says what the dependency does, what it replaces, and what its license is.

Fail: a utility library appears in the diff with no mention in the description.

Honor any explicit list of allowed or forbidden libraries for the project, including license constraints such as forbidding copyleft licenses in distributed code. Review and update dependencies on a schedule with a vulnerability scan.

Bumps are manual by default. Do not add a bot that opens bump pull requests, unless the project owner explicitly asks for one, and never enable auto-merge. A bump is a deliberate pull request that names what changed and why, re-resolves the lock file, the action SHA or the image digest together with its tag, and runs the full suite. Reading security alerts is a separate matter and stays on: an alert names a vulnerable version, and the fix still lands as a manual bump.

Refuse versions younger than the package manager's release-age cooldown, so a freshly published malicious version has time to be caught before it reaches the build. Verify artifact hashes from the lock file, so the artifact installed is the one that was reviewed.

---

### Never hand-edit a generated file

Never hand-edit a generated file. Change the input and rerun the generator. Commit the output only when consumers cannot run the generator (lock files, `go generate` output, published clients), and gate it in CI by regenerating and diffing. Everything else is generated in the build and its output directory is ignored.

Pass: the generator runs in the build and its output directory is ignored, or the committed output is regenerated in CI and the job fails on any diff.

Fail: a generated client is committed, then patched by hand to fix one field.
