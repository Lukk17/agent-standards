---
name: springboot-patterns
description: "Spring Boot services end to end on blocking Spring MVC: controller, service and repository layering, RFC 7807 errors, RestClient wrapped in Resilience4j, caching and events, Spring Security 6 authentication, authorization, headers and rate limiting, JPA mapping, N+1 and HikariCP, JUnit 5 and Testcontainers tests, and the pre-merge build, scan and coverage pipeline. Use when you say \"structure this Spring Boot API\", \"add JWT auth to this endpoint\", \"lock this down to admins\", \"why does this query run two hundred times\", \"write a @WebMvcTest for this controller\", \"rate limit this endpoint\", or \"verify this before I open the PR\". Not for Java language style, naming, records and Optional usage, use `java-coding-standards`."
license: Apache-2.0
---

# Spring Boot Patterns

How a production Spring Boot service is put together, from the controller down to the database, the security
around it, the tests, and the pipeline that ships it. Each reference below carries the depth for one area.

---

### Baseline

Java 21 LTS is the minimum and Java 25 LTS is the recommended target, so records, sealed types, pattern matching,
and virtual threads are all available and expected. Spring Boot 3.x throughout, with Spring Security 6.x and the
Hibernate 6 that ships with it. This targets blocking Spring MVC on virtual threads, and WebFlux is out of scope.

---

### When to activate

- Building or restructuring a REST API on Spring MVC, and layering its controllers, services, and repositories.
- Adding validation, exception handling, or pagination to endpoints.
- Configuring caching, asynchronous processing, or Spring events.
- Calling another service over HTTP and making that call survive the other service.
- Adding authentication, authorization, CORS, response headers, or rate limiting.
- Designing entities, choosing a fetch strategy, chasing an N+1 query, or sizing the connection pool.
- Writing the tests, choosing a slice, wiring Testcontainers, or fixing a coverage gate.
- Running the build, analysis, and scan pipeline before a pull request or a deployment.

---

### When not to activate

- Java language style, naming, immutability, and `Optional`, use `java-coding-standards`.
- Ports and adapters layering across the whole service, use `hexagonal-architecture`.
- Log format, metrics, tracing, and the startup readiness banner, use `observability-and-logging`.
- Schema change and rollout mechanics, use `database-migrations`.
- PostgreSQL query planning and index internals, use `postgres-patterns`.
- Language-neutral threat modelling and review checklists, use `security-review`.
- Configuring Keycloak itself as the identity provider, use `keycloak-patterns`.
- Version catalogs, BOM imports, and dependency admission, use `build-dependency-management`.

---

### Keep the layers doing one job each

The controller parses and returns. The service holds the behaviour and the transaction. The repository talks to the
database. A controller that touches a repository has skipped the layer where the rules live.

Pass: a thin controller delegating to a service that returns a project DTO.

```java
@RestController
@RequestMapping("/api/markets")
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
validation examples: [references/rest-api-and-validation.md](references/rest-api-and-validation.md).

---

### Never let a framework type into the API contract

Spring Data's `Page` serialises differently between versions and exposes internals no client asked for. Map it into
a project-owned envelope inside the service, so the wire contract belongs to the project.

Pass: the service returns `PageResponse.from(page, MarketResponse::from)`, and the controller never sees `Page`.

Fail: `ResponseEntity<Page<MarketEntity>>`, which publishes the entity and the framework type in one move.

The same rule covers entities: a DTO is the contract, and an entity on the wire leaks the schema and every column
somebody adds later.

---

### Return RFC 7807 problem details

Every error response is `application/problem+json` built from Spring's `ProblemDetail`, with `type`, `title`,
`status`, and `detail` set, and field errors carried as a problem property. An ad-hoc error shape means each client
writes a parser for this service alone.

Pass: one `@ControllerAdvice` whose handlers each build a `ProblemDetail` and carry field errors in a problem
property, in full in [references/rest-api-and-validation.md](references/rest-api-and-validation.md).

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
[references/outbound-and-resilience.md](references/outbound-and-resilience.md).

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
[references/caching-async-and-events.md](references/caching-async-and-events.md).

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

Tokens, hashing, CSRF, headers, CORS, secrets, uploads, rate limiting: [references/security.md](references/security.md).

---

### Write the failing test first

Red, green, refactor, in that order. A test written after the code passes on the first run, which proves nothing
about whether it would catch the regression it exists for. Pick the narrowest slice that can hold the behaviour:
plain JUnit with Mockito for service logic, `@WebMvcTest` for status codes and validation, `@DataJpaTest` with
Testcontainers for repositories, and `@SpringBootTest` only where the wiring itself is the subject.

Pass: the new test fails for the right reason, then the implementation makes it pass.

Fail: the implementation lands first and the test is written to match whatever it already does. Slice examples,
Testcontainers wiring, builders, and the JaCoCo gate are in [references/testing.md](references/testing.md).

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
 * Publishes the order to the fulfilment topic once the transaction commits.
 *
 * @throws OrderPublishException when the broker rejects the message
 */
public void publish(OrderId orderId) { ... }

// BAD: restates the signature, and the first tag wraps onto a second line
/**
 * Publishes an order.
 *
 * @param orderId the identifier of the order that should be published to the
 *                fulfilment topic
 * @return nothing
 */
public void publish(OrderId orderId) { ... }
```

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

