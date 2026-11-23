# Scope

Companion reference for the [build-dependency-management](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Adding, upgrading, or removing a dependency.
- Setting up or refactoring build files for a new module or project.
- Centralising versions or build configuration across a multi-module repository.
- Reviewing a change that touches build or dependency files.
- The user says "add this dependency", "set up the Gradle build", "centralise our versions", "import the Spring Boot BOM", or "why do two modules use different versions of the same library".

---

### When not to activate

- Writing the Java inside the modules, use `java-coding-standards`.
- Wiring Spring Boot beans, starters, and application configuration, use `springboot-patterns`.
- Test libraries and coverage gates, use `tdd-workflow`, or `springboot-patterns` in a Spring Boot project.
- The pre-merge build, analysis and scan pipeline, use `deployment-patterns`, or `springboot-patterns` in a Spring Boot
  project.

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `coding-standards` | The cross-cutting principles this skill sits under. |
| `java-coding-standards` | Java language style, and the static analysis tools the build runs. |
| `springboot-patterns` | Spring Boot structure and starters, and the pipeline that runs the build and its gates. |
| `tdd-workflow` | Test libraries and coverage gates outside a Spring Boot project. |
| `deployment-patterns` | The CI pipeline that runs the build and its gates outside a Spring Boot project. |
