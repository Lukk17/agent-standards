---
name: build-dependency-management
description: 'Build files and dependency versions: one version catalog, bill-of-materials imports, shared build logic, lock files, release-age cooldowns, hash verification, and deliberate dependency admission. Use when the user says "add this dependency", "centralise our versions", or "import the Spring Boot BOM". Not for Java language style, use `java-coding-standards`.'
license: Apache-2.0
---

# Build and Dependency Management

How a project declares versions, shares build logic, and admits new dependencies. The cross-cutting principles hub
is the `coding-standards` skill, and this skill is the build-layer detail underneath it.

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

### One version catalog per project

Keep every dependency version in one central place, a single version catalog such as a Gradle `libs.versions.toml`,
or the manifest and lock pair the language provides. A module references a catalog alias, so a bump is one edit in
one file.

Pass: the version lives in the catalog and the module names the alias.

```toml
[versions]
mapstruct = "1.6.3"
resilience4j = "2.3.0"

[libraries]
mapstruct = { module = "org.mapstruct:mapstruct", version.ref = "mapstruct" }
mapstruct-processor = { module = "org.mapstruct:mapstruct-processor", version.ref = "mapstruct" }
resilience4j-spring-boot3 = { module = "io.github.resilience4j:resilience4j-spring-boot3", version.ref = "resilience4j" }
```

```kotlin
dependencies {
    implementation(libs.mapstruct)
    annotationProcessor(libs.mapstruct.processor)
    implementation(libs.resilience4j.spring.boot3)
}
```

Fail: the version string is typed into the module, so the next bump has to find every copy, and the processor has
already drifted away from the library it generates against.

```kotlin
dependencies {
    implementation("org.mapstruct:mapstruct:1.6.3")
    annotationProcessor("org.mapstruct:mapstruct-processor:1.6.2")
}
```

An application pins through a committed lock file, so a clean checkout builds the same artifacts tomorrow. A published
library declares the compatible range it is tested against and leaves pinning to the application, because a library
that pins exact versions forces a resolver conflict on every consumer that needs a different patch. The PyPA guidance
says the same of `install_requires`: pinning there "is overly-restrictive, and prevents the user from gaining the
benefit of dependency upgrades".

---

### Import a bill of materials instead of pinning a family by hand

A bill of materials pins a whole family of libraries to versions their maintainers tested together. Import it and
declare the members with no version at all. Pinning one member by hand is how version-skew bugs start, because the
hand-pinned member and the managed members stop agreeing about a shared transitive dependency.

Pass: import the BOM, name the members without versions.

```kotlin
dependencies {
    implementation(platform(libs.jackson.bom))
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")
    implementation("com.fasterxml.jackson.module:jackson-module-parameter-names")
}
```

Fail: three members of one family pinned separately, and the databind artifact has already drifted ahead of the
other two.

```kotlin
dependencies {
    implementation("com.fasterxml.jackson.core:jackson-databind:2.20.0")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310:2.18.2")
    implementation("com.fasterxml.jackson.module:jackson-module-parameter-names:2.18.2")
}
```

The BOM coordinate itself is a version like any other, so it belongs in the catalog too.

```toml
[libraries]
jackson-bom = { module = "com.fasterxml.jackson:jackson-bom", version.ref = "jackson" }
```

---

### Share build configuration

Put common build configuration in one place, a convention plugin, a shared build file, or a parent definition,
rather than repeating it in every module. Module build files drift exactly the way duplicated code drifts.

Pass: one convention plugin sets the toolchain, the compiler arguments, and the test framework, and each module
applies it.

Fail: eight module build files each set the same toolchain, and two of them are a release behind.

A build file is code. The naming, structure, and DRY rules in `coding-standards` apply to it.

---

### Admit dependencies deliberately

Justify every new dependency before adding it, and ask first. A dependency is a permanent maintenance and security
liability rather than a free function. Prefer the standard library and boring, well-understood libraries over
novelty, because the exciting library is the one abandoned in two years.

Pass: the pull request says what the dependency does, what it replaces, and what its license is.

Fail: a utility library appears in the diff with no mention in the description.

Honor any explicit list of allowed or forbidden libraries for the project, including license constraints such as
forbidding copyleft licenses in distributed code. Review and update dependencies on a schedule with a vulnerability
scan. Automated update pull requests are allowed once approved, auto-merge never is.

Refuse versions younger than the package manager's release-age cooldown (pnpm `minimumReleaseAge`, Renovate
`minimumReleaseAge`, uv `exclude-newer`), so a freshly published malicious version has time to be caught before it
reaches the build. Verify artifact hashes from the lock file (`pip --require-hashes`, Gradle dependency verification),
so the artifact installed is the one that was reviewed.

---

### Never hand-edit a generated file

Never hand-edit a generated file. Change the input and rerun the generator. Commit the output only when consumers
cannot run the generator (lock files, `go generate` output, published clients), and gate it in CI by regenerating and
diffing. Everything else is generated in the build and its output directory is ignored.

Pass: the generator runs in the build and its output directory is ignored, or the committed output is regenerated in
CI and the job fails on any diff.

Fail: a generated client is committed, then patched by hand to fix one field.

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
