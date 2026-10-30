---
name: java-coding-standards
description: "Java language standards for Spring Boot services, covering naming, Lombok and constructor injection, records, Optional, streams, exceptions, generics, null safety, SLF4J logging and Javadoc. Use when the user says \"review this Java class\" or \"should this be a record\", or asks to set up Checkstyle and SpotBugs. Not for Spring Boot wiring and REST structure, use `springboot-patterns`."
license: Apache-2.0
---

# Java Coding Standards

How Java itself is written in a Spring Boot service, from naming through to Javadoc. Written for Java 25, with Java 21 as the minimum, so records, sealed types, pattern matching, and virtual threads are all available and expected.

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

### Rules

1. Types are PascalCase, methods and fields camelCase, constants UPPER_SNAKE_CASE, booleans start with `is`, `has` or `can`, and a method name is a verb phrase specific enough to skip the body.
2. Inject through the constructor with `@RequiredArgsConstructor` and take the logger from `@Slf4j`, never an `@Autowired` field. `@Builder` only for complex construction, `@Value` for value objects, `@Getter` or `@Setter` only where neither a record nor `@Value` fits.
3. Records for data, final fields elsewhere, and no setter that exists only because a framework once needed one.
4. `Optional` is a return type for a lookup that can find nothing, never a field, parameter or element. Map it and end with `orElseThrow`, never `.isPresent()` then `.get()`.
5. Keep stream pipelines short, and extract a long pipeline or a multi-line lambda into a named private method.
6. One public top-level type per file, members ordered constants, fields, constructors, public, protected, private, short methods, imports instead of qualified names, indentation matching the project.
7. Prefer an explicit type over `var`, except where the right-hand side already names the type.
8. Domain errors are named unchecked exceptions, technical ones are wrapped with context, and one `@ControllerAdvice` turns them into responses, so business methods hold no try-catch.
9. No raw types, and bound a type parameter when a utility needs a capability from it.
10. Annotate public signatures with `@NonNull` and `@Nullable` from JSpecify or `jakarta.annotation`, enforce them with NullAway or the JSpecify processor in CI, and stop nulls at the edge with Bean Validation.
11. Log through the SLF4J API with a stable message key and `{}` parameters, never concatenation and never a Logback or Log4j2 import. `ERROR` unhandled, `WARN` recoverable, `INFO` domain events, `DEBUG` diagnostics.

---

### Javadoc

Javadoc follows the Doc Comments rules in `coding-standards`. Java delta: write `@throws` for every unchecked exception a caller can act on, because unchecked exceptions never appear in the signature, and give a declared checked exception a `@throws` line only when it names the condition.

---

### Reference material

| Open this | When |
| --- | --- |
| [references/core-rules.md](references/core-rules.md) | A hub rule needs its Pass and Fail example or its full reasoning. |
| [references/concurrency.md](references/concurrency.md) | Virtual threads, executors, `CompletableFuture` composition, and thread-safety documentation. |
| [references/serialization-and-config.md](references/serialization-and-config.md) | Jackson setup, typed `@ConfigurationProperties`, and entity to DTO mapping. |
| [references/static-analysis.md](references/static-analysis.md) | Checkstyle, SpotBugs, and PMD wiring, and keeping build output readable. |
| [references/project-layout.md](references/project-layout.md) | Package structure for a layered project, and the code smells to fix on sight. |

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `springboot-patterns` | Spring Boot structure, REST contracts, security, JPA, tests, and the analysis pipeline. |
| `build-dependency-management` | Version catalog and BOM discipline for the plugins above. |
| `hexagonal-architecture` | Ports and adapters layering when the project uses it. |
| `observability-and-logging` | Structured log output, metrics, and tracing. |
| `coding-standards` | The cross-language principles this skill applies to Java. |

---

### Checklist

- [ ] Names say what the thing is, and booleans read as questions.
- [ ] Every dependency arrives through the constructor, and no field carries `@Autowired`.
- [ ] Data types are records or final-field classes, with no setter that nothing needs.
- [ ] `Optional` appears only as a return type, and never after `.isPresent()` plus `.get()`.
- [ ] Stream pipelines are short, or extracted into named methods.
- [ ] Explicit types instead of `var`, except where the right-hand side already names the type.
- [ ] Domain exceptions are unchecked, named, and handled in one `@ControllerAdvice`.
- [ ] No raw types anywhere.
- [ ] Nullability annotations are present on public signatures and enforced in CI.
- [ ] Logging goes through `@Slf4j` with parameterised messages, never concatenation.
- [ ] Javadoc follows the `coding-standards` Doc Comments rules, with `@throws` on every unchecked exception a caller can act on.
