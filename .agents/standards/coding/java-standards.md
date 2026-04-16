# Java Standards

Applies to all Java code. For Spring Boot–specific rules, see `spring-boot-standards.md`. Universal rules in `universal-coding-standards.md` apply in addition to these.

---

## Architecture

Strictly adhere to Hexagonal Architecture:
- Always define the Domain Interface (Port) before implementing the Adapter.
- The domain layer must have zero dependencies on external frameworks (Lombok is the only permitted exception).

---

## Language Features

- Use **Virtual Threads** for all concurrency (Java 21+). Do not use platform threads for I/O-bound work.
- Use **Java Records** for immutable data structures.
- Use **`Optional`** and Stream-like chains instead of null checks and multi-if statements.
  - Prefer `Optional.ofNullable(...).map(...).orElse(...)` chains over `if (x != null)` blocks.
- Use **Stream API** for collection processing; avoid manual loops for transformations and filters.
- Avoid deep nesting via guard clauses and early returns.
- Prefer descriptive object type names over `var`; use `var` only when the type is declared on the same line and is long.
- Never use fully qualified class names in code; use imports.

---

## Lombok

Always use Lombok annotations to eliminate boilerplate:
- `@Slf4j` for logging.
- `@Getter`, `@Setter` where appropriate.
- `@RequiredArgsConstructor` for constructor injection.
- `@Builder` for complex object construction.
- `@Value` for immutable classes (when Record is insufficient).

Prefer annotation-based configuration over manual wiring.

---

## Naming

- Boolean variables and methods must start with `is`, `has`, or `can`.
- Method names must be descriptive verbs: `calculateTotalRevenue`, `findActiveUsers`.
- Constants in `UPPER_SNAKE_CASE`; no magic numbers inline.

---

## Methods

- Public methods must be concise; extract complex logic into private helpers.
- Lambda expressions longer than one line must be extracted to a named private method.
- In lambda bodies, do not use inline multi-line logic; extract it.

---

## Error Handling

- Use global exception handlers (e.g., `@ControllerAdvice` in Spring, or a top-level handler in other contexts).
- No local try-catch blocks scattered across business logic methods.
- Extract complex error-handling logic to dedicated private methods.

---

## Gradle

All Gradle tasks must be run with output redirected to a single file:

```bash
./gradlew <task> > build_log.txt 2>&1
```

This overwrites `build_log.txt` so it always reflects only the most recent execution.

---

## Documentation

Use Javadoc only when strictly necessary to explain a public class's contract. Do not add Javadoc to methods, constructors, or obvious classes.

---

## Testing (Java-Specific)

These rules extend `testing-standards.md`:

- Use JUnit 5.
- Use `@InjectMocks` and `@Mock` (Mockito) instead of manual `@BeforeEach` initialization.
- Extract object creation to helper methods or a shared `TestDataFactory` class.

---

## Logging

- Use **SLF4J** as the logging API in all code; never import a concrete logging framework (Logback, Log4j2) directly in business logic.
- Use **Logback** as the default implementation; switch to Log4j2 only if async appenders or advanced routing are required.
- In production, configure Logback with a JSON encoder (e.g., `logstash-logback-encoder`) to produce structured log output.
- Use `@Slf4j` (Lombok) for logger injection; never instantiate `LoggerFactory.getLogger(...)` manually in annotated classes.
- Log at `ERROR` for unhandled exceptions, `WARN` for recoverable issues, `INFO` for significant domain events, `DEBUG` for diagnostic detail.

---

## Code Quality Tools

Add the following to every Gradle build and fail the build on violations:

- **Checkstyle**: enforce Google Java Style or a project-defined ruleset.
- **SpotBugs**: static bytecode analysis; treat all `HIGH` and `MEDIUM` priority findings as errors.
- **PMD**: copy-paste detection and additional code smell rules.

```kotlin
// build.gradle.kts example
plugins {
    checkstyle
    id("com.github.spotbugs") version "6.x"
    pmd
}
checkstyle { toolVersion = "10.x"; isIgnoreFailures = false }
spotbugs { effort = Effort.MAX; reportLevel = Confidence.MEDIUM }
pmd { isIgnoreFailures = false }
```

---

## Jackson Configuration

- Register `JavaTimeModule` globally to support `java.time` types; never configure per-object-mapper ad hoc.
- Set `FAIL_ON_UNKNOWN_PROPERTIES` to `false` for inbound DTOs (tolerant reader pattern) and `true` only for outbound serialisation tests.
- Use `@JsonProperty` on DTO fields to decouple JSON keys from Java field names explicitly.
- Never expose domain entities directly as JSON response bodies; always use dedicated DTO/record types.

---

## Null Safety

- Annotate all public API method parameters and return types with `@NonNull` or `@Nullable` (from `org.jspecify` or `jakarta.annotation`).
- Enable null-checking in the IDE and CI (IntelliJ inspections or the NullAway Checker Framework annotation processor).
- Do not rely on `Optional` as a null safety mechanism for fields or constructor parameters; use it only as a return type for methods that explicitly represent "absent value".

---

## Concurrency

- Prefer **Virtual Threads** (Java 21) for all I/O-bound concurrency; do not create platform thread pools manually for I/O tasks.
- Use **`CompletableFuture`** for composing async pipelines; always specify an explicit executor — never use the common pool for I/O tasks.
- Avoid shared mutable state; use immutable Records or `@Value` classes as data carriers between threads.
- Document thread-safety guarantees (or lack thereof) on every class that is shared across threads.
