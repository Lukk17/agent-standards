---
name: springboot-patterns
description: 'Spring Boot 4 on Spring MVC: layering, RFC 9457 errors, security, JPA, tests. Use when the user says "structure this Spring Boot API" or "add JWT auth to this endpoint". Not for Java style, use `java-coding-standards`.'
license: Apache-2.0
metadata:
  version: "1.1.0"
---

# Spring Boot Patterns

How a production Spring Boot service is put together, from controller to database, its security, tests and pipeline.

Written for Spring Boot 4 and the libraries that ship with it, on blocking Spring MVC with virtual threads. WebFlux is out of scope, and Spring Boot 3 is an upgrade target, as the core rules reference explains.

---

### When not to activate

- Java language style, naming, immutability, and `Optional`, use `java-coding-standards`.
- Ports and adapters layering across the whole service, use `hexagonal-architecture`.
- Log format, metrics, tracing, and the startup readiness banner, use `observability-and-logging`.

---

### Rules

1. The controller parses and returns, the service holds the behaviour and the transaction, the repository reaches the database, and no controller touches a repository.
2. No entity and no Spring Data `Page` on the wire. The service maps to a DTO and a project-owned `PageResponse` envelope.
3. Every error is a `ProblemDetail` built in one `@ControllerAdvice`, field errors as a problem property.
4. Call out through one `RestClient` bean per upstream with timeouts, a Resilience4j retry, a circuit breaker and a fallback, never `RestTemplate` or `WebClient`.
5. `@Transactional` sits on service methods only, `readOnly = true` on query paths. A self-call bypasses the proxy, so extract the method into another bean.
6. Every cache has a time to live, a size bound, and a `@CacheEvict` written in the same change.
7. Deny by default with `@EnableMethodSecurity` and `@PreAuthorize` on the guarded method, and reject bad payloads with `@Valid` DTOs first.
8. Write the failing test first, in the narrowest slice that holds the behaviour, with `@SpringBootTest` only where the wiring is the subject.
9. Apply the production defaults: tunables in configuration, virtual threads, `ddl-auto=validate`, a sized HikariCP, `/api/v1/` paths.
10. Emit the `observability-and-logging` startup block on `ApplicationReadyEvent`, never `ApplicationStartedEvent`.
11. Query through a `Specification` or a derived method, never an `@Query` string, guarded by ArchUnit.
12. Every endpoint carries the OpenAPI response meta-annotations with its honest success code and the project's own problem schema.
13. Javadoc follows `java-coding-standards`, and nothing about Spring changes it.

---

### Which reference to open for which task

| Task | Reference |
| --- | --- |
| A rule above in full: Pass and Fail examples, the baseline, production defaults | [core-rules.md](references/core-rules.md) |
| Controllers, DTOs, validation, paging envelope, exception handler, OpenAPI | [rest-api-and-validation.md](references/rest-api-and-validation.md) |
| RestClient beans, Resilience4j, timeouts, fallbacks | [outbound-and-resilience.md](references/outbound-and-resilience.md) |
| Redis cache, `@Async`, events, scheduled jobs, request filters | [caching-async-and-events.md](references/caching-async-and-events.md) |
| Authentication, authorization, injection, hashing, CSRF, secrets, uploads, rate limiting | [security.md](references/security.md) |
| OAuth 2.1 flows, JWT claims, the auth filter, session cookies | [oauth2-and-jwt.md](references/oauth2-and-jwt.md) |
| Response headers, CORS, mutual TLS | [headers-cors-mtls.md](references/headers-cors-mtls.md) |
| Entities, Specifications, fetch strategy, N+1, projections, transactions | [jpa.md](references/jpa.md) |
| HikariCP sizing and alerts | [connection-pooling.md](references/connection-pooling.md) |
| Test slices, MockMvc, Testcontainers, fixtures, the JaCoCo gate | [testing.md](references/testing.md) |
| The pre-merge phases, scan commands, report template | [verification-pipeline.md](references/verification-pipeline.md) |
| A Javadoc block | [javadoc.md](references/javadoc.md) |
| Before calling a change or its review done | [checklist.md](references/checklist.md) |
