# Rules and Examples

Contents:

- [One version catalog per project](#one-version-catalog-per-project)
- [Import a bill of materials instead of pinning a family by hand](#import-a-bill-of-materials-instead-of-pinning-a-family-by-hand)
- [Share build configuration](#share-build-configuration)
- [Admit dependencies deliberately](#admit-dependencies-deliberately)
- [Never hand-edit a generated file](#never-hand-edit-a-generated-file)

Each build and dependency rule in SKILL.md in full, with its reasoning, the PyPA quote on library pinning, and the catalog, BOM and Gradle pass and fail forms. Load this file when applying a rule and the one-line summary in SKILL.md is not enough.

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