### Which reference to open for which task

| Task | Reference |
| --- | --- |
| Controllers, DTOs, validation, the pagination envelope, the exception handler, versioning, OpenAPI | [references/rest-api-and-validation.md](references/rest-api-and-validation.md) |
| RestClient beans, Resilience4j retry and circuit breaker settings, timeouts, fallbacks | [references/outbound-and-resilience.md](references/outbound-and-resilience.md) |
| Redis cache manager, `@Async` executors, transactional events, scheduled jobs, request filters | [references/caching-async-and-events.md](references/caching-async-and-events.md) |
| Authentication, method authorization, SQL injection, password hashing, CSRF, secrets, uploads, rate limiting | [references/security.md](references/security.md) |
| OAuth 2.1 flows, refresh token rotation, JWT claim validation, the auth filter, session cookies | [references/oauth2-and-jwt.md](references/oauth2-and-jwt.md) |
| The full response header block, the CORS configuration source, mutual TLS between services | [references/headers-cors-mtls.md](references/headers-cors-mtls.md) |
| Entity mapping, fetch strategy, N+1, projections, transactions, paging, indexing, second-level cache | [references/jpa.md](references/jpa.md) |
| HikariCP sizing formula, pool configuration, utilisation alerts | [references/connection-pooling.md](references/connection-pooling.md) |
| Test slices, MockMvc, Testcontainers, AssertJ, test data builders, the JaCoCo gate | [references/testing.md](references/testing.md) |
| The six pre-merge phases, the scan commands, the report template, the re-run loop | [references/verification-pipeline.md](references/verification-pipeline.md) |
| The startup banner and readiness log block, which `observability-and-logging` owns | [../observability-and-logging/references/startup-readiness-log.md](../observability-and-logging/references/startup-readiness-log.md) |

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

---

### Checklist

- [ ] Controllers parse and return, services hold behaviour, repositories reach the database, nothing skips a layer.
- [ ] No entity and no Spring Data `Page` appears in a response body.
- [ ] Every error response is a `ProblemDetail` from one `@ControllerAdvice`.
- [ ] Outbound HTTP goes through `RestClient`, with a retry, a circuit breaker, and explicit timeouts.
- [ ] `@Transactional` sits on service methods only, with `readOnly = true` on query paths.
- [ ] Event listeners that must not run on a rollback use `AFTER_COMMIT`.
- [ ] Every cache has a TTL, a size bound, and an eviction path.
- [ ] Every sensitive path carries an authorization rule, and every request body is a validated DTO.
- [ ] No association is eager, every paged query has a sort, and no N+1 is left as a follow-up.
- [ ] Every behaviour change started with a test that failed for the right reason, in the narrowest slice.
- [ ] Repository tests run against the production database engine through Testcontainers.
- [ ] Javadoc is absent by default, and every surviving block clears the caps above.
- [ ] The verification pipeline ran in order and every gate is green before the pull request opens.
