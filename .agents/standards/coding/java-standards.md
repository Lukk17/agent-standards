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
