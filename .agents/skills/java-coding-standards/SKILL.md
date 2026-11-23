---
name: java-coding-standards
description: 'Java standards for naming, records, Optional, streams, exceptions and nulls. Use when the user says "review this Java class" or "should this be a record". Not for Spring Boot wiring, use `springboot-patterns`.'
license: Apache-2.0
metadata:
  version: "1.1.0"
---

# Java Coding Standards

How Java itself is written, from naming through to Javadoc. Written for Java 25, with Java 21 as the minimum, so records, sealed types, pattern matching, and virtual threads are all available and expected.

---

### When not to activate

- Spring Boot structure, controllers, DTO contracts, bean wiring, entity mapping, queries, transactions, security wiring and tests, use `springboot-patterns`.
- Version catalogs, BOM imports, and dependency admission, use `build-dependency-management`.
- Ports and adapters layering across a service, use `hexagonal-architecture`.

---

### Rules

1. Types are PascalCase, methods and fields camelCase, constants UPPER_SNAKE_CASE, booleans start with `is`, `has` or `can`, and a method name is a verb phrase specific enough to skip the body. No cryptic abbreviation, and a bucketed concept is an enum.
2. Inject every dependency through the constructor into a final field, never straight into the field.
3. Records for data, final fields elsewhere, and no setter that exists only because a framework once needed one.
4. `Optional` is a return type for a lookup that can find nothing, never a field, parameter or element. Map it and end with `orElseThrow`, never `.isPresent()` then `.get()`.
5. Keep stream pipelines short, and extract a long pipeline or a multi-line lambda into a named private method.
6. One top-level type per file, none nested in a production class, each under a `dto`, `model` or `exception` subpackage. Members ordered constants, fields, constructors, public, protected, private. Imports instead of qualified names. A class past about 300 lines is split by responsibility, per `coding-standards`.
7. Prefer an explicit type over `var`, except where the right-hand side already names the type.
8. Domain errors are named unchecked exceptions, technical ones are wrapped with context, and one central handler turns them into responses, so business methods hold no try-catch.
9. No raw types, and bound a type parameter when a utility needs a capability from it.
10. Annotate public signatures with `@NonNull` and `@Nullable`, enforce them in CI with NullAway or the JSpecify processor, and stop nulls at the edge with Bean Validation.
11. Log through the SLF4J API with a stable message key and `{}` parameters, never concatenation and never a Logback or Log4j2 import.
12. No tunable literal in code. A tunable, such as a timeout or a business maximum, comes from validated configuration, because a value in code needs a release to change. Only algorithm and protocol constants stay.
13. A `Set` for membership or uniqueness, a `List` only when order matters, because the declared type is the contract.
14. One shared blank check, never a hand-rolled `s == null || s.isBlank()`, because the copies drift.
15. Javadoc follows the Doc Comments rules in `coding-standards`, plus `@throws` for every unchecked exception a caller can act on, and for a checked one only when it names the condition.

---

### Reference material

| Open this | When |
| --- | --- |
| [core-rules.md](references/core-rules.md) | A rule above needs its Pass and Fail example, its full reasoning, the log levels or the Javadoc delta. |
| [spring-and-lombok.md](references/spring-and-lombok.md) | The code uses Spring or Lombok: injection, logging, the advice, typed configuration, which literals are tunables, the blank check. |
| [concurrency.md](references/concurrency.md) | Virtual threads, executors, `CompletableFuture`, thread-safety documentation. |
| [jackson.md](references/jackson.md) | Jackson setup, or a JSON field that is not binding. |
| [mapstruct.md](references/mapstruct.md) | Entity to DTO mapping. |
| [static-analysis.md](references/static-analysis.md) | Checkstyle, SpotBugs, and PMD wiring, and keeping build output readable. |
| [project-layout.md](references/project-layout.md) | Package structure for a layered project, and the code smells to fix on sight. |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job. |
| [checklist.md](references/checklist.md) | Before calling a Java change or a Java review done. |
