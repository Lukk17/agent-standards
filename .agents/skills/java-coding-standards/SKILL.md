---
name: java-coding-standards
description: "Java coding standards for Spring Boot services: naming, immutability, Optional usage, streams, exceptions, generics, concurrency, logging, Jackson, null safety, Lombok, and project layout."
origin: ECC
---

# Java Coding Standards

Standards for readable, maintainable Java (17+) code in Spring Boot services.

## When to Activate

- Writing or reviewing Java code in Spring Boot projects
- Enforcing naming, immutability, or exception handling conventions
- Working with records, sealed classes, or pattern matching (Java 17+)
- Reviewing use of Optional, streams, or generics
- Structuring packages and project layout

## Core Principles

- Prefer clarity over cleverness
- Immutable by default; minimize shared mutable state
- Fail fast with meaningful exceptions
- Consistent naming and package structure

## Naming

```java
// PASS: Classes/Records: PascalCase
public class MarketService {}
public record Money(BigDecimal amount, Currency currency) {}

// PASS: Methods/fields: camelCase
private final MarketRepository marketRepository;
public Market findBySlug(String slug) {}

// PASS: Constants: UPPER_SNAKE_CASE
private static final int MAX_PAGE_SIZE = 100;
```

Boolean variables and methods must start with `is`, `has`, or `can`.

Method names must be descriptive verbs: `calculateTotalRevenue`, `findActiveUsers`.

## Lombok

Use Lombok to eliminate boilerplate. Required annotations:

- `@Slf4j` — mandatory for all logging; never use `LoggerFactory.getLogger(...)` manually
- `@RequiredArgsConstructor` — constructor injection
- `@Builder` — for complex object construction
- `@Value` — for immutable value objects
- `@Getter` / `@Setter` — only when not using `@Value` or records

Prefer annotation-based configuration over manual wiring.

## Immutability

```java
// PASS: Favor records and final fields
public record MarketDto(Long id, String name, MarketStatus status) {}

public class Market {
  private final Long id;
  private final String name;
  // getters only, no setters
}
```

## Optional Usage

```java
// PASS: Return Optional from find* methods
Optional<Market> market = marketRepository.findBySlug(slug);

// PASS: Map/flatMap instead of get()
return market
    .map(MarketResponse::from)
    .orElseThrow(() -> new EntityNotFoundException("Market not found"));
```

`Optional` as return type ONLY — not for fields or constructor parameters.

## Streams Best Practices

```java
// PASS: Use streams for transformations, keep pipelines short
List<String> names = markets.stream()
    .map(Market::name)
    .filter(Objects::nonNull)
    .toList();

// FAIL: Avoid complex nested streams; prefer loops for clarity
```

## Formatting and Style

- Use 2 or 4 spaces consistently (project standard)
- One public top-level type per file
- Keep methods short and focused; extract helpers
- Order members: constants, fields, constructors, public methods, protected, private
- Lambda expressions longer than one line must be extracted to a named private method

Use `var` only when the declared type appears explicitly on the same line and is verbose (e.g., `var list = new ArrayList<String>()`). Prefer explicit type names for clarity.

Never use fully qualified class names in code; use imports.

## Exceptions

- Use unchecked exceptions for domain errors; wrap technical exceptions with context
- Create domain-specific exceptions (e.g., `MarketNotFoundException`)
- Avoid broad `catch (Exception ex)` unless rethrowing/logging centrally
- Use global exception handlers (e.g., `@ControllerAdvice` in Spring)
- No local try-catch blocks scattered across business logic methods

```java
throw new MarketNotFoundException(slug);
```

## Generics and Type Safety

- Avoid raw types; declare generic parameters
- Prefer bounded generics for reusable utilities

```java
public <T extends Identifiable> Map<Long, T> indexById(Collection<T> items) { ... }
```

## Null Safety

- Annotate all public API signatures with `@NonNull` / `@Nullable` (jspecify or `jakarta.annotation`)
- Enforce with NullAway or jspecify annotation processor in CI
- `Optional` as return type ONLY — not for fields or constructor parameters
- Accept `@Nullable` only when unavoidable; otherwise use `@NonNull`
- Use Bean Validation (`@NotNull`, `@NotBlank`) on inputs

