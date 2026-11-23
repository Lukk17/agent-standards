# Scope

Companion reference for the [java-coding-standards](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing Java in a Spring Boot project.
- The user says "review this Java class", "should this be a record", "is this Optional usage correct", "rename these methods properly", or "set up Checkstyle and SpotBugs".
- Deciding between a record, a class, and a sealed hierarchy.
- Enforcing naming, immutability, or exception conventions in review.
- Reviewing use of `Optional`, streams, or generics.
- Structuring packages, or setting up the static analysis that guards this style.

---

### When not to activate

- Spring Boot structure, controllers, DTO contracts, and bean wiring, use `springboot-patterns`.
- Entity mapping, queries, transaction boundaries, and security wiring, use `springboot-patterns`.
- Writing the tests, and running the analysis pipeline before a pull request, use `springboot-patterns`.
- Version catalogs, BOM imports, and dependency admission, use `build-dependency-management`.
- Ports and adapters layering across a service, use `hexagonal-architecture`.

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `springboot-patterns` | Spring Boot structure, REST contracts, security, JPA, tests, and the analysis pipeline. |
| `build-dependency-management` | Version catalog and BOM discipline for the static analysis plugins. |
| `hexagonal-architecture` | Ports and adapters layering when the project uses it. |
| `observability-and-logging` | Structured log output, metrics, and tracing. |
| `coding-standards` | The cross-language principles this skill applies to Java. |
