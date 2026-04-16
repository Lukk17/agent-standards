# Spring Boot Standards

Applies to Spring Boot applications. Requires `java-standards.md` and `universal-coding-standards.md`.

---

## HTTP Clients

- Use **`RestClient`** for all synchronous HTTP calls (Spring 6.1+).
- Always back `RestClient` calls with Virtual Threads for non-blocking I/O.
- Do not use `WebClient` or `WebFlux` unless the entire application is reactive end-to-end.
- Do not use `RestTemplate`; it is deprecated.

---

## Configuration

- Extract all configuration to `application.yaml`. Never hardcode environment-specific values in code.
- Use typed `@ConfigurationProperties` records or classes instead of `@Value` for groups of related properties.
- Use Spring profiles (`application-dev.yaml`, `application-prod.yaml`) for environment differences.
- Prefer annotation-based setup (`@Bean`, `@Configuration`) over manual programmatic configuration.

---

## Architecture (Spring-specific layers)

Follow Hexagonal Architecture adapted for Spring:

| Layer | Annotation | Rule |
|---|---|---|
| Domain | none | No Spring dependencies; pure Java |
| Application Service | `@Service` | Orchestrates domain; no HTTP/DB details |
| REST Adapter | `@RestController` | Thin; delegates immediately to service |
| Persistence Adapter | `@Repository` | Implements domain Port |

- Controllers must not contain business logic.
- Services must not contain SQL or HTTP details.
- Repositories must not contain business logic.

---

## Exception Handling

- Use `@ControllerAdvice` with `@ExceptionHandler` methods as the single global error handler.
- Return structured error responses (consistent JSON body with `status`, `message`, `timestamp`).
- Never swallow exceptions silently.

---

## Security

- Use Spring Security. Never implement custom authentication from scratch.
- Disable CSRF only for stateless APIs (JWT-authenticated); document the reason.
- Never log sensitive data (passwords, tokens, PII).
- Use `@PreAuthorize` for method-level access control where appropriate.

---

## Testing (Spring-specific)

These rules extend `testing-standards.md` and `java-standards.md`:

- Use `@SpringBootTest` only for true integration tests that require the full context.
- Use `@WebMvcTest` for controller-layer tests; mock the service layer.
- Use `@DataJpaTest` for repository tests; use an in-memory or Testcontainers database.
- Use **Testcontainers** for integration tests that require real infrastructure (databases, queues). Do not mock infrastructure in integration tests.
- Use `MockMvc` for HTTP-layer assertions in controller tests.

---

## Actuator and Observability

- Enable `spring-boot-starter-actuator` in every service.
- Expose `/actuator/health` (with liveness and readiness groups), `/actuator/info`, and `/actuator/prometheus` at minimum.
- Secure all management endpoints: restrict `/actuator` to internal network or require a separate management port (`management.server.port`).
- Implement custom `HealthIndicator` beans for every critical dependency (database, external APIs, message broker).
- Use **Micrometer** with OTLP or Prometheus export for metrics; instrument all service operations with `@Timed` or manual `MeterRegistry` calls.
- Propagate distributed traces using `spring-boot-starter-actuator` + Micrometer Tracing (Brave/OTLP); forward spans to Zipkin, Jaeger, or an OTLP collector.

---

## API Versioning

- Use URI path versioning: `/api/v1/`, `/api/v2/` — this is the most explicit and cache-friendly strategy.
- Never remove a versioned endpoint without a deprecation period of at least one release cycle.
- Annotate deprecated endpoints with `@Deprecated` and return a `Deprecation` response header with the sunset date.

---

## OpenAPI Documentation

- Add `springdoc-openapi-starter-webmvc-ui` to every HTTP service.
- Annotate all controllers with `@Tag`, all operations with `@Operation`, and all error responses with `@ApiResponse`.
- Commit the generated `openapi.yaml` to the repository as a build artifact and verify it does not change unexpectedly in CI.

---

## Resilience

- Wrap all outbound HTTP calls and external service interactions with **Resilience4j** circuit breakers and retry policies.
- Configure exponential backoff with jitter on retry; never use fixed-interval retries.
- Set explicit timeouts on `RestClient` calls; never rely on OS-level connection timeouts.
- Use `@CircuitBreaker` or programmatic `CircuitBreakerRegistry` — not `@Retryable` alone for external calls.

---

## Caching

- Use the **Spring Cache abstraction** (`@Cacheable`, `@CacheEvict`, `@CachePut`) — never bypass it with direct cache client calls in service methods.
- Define explicit eviction policies (TTL, max size) for every cache region; never allow unbounded caches.
- Never cache mutable shared state without a documented invalidation strategy.

---

## Transaction Management

- Apply `@Transactional` at the **service layer only** — never on controllers or repository methods that are called from within an existing transaction.
- Default to `readOnly = true` for query-only methods; override to `readOnly = false` explicitly for write transactions.
- Never call a `@Transactional` method from within the same bean without going through the proxy (self-invocation breaks the transaction boundary).

---

## Event-Driven Patterns

- Use Spring `ApplicationEvent` / `ApplicationEventPublisher` for intra-service decoupling of domain side-effects.
- Publish domain events after a successful transaction commit using `@TransactionalEventListener(phase = AFTER_COMMIT)`.
- For inter-service messaging (Kafka, RabbitMQ), define a dedicated event schema class per topic/exchange; never publish raw domain entities.
