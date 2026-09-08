---
name: java-coding-standards
description: "Java language standards for Spring Boot services: naming, Lombok and constructor injection, immutability and records, Optional, streams, exceptions, generics, null safety, SLF4J logging, and Javadoc discipline. Use when you say \"review this Java class\", \"should this be a record\", \"is this Optional usage correct\", \"rename these methods properly\", or \"set up Checkstyle and SpotBugs\". Not for Spring Boot wiring and REST structure, use `springboot-patterns`."
license: Apache-2.0
---

# Java Coding Standards

How Java itself is written in a Spring Boot service, from naming through to Javadoc. Java 21 LTS is the minimum and
Java 25 LTS, released September 2025, is the recommended target, so records, sealed types, pattern matching, and
virtual threads are all available and expected.

---

### When to activate

- Writing or reviewing Java in a Spring Boot project.
- Deciding between a record, a class, and a sealed hierarchy.
- Enforcing naming, immutability, or exception conventions in review.
- Reviewing use of `Optional`, streams, or generics.
- Structuring packages, or setting up the static analysis that guards this style.

---

### When not to activate

- Spring Boot structure, controllers, DTO contracts, and bean wiring, use `springboot-patterns`.
- Entity mapping, queries, and transaction boundaries, use `jpa-patterns`.
- Writing the tests, use `springboot-tdd`.
- Running the build and analysis pipeline before a pull request, use `springboot-verification`.
- Version catalogs, BOM imports, and dependency admission, use `build-dependency-management`.
- Ports and adapters layering across a service, use `hexagonal-architecture`.

---

### Name things after what they are

Classes and records are PascalCase, methods and fields camelCase, constants UPPER_SNAKE_CASE. A boolean starts with
`is`, `has`, or `can`. A method name is a verb phrase specific enough that a reader does not have to open the body.

Pass:

```java
public record Money(BigDecimal amount, Currency currency) {}

private static final int MAX_PAGE_SIZE = 100;

public List<User> findActiveUsersByTenant(TenantId tenantId) { ... }
```

Fail: `getData()`, `flag`, `process()`, and a constant spelled `maxPageSize`.

---

### Inject through the constructor, log through Lombok

Lombok removes boilerplate that carries no decisions. `@RequiredArgsConstructor` for injection, `@Slf4j` for the
logger, `@Builder` where construction is genuinely complex, `@Value` for immutable value objects, and `@Getter` or
`@Setter` only where neither a record nor `@Value` fits.

Pass: final fields, one generated constructor, no annotation on the field.

```java
@Service
@Slf4j
@RequiredArgsConstructor
public class MarketService {
  private final MarketRepository marketRepository;
}
```

Fail: field injection, which hides the dependency from every constructor call and from every test.

```java
@Autowired
private MarketRepository marketRepository;
```

---

### Make it immutable unless something has to change

Records for data, final fields elsewhere, and no setter that exists only because a framework once needed one.
Immutable objects are safe to share across threads and cannot be half-updated by a failed operation.

Pass:

```java
public record MarketDto(Long id, String name, MarketStatus status) {}
```

Fail: a mutable bean with a no-argument constructor and a setter per field, passed between threads.

---

### Return Optional, never store it

`Optional` is a return type for a lookup that can legitimately find nothing. It is not a field type, not a
parameter type, and not a collection element.

Pass: map or flatMap the value, and end with `orElseThrow`.

```java
return marketRepository.findBySlug(slug)
    .map(MarketResponse::from)
    .orElseThrow(() -> new MarketNotFoundException(slug));
```

Fail: `.get()` after `.isPresent()`, or an `Optional<String>` field on an entity.

---

### Keep stream pipelines short and named

A stream expresses a transformation. When the pipeline needs more than a few stages, or a stage needs a comment,
extract it into a method whose name says what the transformation produces.

Pass:

```java
List<String> names = markets.stream()
    .map(Market::name)
    .filter(Objects::nonNull)
    .toList();
```

Fail: a twelve-stage pipeline with a nested `flatMap` and a lambda spanning six lines. Extract the lambda, or the
whole pipeline, into a named private method.

---

### Write for the next reader

One public top-level type per file. Members in order: constants, fields, constructors, public methods, protected,
private. Methods short enough to hold in your head, with helpers extracted. A lambda longer than one line becomes a
named private method. Never write a fully qualified class name in code, import it.

Prefer an explicit type over `var`. The narrow allowance is a right-hand side that already names the type, such as
`var list = new ArrayList<String>()`. Everywhere else, the type is the documentation.

