# Gradle

The Gradle form of the build and dependency rules in SKILL.md, with pass and fail code. The reasoning behind each rule is in [rules-and-examples.md](rules-and-examples.md).

---

### Version catalog

A Gradle project keeps its one version catalog in `libs.versions.toml`.

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

Fail: the version string is typed into the module, so the next bump has to find every copy, and the processor has already drifted away from the library it generates against.

```kotlin
dependencies {
    implementation("org.mapstruct:mapstruct:1.6.3")
    annotationProcessor("org.mapstruct:mapstruct-processor:1.6.2")
}
```

---

### Bill of materials

Pass: import the BOM with `platform(...)`, name the members without versions.

```kotlin
dependencies {
    implementation(platform(libs.jackson.bom))
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")
    implementation("com.fasterxml.jackson.module:jackson-module-parameter-names")
}
```

Fail: three members of one family pinned separately, and the databind artifact has already drifted ahead of the other two.

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

### Shared build logic

The shared build configuration of a Gradle project is one convention plugin that sets the toolchain, the compiler arguments, and the test framework, and each module applies it.

---

### Hash verification

Verify artifact hashes with Gradle dependency verification, so the artifact installed is the one that was reviewed.
