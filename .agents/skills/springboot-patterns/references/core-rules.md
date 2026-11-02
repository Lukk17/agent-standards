# Spring Boot Core Rules in Depth

The baseline detail, the Pass and Fail examples, and the reasoning behind each rule the SKILL.md hub states in one or two lines, plus the production defaults, the startup hook and the related skills. Open it when a hub rule needs its worked form or its full explanation. Written for Spring Boot 4 on blocking Spring MVC.

---

### Contents

- Baseline
- Keep the layers doing one job each
- Never let a framework type into the API contract
- Return RFC 9457 problem details
- Call other services with RestClient, wrapped in Resilience4j
- Put the transaction on the service method
- Cache with a TTL and an eviction path
- Deny by default and validate at the edge
- Write the failing test first
- Production defaults
- Startup readiness log
- Related skills

---

### Baseline

Written for Spring Boot 4, with the Spring Security 7, Hibernate 7, Jackson 3 and JUnit 6 that ship with it. The Java version and the language features it unlocks follow `java-coding-standards`. A Spring Boot 3 project is an upgrade target rather than a second baseline: `@MockBean` and `@SpyBean` are removed in 4, and Jackson moved to the `tools.jackson` packages. This targets blocking Spring MVC on virtual threads, and WebFlux is out of scope.

---

### Keep the layers doing one job each

The controller parses and returns. The service holds the behaviour and the transaction. The repository talks to the
database. A controller that touches a repository has skipped the layer where the rules live.

Pass: a thin controller delegating to a service that returns a project DTO.

```java
@RestController
@RequestMapping("/api/v1/markets")
@Validated
class MarketController {
  @PostMapping
  ResponseEntity<MarketResponse> create(@Valid @RequestBody CreateMarketRequest request) {
    Market market = marketService.create(request);
    return ResponseEntity.status(HttpStatus.CREATED).body(MarketResponse.from(market));
  }
}
```

Fail: a controller injecting `MarketRepository` and building the response from an entity. Full controller, DTO, and
validation examples: [references/rest-api-and-validation.md](rest-api-and-validation.md).

---

### Never let a framework type into the API contract

Spring Data's `Page` serialises differently between versions and exposes internals no client asked for. Map it into
a project-owned envelope inside the service, so the wire contract belongs to the project.

Pass: the service returns `PageResponse.from(page, MarketResponse::from)`, and the controller never sees `Page`.

Fail: `ResponseEntity<Page<MarketEntity>>`, which publishes the entity and the framework type in one move.

The same rule covers entities: a DTO is the contract, and an entity on the wire leaks the schema and every column
somebody adds later.

---

### Return RFC 9457 problem details

Every error response is `application/problem+json` built from Spring's `ProblemDetail`, with `type`, `title`,
`status`, and `detail` set, and field errors carried as a problem property. An ad-hoc error shape means each client
writes a parser for this service alone.

Pass: one `@ControllerAdvice` whose handlers each build a `ProblemDetail` and carry field errors in a problem
property, in full in [references/rest-api-and-validation.md](rest-api-and-validation.md).

Fail: a try-catch in the controller returning `Map.of("error", ex.getMessage())`, which also leaks internals to the
caller.

Enable the framework's own problem responses with `spring.mvc.problemdetails.enabled=true`.

---

### Call other services with RestClient, wrapped in Resilience4j

`RestClient` is the synchronous outbound client. Configure it as a bean with a base URL, explicit connect and read
timeouts, and shared default headers. Then accept that an external call fails eventually: retry with exponential
backoff and jitter, and open a circuit when the far end is clearly down. Never hand-roll a retry loop around a
`Thread.sleep`, and never retry at a fixed interval, because fixed intervals synchronise callers into one burst.

Pass: one bean per upstream, annotations plus configuration, and a fallback that degrades rather than throws.

```java
@Retry(name = "externalApi")
@CircuitBreaker(name = "externalApi", fallbackMethod = "fallback")
public ResponseEntity<String> call() {
    return restClient.get().uri("/endpoint").retrieve().toEntity(String.class);
}

public ResponseEntity<String> fallback(Exception ex) {
    return ResponseEntity.status(503).body("Service unavailable");
}
```

Fail: `RestTemplate`, which is in maintenance mode. It is not annotated deprecated and existing code keeps working,
but it receives only security and bug fixes, so no new call site should use it. `WebClient` is also wrong here,
because WebFlux is out of scope and there is no reactive path to justify it. Equally a fail: a `while` loop
counting attempts around a `Thread.sleep`, which has no jitter, no circuit, and no metrics.

