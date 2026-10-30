# Java Core Rules in Depth

The Pass and Fail examples and the reasoning behind each rule the SKILL.md hub states in one or two lines. Open it when a hub rule needs its worked form or its full explanation. Written for Java 25, with Java 21 as the minimum.

---

### Contents

- Name things after what they are
- Inject through the constructor, log through Lombok
- Make it immutable unless something has to change
- Return Optional, never store it
- Keep stream pipelines short and named
- Write for the next reader
- Fail with a domain exception, handle it centrally
- Declare your generics
- Say where null is allowed
- Log through SLF4J with structured messages

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