Pass: `MarketResponse response = service.findBySlug(slug);`

Fail: `var result = service.process(input);`, where a reader has to open two methods to learn what `result` is.

Indent with 2 or 4 spaces, matching the project. Consistency beats preference.

---

### Fail with a domain exception, handle it centrally

Domain errors are unchecked exceptions named after the thing that went wrong. Technical exceptions get wrapped with
context rather than swallowed. One `@ControllerAdvice` translates them into responses, so business methods stay
free of try-catch blocks.

Pass:

```java
throw new MarketNotFoundException(slug);
```

Fail: `catch (Exception ex) { log.error("error", ex); }` in the middle of a service method, which turns a failure
into a wrong answer.

---

### Declare your generics

No raw types. Bound a type parameter when a reusable utility needs a capability from it. A raw type turns a
compile-time error into a `ClassCastException` at runtime.

Pass:

```java
public <T extends Identifiable> Map<Long, T> indexById(Collection<T> items) { ... }
```

Fail: `public Map indexById(Collection items)`.

---

### Say where null is allowed

Annotate public API signatures with `@NonNull` and `@Nullable`, from JSpecify or `jakarta.annotation`, and enforce
them with NullAway or the JSpecify processor in CI. Accept `@Nullable` only where the absence is genuinely part of
the contract. Validate inbound values with Bean Validation so a null never travels deeper than the edge.

Pass: an annotated signature with a CI check that fails on a violation.

Fail: annotations added for documentation with nothing enforcing them, which drift within a release.

---

### Log through SLF4J with structured messages

Use SLF4J as the API, and never import Logback or Log4j2 in business code. Take the logger from `@Slf4j`. Message
keys are stable tokens with the variable parts as parameters, so a log aggregator can group them.

Pass: `log.info("fetch_market slug={}", slug);` inside a class annotated `@Slf4j`.

Fail: `log.info("Fetching market " + slug)`, or a logger built by hand with
`LoggerFactory.getLogger(MarketService.class)`.

Levels: `ERROR` for unhandled exceptions, `WARN` for recoverable problems, `INFO` for significant domain events,
`DEBUG` for diagnostics. Structured JSON output and the production logging stack belong to
`observability-and-logging`.

---

### Javadoc

Default to none. A Javadoc block is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named method, rename the parameters so they carry their own meaning, and tighten the
types. Do that first and most Javadoc blocks have nothing left to say, which is the outcome you want. Code that
explains itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@param` and `@return` and `@throws` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `@param` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or
   who owns the argument afterwards. `@param orderId the wholesale order identifier` is noise, delete it.
3. `@return` only when it is non-obvious.
4. `@throws` always, for every exception a caller can act on. Unchecked exceptions never appear in the signature, so
   this one is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

```java
// GOOD: one sentence, then only what the signature cannot say
/**
 * Reserves stock for an order and holds it until the payment window closes.
 *
 * @param holdFor how long the reservation survives, at most 15 minutes
 * @throws InsufficientStockException when the warehouse cannot cover the order
 */
public Reservation reserve(OrderId orderId, Duration holdFor) { ... }

// BAD: restates the signature, and the first tag wraps onto a second line
/**
 * Reserves stock.
 *
 * @param orderId the identifier of the order that stock is being reserved
 *                against, taken from the inbound request
 * @param holdFor the hold duration
 * @return the reservation
 */
public Reservation reserve(OrderId orderId, Duration holdFor) { ... }

// BEST: naming and types carry it, no Javadoc needed
public Reservation reserveStockUntilPaymentWindowCloses(OrderId orderId, Duration holdFor) { ... }
```

---

### Reference material

| Open this | For |
| --- | --- |
| [references/concurrency.md](references/concurrency.md) | Virtual threads, executors, `CompletableFuture` composition, and thread-safety documentation. |
| [references/serialization-and-config.md](references/serialization-and-config.md) | Jackson setup, typed `@ConfigurationProperties`, and entity to DTO mapping. |
| [references/static-analysis.md](references/static-analysis.md) | Checkstyle, SpotBugs, and PMD wiring, and keeping build output readable. |
| [references/project-layout.md](references/project-layout.md) | Package structure for a layered project, and the code smells to fix on sight. |

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `springboot-patterns` | Spring Boot structure, REST contracts, caching, and async. |
| `jpa-patterns` | Entities, queries, and transactions. |
| `springboot-tdd` | Test structure, slices, and the coverage gate. |
| `springboot-verification` | The pipeline that runs the analysis tools. |
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
- [ ] Javadoc is absent by default, and every surviving block clears the caps above.
