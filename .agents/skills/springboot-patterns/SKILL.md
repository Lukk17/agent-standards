---
name: springboot-patterns
description: "Spring Boot service architecture on blocking Spring MVC: controller, service and repository layering, RFC 7807 errors, RestClient calls wrapped in Resilience4j, caching, async work, transactional events, and API versioning. Use when you say \"structure this Spring Boot API\", \"return proper error responses\", \"retry this external call\", \"cache this lookup\", or \"version this endpoint\". Not for authentication and rate limiting, use `springboot-security`."
license: Apache-2.0
---

# Spring Boot Development Patterns

How a production Spring Boot service is put together, from the controller down to the outbound HTTP client. Java 21
LTS is the minimum with Java 25 LTS as the recommended target, and Spring Boot 3.x throughout. This skill targets
blocking Spring MVC on virtual threads, and WebFlux is out of scope.

---

### When to activate

- Building or restructuring a REST API on Spring MVC, and layering its controllers, services, and repositories.
- Adding validation, exception handling, or pagination to endpoints.
- Configuring caching, asynchronous processing, or Spring events.
- Calling another service over HTTP and making that call survive the other service.
- Setting up profiles and production defaults for a Spring Boot deployment.

---

### When not to activate

- Authentication, authorization, security headers, and rate limiting, use `springboot-security`.
- Entity mapping, fetch strategy, and query tuning, use `jpa-patterns`.
- Java language style, naming, and immutability, use `java-coding-standards`.
- Writing the tests, use `springboot-tdd`.
- Ports and adapters layering across the whole service, use `hexagonal-architecture`.
- Log format, metrics, tracing, and the startup readiness banner, use `observability-and-logging`.

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

The same rule covers entities. A DTO is the contract, and an entity on the wire leaks the schema and every column
somebody adds later.

---

### Return RFC 7807 problem details

Every error response is `application/problem+json` built from Spring's `ProblemDetail`, with `type`, `title`,
`status`, and `detail` set, and field errors carried as a problem property. An ad-hoc error shape means each client
writes a parser for this service alone.

Pass: one `@ControllerAdvice` translating exceptions centrally.
```java
@ExceptionHandler(MethodArgumentNotValidException.class)
ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
  ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
  problem.setType(URI.create("https://example.com/problems/validation"));
  problem.setTitle("Validation failed");
  problem.setProperty("errors", fieldErrorsOf(ex));
  return problem;
}
```

Fail: a try-catch in the controller returning `Map.of("error", ex.getMessage())`, which also leaks internals to the
caller.

Enable the framework's own problem responses with `spring.mvc.problemdetails.enabled=true`.

---

### Call other services with RestClient

`RestClient` is the synchronous outbound client. Configure it as a bean with a base URL, explicit connect and read
timeouts, and shared default headers, then inject it.

Pass:
```java
@Bean
public RestClient marketApiClient(RestClient.Builder builder) {
    return builder.baseUrl("https://api.example.com").requestFactory(timedFactory()).build();
}
```

Fail: `RestTemplate`, which is in maintenance mode. It is not annotated deprecated and existing code keeps working,
but it receives only security and bug fixes, so no new call site should use it. `WebClient` is also wrong here,
because WebFlux is out of scope and there is no reactive path to justify it.

---

### Wrap every outbound call in Resilience4j

An external call fails eventually. Retry with exponential backoff and jitter, and open a circuit when the far end
is clearly down. Never hand-roll a retry loop with `Thread.sleep`, and never retry at a fixed interval, because
fixed intervals synchronise every caller into one burst.

Pass: annotations plus configuration, with a fallback that degrades rather than throws.
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

Fail: a `while` loop counting attempts around a `Thread.sleep`, which has no jitter, no circuit, and no metrics.

The full Resilience4j configuration and timeout settings are in
[references/outbound-and-resilience.md](references/outbound-and-resilience.md).

---

### Put the transaction on the service method

`@Transactional` belongs on service methods, never on a controller and never on a repository method. Mark query
paths `readOnly = true`. Remember that calling a transactional method from inside the same bean bypasses the proxy
entirely, so the annotation does nothing.

Pass:
```java
@Transactional(readOnly = true)
public Order findById(Long id) { ... }

@Transactional
public Order createOrder(CreateOrderCommand cmd) { ... }
```

Fail: a private helper annotated `@Transactional`, or a public method calling `this.otherTransactionalMethod()` and
expecting a new transaction. Extract it into a separate bean.

---