## Logging

Use **SLF4J** as the logging API in all code; never import a concrete logging framework (Logback, Log4j2) directly in business logic.

Use `@Slf4j` (Lombok) for logger injection; never instantiate `LoggerFactory.getLogger(...)` manually.

```java
// PASS
@Slf4j
public class MarketService {
    public Market findBySlug(String slug) {
        log.info("fetch_market slug={}", slug);
        log.error("failed_fetch_market slug={}", slug, ex);
    }
}

// FAIL
private static final Logger log = LoggerFactory.getLogger(MarketService.class);
```

Log levels:
- `ERROR` — unhandled exceptions
- `WARN` — recoverable issues
- `INFO` — significant domain events
- `DEBUG` — diagnostic detail

### Logging (Production)

- Use `logstash-logback-encoder` for structured JSON logs in production
- Use Logback as the default implementation; switch to Log4j2 only if async appenders or advanced routing are required

## Concurrency

### Virtual Threads (Java 21+)

Use `Executors.newVirtualThreadPerTaskExecutor()` for all I/O-bound concurrency. Never use platform threads for I/O-bound work.

### Async Pipelines

Use `CompletableFuture` for composing async pipelines. Always specify an explicit executor — never use the default ForkJoinPool for I/O:

```java
CompletableFuture.supplyAsync(() -> fetchData(), ioExecutor)
    .thenApplyAsync(data -> transform(data), computeExecutor);
```

Avoid shared mutable state; use immutable Records or `@Value` classes as data carriers between threads. Document thread-safety guarantees (or lack thereof) on every class that is shared across threads.

## Jackson Configuration

- Register `JavaTimeModule` globally for Java 8 date/time types; never configure per-object-mapper ad hoc
- Set `FAIL_ON_UNKNOWN_PROPERTIES` to `false` for inbound DTOs (tolerant reader pattern)
- Use `@JsonProperty` for explicit field mapping, decoupling JSON keys from Java field names
- Never expose domain entities directly as JSON response bodies — use DTOs

## Project Structure (Maven/Gradle)

```
src/main/java/com/example/app/
  config/
  controller/
  service/
  repository/
  domain/
  dto/
  util/
src/main/resources/
  application.yml
src/test/java/... (mirrors main)
```

## Code Quality Gates (CI)

Enforce in CI via Gradle:

- **Checkstyle** — style enforcement (Google Java Style or project-defined ruleset)
- **SpotBugs** — static bytecode analysis; treat all `HIGH` and `MEDIUM` findings as errors
- **PMD** — copy-paste detection and additional code smell rules

```groovy
plugins {
    id 'checkstyle'
    id 'com.github.spotbugs' version '6.0.9'
    id 'pmd'
}
checkstyle { toolVersion = '10.12.4'; ignoreFailures = false }
spotbugs { effort = 'max'; reportLevel = 'medium' }
pmd { ignoreFailures = false; ruleSetFiles = files('config/pmd/ruleset.xml') }
```

## Build Output

Redirect Gradle output to a log file to prevent terminal overflow:

```bash
./gradlew <task> > build_log.txt 2>&1
```

This overwrites `build_log.txt` so it always reflects only the most recent execution.

## Javadoc

Use Javadoc only when strictly necessary to document a public class's non-obvious contract. Do NOT add Javadoc to methods, constructors, or self-explanatory classes.

## Testing Expectations

- JUnit 5 + AssertJ for fluent assertions
- Mockito for mocking; use `@InjectMocks` and `@Mock` instead of manual `@BeforeEach` initialization
- Avoid partial mocks where possible
- Favor deterministic tests; no hidden sleeps
- Extract object creation to helper methods or a shared `TestDataFactory` class

## Code Smells to Avoid

- Long parameter lists → use DTO/builders
- Deep nesting → early returns
- Magic numbers → named constants
- Static mutable state → prefer dependency injection
- Silent catch blocks → log and act or rethrow

**Remember**: Keep code intentional, typed, and observable. Optimize for maintainability over micro-optimizations unless proven necessary.