The full Resilience4j configuration and timeout settings are in
[references/outbound-and-resilience.md](outbound-and-resilience.md).

---

### Put the transaction on the service method

`@Transactional` belongs on service methods, never on a controller and never on a repository method. Mark query
paths `readOnly = true`. Remember that calling a transactional method from inside the same bean bypasses the proxy
entirely, so the annotation does nothing.

Pass: `@Transactional(readOnly = true)` on `findById`, and a plain `@Transactional` on `createOrder`.

Fail: a private helper annotated `@Transactional`, or a public method calling `this.otherTransactionalMethod()` and
expecting a new transaction. Extract it into a separate bean.

---

### Cache with a TTL and an eviction path

Caching needs `@EnableCaching`, an explicit time to live, and a size bound. An unbounded cache is a memory leak
with a friendly name, and a cache of mutable state with no invalidation serves stale data until the next deploy.

Pass: `@Cacheable(value = "market", key = "#id")` on the read, with a matching
`@CacheEvict(value = "market", key = "#id")` written in the same change.

Fail: `@Cacheable` on a method whose result changes, with no `@CacheEvict` anywhere in the codebase.

Redis cache manager setup, `@Async` executors, transactional event listeners, and background jobs are in
[references/caching-async-and-events.md](caching-async-and-events.md).

---

### Deny by default and validate at the edge

Two security rules apply to every endpoint, so they sit here rather than one reference away. Turn on
`@EnableMethodSecurity` and put the authorization rule next to the method it guards, so a new endpoint is closed
until somebody opens it, and constrain the request DTO so Bean Validation rejects the payload before any business
code runs.

Pass: `@PreAuthorize("hasRole('ADMIN')")` on the handler, and `@Valid @RequestBody CreateUserDto dto` where the
record carries `@NotBlank`, `@Size`, and `@Email`.

Fail: an ownership check written inside the method body, which every later caller of that service method skips, or
an unconstrained DTO where the first thing to notice a bad value is a database constraint violation.

Tokens, hashing, CSRF, headers, CORS, secrets, uploads, rate limiting: [references/security.md](security.md).

---

### Write the failing test first

Red, green, refactor, in that order. A test written after the code passes on the first run, which proves nothing
about whether it would catch the regression it exists for. Pick the narrowest slice that can hold the behaviour:
plain JUnit with Mockito for service logic, `@WebMvcTest` for status codes and validation, `@DataJpaTest` with
Testcontainers for repositories, and `@SpringBootTest` only where the wiring itself is the subject.

Pass: the new test fails for the right reason, then the implementation makes it pass.

Fail: the implementation lands first and the test is written to match whatever it already does. Slice examples,
Testcontainers wiring, builders, and the JaCoCo gate are in [references/testing.md](testing.md).

---

### Production defaults

- Constructor injection everywhere, no field injection.
- `spring.mvc.problemdetails.enabled=true` so framework errors match your own.
- `spring.threads.virtual.enabled=true`, since this skill targets blocking MVC on virtual threads.
- `spring.jpa.hibernate.ddl-auto=validate`, with the schema owned by Flyway or Liquibase migrations.
- HikariCP sized for the workload with explicit timeouts, and `readOnly = true` on every query path.
- Nullability enforced with `@NonNull` and `Optional`, per `java-coding-standards`.
- The version in the path as `/api/v1/resource`, and a computed future `Sunset` date on anything deprecated.

---

### Startup readiness log

The banner and its format belong to `observability-and-logging`. What is Spring-specific is the hook: emit the block
from an `@EventListener(ApplicationReadyEvent.class)` method. Spring Boot sends that event after every application and
command-line runner has run, right before readiness moves to `ACCEPTING_TRAFFIC`, whereas `ApplicationStartedEvent`
fires before those runners.

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `java-coding-standards` | Java naming, records, immutability, exceptions, and logging style. |
| `coding-standards` | The cross-language engineering floor these patterns sit on. |
| `hexagonal-architecture` | Ports and adapters layering, when the project has chosen it over layered packages. |
| `api-design` | Resource naming, status codes, and versioning policy above the framework. |
| `database-migrations` | Migration authoring, rollback, and zero-downtime schema change. |
| `postgres-patterns` | PostgreSQL-specific indexing and query planning. |
| `observability-and-logging` | Log format, metrics, tracing, health, and the startup banner. |
| `build-dependency-management` | Version catalogs, BOM imports, and where the plugin versions live. |
| `keycloak-patterns` | Configuring Keycloak as the identity provider behind these flows. |
| `code-reviewer` | Reviewing a Spring Boot diff against all of the above. |
