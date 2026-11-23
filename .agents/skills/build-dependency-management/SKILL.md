---
name: build-dependency-management
description: 'Build files and dependency versions: one catalog, BOM imports, lock files, admission rules. Use when the user says "add this dependency" or "centralise our versions". Not for Java style, use `java-coding-standards`.'
license: Apache-2.0
metadata:
  version: "1.1.0"
---

# Build and Dependency Management

How a project declares versions, shares build logic, and admits new dependencies. The cross-cutting principles hub is the `coding-standards` skill, and this skill is the build-layer detail underneath it.

---

### When not to activate

- Writing the Java inside the modules, use `java-coding-standards`.
- Spring Boot beans, starters and application configuration, and the test libraries, coverage gates and pre-merge pipeline of a Spring Boot project, use `springboot-patterns`.
- The pre-merge build, analysis and scan pipeline outside a Spring Boot project, use `deployment-patterns`.

---

### Rules

1. One version catalog per project, or the manifest and lock pair the language provides. Modules reference catalog aliases, so a bump is one edit. An application pins through a committed lock file. A published library declares the compatible range it is tested against and leaves pinning to the application.
2. Import a bill of materials instead of pinning a family by hand, and declare its members with no version, because one hand-pinned member drifts from the rest over a shared transitive dependency. The BOM coordinate itself lives in the catalog.
3. Share build configuration in one convention plugin, shared build file or parent definition. A build file is code, and the `coding-standards` naming, structure and DRY rules apply to it.
4. Admit dependencies deliberately. Justify each one and ask first, stating purpose, what it replaces and its license. Prefer the standard library and boring libraries. Honor the project's allowed and forbidden lists and license constraints. Review on a schedule with a vulnerability scan. No bot that opens version-bump pull requests unless the owner asks for one, and auto-merge never: a bump is a deliberate, manual pull request, because a stream of automatic bumps gets approved unread. Refuse versions younger than the release-age cooldown and verify hashes from the lock file.
5. Never hand-edit a generated file. Change the input and rerun the generator. Commit output only when consumers cannot run the generator (lock files, generated source, published clients), and then regenerate and diff it in CI. Otherwise generate in the build and ignore the output directory.

---

### Reference files

| Open this | When |
| --- | --- |
| [rules-and-examples.md](references/rules-and-examples.md) | A rule above needs its reasoning or its pass and fail form. |
| [gradle.md](references/gradle.md) | The build is Gradle: `libs.versions.toml`, a platform BOM import, a convention plugin, dependency verification. |
| [package-managers.md](references/package-managers.md) | The project uses pnpm, uv or pip, or someone proposes Dependabot or Renovate: cooldown settings, hash checks, library ranges, bump bots. |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job. |
| [checklist.md](references/checklist.md) | Before calling a build or dependency change done. |
