---
name: build-dependency-management
description: 'Build files and dependency versions: one version catalog, bill-of-materials imports, shared build logic, lock files, release-age cooldowns, hash verification, and deliberate dependency admission. Use when the user says "add this dependency", "centralise our versions", or "import the Spring Boot BOM". Not for Java language style, use `java-coding-standards`.'
license: Apache-2.0
---

# Build and Dependency Management

How a project declares versions, shares build logic, and admits new dependencies. The cross-cutting principles hub
is the `coding-standards` skill, and this skill is the build-layer detail underneath it.

| Task | Open |
|---|---|
| Applying a rule: its reasoning, the PyPA quote, and the catalog, BOM and Gradle pass and fail forms | [rules-and-examples.md](references/rules-and-examples.md) |

---

### When to activate

- Adding, upgrading, or removing a dependency.
- Setting up or refactoring build files for a new module or project.
- Centralising versions or build configuration across a multi-module repository.
- Reviewing a change that touches build or dependency files.
- The user says "add this dependency", "set up the Gradle build", "centralise our versions", "import the Spring Boot
  BOM", or "why do two modules use different versions of the same library".

---

### When not to activate

- Writing the Java inside the modules, use `java-coding-standards`.
- Wiring Spring Boot beans, starters, and application configuration, use `springboot-patterns`.
- Test libraries and coverage gates, use `tdd-workflow`, or `springboot-patterns` in a Spring Boot project.
- The pre-merge build, analysis and scan pipeline, use `deployment-patterns`, or `springboot-patterns` in a Spring Boot
  project.

---

### Rules

1. One version catalog per project, such as a Gradle `libs.versions.toml` or the language's manifest and lock pair. Modules reference catalog aliases, so a bump is one edit. An application pins through a committed lock file; a published library declares the compatible range it is tested against and leaves pinning to the application.
2. Import a bill of materials instead of pinning a family by hand, and declare its members with no version, because one hand-pinned member drifts from the rest over a shared transitive dependency. The BOM coordinate itself lives in the catalog.
3. Share build configuration in one convention plugin, shared build file or parent definition. A build file is code, and the `coding-standards` naming, structure and DRY rules apply to it.
4. Admit dependencies deliberately. Justify each one and ask first, stating purpose, what it replaces and its license. Prefer the standard library and boring libraries. Honor the project's allowed and forbidden lists and license constraints. Review on a schedule with a vulnerability scan; approved automated update pull requests are fine, auto-merge never. Refuse versions younger than the release-age cooldown (pnpm and Renovate `minimumReleaseAge`, uv `exclude-newer`) and verify hashes from the lock file (`pip --require-hashes`, Gradle dependency verification).
5. Never hand-edit a generated file. Change the input and rerun the generator. Commit output only when consumers cannot run the generator (lock files, `go generate` output, published clients), and then regenerate and diff it in CI; otherwise generate in the build and ignore the output directory.

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `coding-standards` | The cross-cutting principles this skill sits under. |
| `java-coding-standards` | Java language style, and the static analysis tools the build runs. |
| `springboot-patterns` | Spring Boot structure and starters, and the pipeline that runs the build and its gates. |
| `tdd-workflow` | Test libraries and coverage gates outside a Spring Boot project. |
| `deployment-patterns` | The CI pipeline that runs the build and its gates outside a Spring Boot project. |

---

### Checklist

- [ ] Every version lives in one catalog, and no module hardcodes a version string.
- [ ] Every managed family comes from an imported bill of materials, with no member pinned by hand.
- [ ] An application commits its lock file and builds reproducibly from a clean checkout, a library declares ranges.
- [ ] New versions wait out a release-age cooldown, and installs verify hashes from the lock file.
- [ ] Shared build configuration lives in one convention plugin or parent definition.
- [ ] Each new dependency has a stated purpose, a license check, and prior approval.
- [ ] No generated file is hand-edited, and any committed generated output is regenerated and diffed in CI.