### Publish domain events after the commit

`ApplicationEventPublisher` decouples work inside one service. Listen with
`@TransactionalEventListener(phase = AFTER_COMMIT)` so a rolled-back write never triggers an email nobody can
un-send.

Pass: `@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)` on the listener, with the event carrying
an identifier rather than a detached entity.

Fail: a plain `@EventListener`, which runs inside the transaction and fires even when the transaction later rolls
back.

---

### Cache with a TTL and an eviction path

Caching needs `@EnableCaching`, an explicit time to live, and a size bound. An unbounded cache is a memory leak
with a friendly name, and a cache of mutable state with no invalidation serves stale data until the next deploy.

Pass: `@Cacheable(value = "market", key = "#id")` on the read, with a matching
`@CacheEvict(value = "market", key = "#id")` written in the same change.

Fail: `@Cacheable` on a method whose result changes, with no `@CacheEvict` anywhere in the codebase.

Redis cache manager configuration, `@Async` setup, and background job patterns are in
[references/caching-async-and-events.md](references/caching-async-and-events.md).

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

### Version in the path, and deprecate with a real date

Put the version in the URI as `/api/v1/resource`. When a version is going away, mark the controller `@Deprecated`,
send a `Deprecation` header, and send a `Sunset` header holding a date at least one full release cycle ahead of the
announcement. Compute that date when you write the deprecation rather than copying one from an example, because a
sunset date already in the past tells a client the endpoint is gone while it is still serving traffic.

Pass: `.header("Sunset", sunsetDate.format(DateTimeFormatter.RFC_1123_DATE_TIME))` on a `@Deprecated` controller,
where `sunsetDate` is computed from the release calendar rather than typed in.

Fail: a hardcoded sunset date nobody revisits, or a version removed in the release that announced its deprecation.

---

### Production defaults

- Constructor injection everywhere, no field injection.
- `spring.mvc.problemdetails.enabled=true` so framework errors match your own.
- `spring.threads.virtual.enabled=true`, since this skill targets blocking MVC on virtual threads.
- HikariCP sized for the workload with explicit timeouts, per `jpa-patterns`, and `readOnly = true` on query paths.
- Nullability enforced with `@NonNull` and `Optional`, per `java-coding-standards`.

---

### Reference material

| Open this | For |
| --- | --- |
| [references/rest-api-and-validation.md](references/rest-api-and-validation.md) | Full controller, DTO, validation, pagination envelope, exception handler, and OpenAPI setup. |
| [references/outbound-and-resilience.md](references/outbound-and-resilience.md) | RestClient configuration, Resilience4j retry and circuit breaker settings, timeouts. |
| [references/caching-async-and-events.md](references/caching-async-and-events.md) | Redis cache manager, `@Async` executors, Spring events, background jobs, request filters. |
| [../observability-and-logging/references/startup-readiness-log.md](../observability-and-logging/references/startup-readiness-log.md) | The startup banner and readiness log block, which `observability-and-logging` owns. |
| [../springboot-security/SKILL.md](../springboot-security/SKILL.md) | Rate limiting, which has exactly one implementation and it lives there. |

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `springboot-security` | Authentication, authorization, headers, secrets, and rate limiting. |
| `jpa-patterns` | Entities, queries, transactions at the data layer, and pooling. |
| `java-coding-standards` | Java naming, immutability, exceptions, and logging style. |
| `springboot-tdd` | Test slices and coverage for everything here. |
| `observability-and-logging` | Log format, metrics, tracing, health, and the startup banner. |
| `hexagonal-architecture` | Ports and adapters layering, when the project has chosen it over layered packages. |
| `api-design` | Resource naming, status codes, and versioning policy above the framework. |

---

### Checklist

- [ ] Controllers parse and return, services hold behaviour, repositories reach the database, nothing skips a layer.
- [ ] No entity and no Spring Data `Page` appears in a response body.
- [ ] Every error response is a `ProblemDetail` from one `@ControllerAdvice`.
- [ ] Outbound HTTP goes through `RestClient`, with no new `RestTemplate` call site.
- [ ] Every external call has a retry with backoff and jitter, a circuit breaker, and explicit timeouts.
- [ ] `@Transactional` sits on service methods only, with `readOnly = true` on query paths.
- [ ] Event listeners that must not run on a rollback use `AFTER_COMMIT`.
- [ ] Every cache has a TTL, a size bound, and an eviction path.
- [ ] Deprecated versions carry a `Sunset` date computed to be in the future.
