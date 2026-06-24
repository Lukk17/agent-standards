---
name: build-dependency-management
description: Build configuration and dependency management discipline. One central version catalog per project, bill-of-materials driven versions, shared build config, justified dependencies, and reproducible locked installs. Use when adding a dependency, setting up or refactoring build files, or managing versions across a multi-module project.
---

# Build and Dependency Management

How a project declares versions, shares build logic, and admits new dependencies. The cross-cutting principles hub is
the `coding-standards` skill; this skill is the build-layer detail.

---

### When to activate

- Adding, upgrading, or removing a dependency.
- Setting up or refactoring build files for a new module or project.
- Centralising versions or build configuration across a multi-module repository.
- Reviewing a change that touches build or dependency files.

---

### One version catalog per project

- Keep all dependency versions in one central place: a single version catalog in a TOML file (for example a Gradle
  `libs.versions.toml`, or the equivalent lock and manifest pair for the language).
- Never hardcode a version string inside an individual module. A module references the catalog entry; the version
  lives in one place so a bump is one edit.
- Pin versions so installs are reproducible. Commit the lockfile. An unpinned range turns a clean checkout into a
  different build tomorrow.

---

### Lean on a bill of materials

- Manage versions through a bill of materials wherever one exists, and import it rather than pinning the versions it
  already governs.
- Lean on a bill of materials as much as possible so a whole family of libraries moves together and stays mutually
  compatible. Pinning one member of a managed family by hand is how version-skew bugs start.

---

### Share build configuration

- Share common build configuration in one place (a convention plugin, a shared build file, a parent definition)
  rather than repeating it in every module. Repetition across module build files drifts the same way duplicated code
  does.
- Keep the build itself readable. A build file is code; the naming, structure, and DRY rules apply to it too.

---

### Admit dependencies deliberately

- Justify every new dependency before adding it, and ask first. A dependency is a permanent maintenance and security
  liability, not a free function.
- Prefer the standard library and boring, well-understood dependencies over novelty. The exciting library is the one
  that is abandoned in two years.
- Honor any explicit list of allowed or forbidden libraries for the project, including license constraints (for
  example forbidding copyleft licenses in distributed code).
- Review and update dependencies on a schedule, with a vulnerability scan, but never through an automatic trigger.
  Enabling a self-scanning bot or auto-merging a dependency bump is an approval-gated decision, not a default.

---

### Generated sources

Never commit generated sources or build output. Regenerate them from their source, and never hand-edit a generated
file; change the input and run the generator. A generated file checked into version control drifts from its source
the first time someone edits it by hand.
