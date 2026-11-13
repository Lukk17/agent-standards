---
name: springboot-patterns
description: "Spring Boot 4 services on blocking Spring MVC, covering layering, RFC 9457 errors, RestClient with Resilience4j, caching and events, Spring Security 7, JPA and HikariCP, Testcontainers tests and the pre-merge pipeline. Use when the user says \"structure this Spring Boot API\" or \"add JWT auth to this endpoint\". Not for Java language style, naming and records, use `java-coding-standards`."
license: Apache-2.0
metadata:
  version: "1.0.0"
---

# Spring Boot Patterns

How a production Spring Boot service is put together, from controller to database, its security, tests and pipeline. Each reference carries the depth for one area.

Written for Spring Boot 4, with the Spring Security 7, Hibernate 7, Jackson 3 and JUnit 6 that ship with it, on blocking Spring MVC with virtual threads. WebFlux is out of scope, and Spring Boot 3 is an upgrade target, as the core rules reference explains.

---

### When to activate

- Building or restructuring a REST API on Spring MVC: layering, validation, errors, pagination, OpenAPI and outbound calls.
- The user says "structure this Spring Boot API", "add JWT auth to this endpoint", "why does this query run two hundred times", "write a @WebMvcTest for this controller", or "verify this before I open the PR".
- Caching, asynchronous work, events, authentication, authorization, CORS, headers or rate limiting.
- Entities, queries, fetch strategy, an N+1 query, or connection pool sizing.
- Tests, slices, Testcontainers, the coverage gate, and the pipeline before a merge or deploy.

---

### When not to activate

- Java language style, naming, immutability, and `Optional`, use `java-coding-standards`.
- Ports and adapters layering across the whole service, use `hexagonal-architecture`.
- Log format, metrics, tracing, and the startup readiness banner, use `observability-and-logging`.
- Schema change and rollout mechanics, use `database-migrations`.
- PostgreSQL query planning and index internals, use `postgres-patterns`.
- Language-neutral security review checklists, use `application-security-review`. Threat modelling goes to the `security-auditor` agent.
- Configuring Keycloak itself as the identity provider, use `keycloak-patterns`.
- Version catalogs, BOM imports, and dependency admission, use `build-dependency-management`.

---

### Rules

1. The controller parses and returns, the service holds the behaviour and the transaction, the repository reaches the database. No controller touches a repository.
2. No entity and no Spring Data `Page` on the wire. The service maps to a DTO and a project-owned `PageResponse` envelope.
3. Every error is `application/problem+json` from a `ProblemDetail` built in one `@ControllerAdvice`, field errors as a problem property, with `spring.mvc.problemdetails.enabled=true`.
4. Call out through one `RestClient` bean per upstream with explicit timeouts, wrapped in Resilience4j retry with backoff and jitter, a circuit breaker and a degrading fallback. Never `RestTemplate`, `WebClient`, or a `Thread.sleep` loop.
5. `@Transactional` sits on service methods only, `readOnly = true` on query paths. A self-call bypasses the proxy, so extract the method into another bean.
6. Every cache has `@EnableCaching`, a time to live, a size bound, and a `@CacheEvict` written in the same change.
7. Deny by default with `@EnableMethodSecurity` and a `@PreAuthorize` beside the method it guards, and reject bad payloads with `@Valid` constrained DTOs before business code runs.
8. Write the failing test first, in the narrowest slice: JUnit and Mockito with `@InjectMocks` for services, `@WebMvcTest` for the web layer, `@DataJpaTest` with digest-pinned Testcontainers images for repositories, `@SpringBootTest` only for wiring.
9. Apply the production defaults: tunables in `application.yml` per `java-coding-standards`, virtual threads on, `ddl-auto=validate` with migrations owning the schema, a sized HikariCP, `/api/v1/` paths, and a `Sunset` date on anything deprecated.
10. The startup readiness block belongs to `observability-and-logging`, emitted from an `@EventListener(ApplicationReadyEvent.class)` method, never `ApplicationStartedEvent`.
11. Query through a `Specification` or a derived method, aggregates through the Criteria API on them. Never an `@Query` JPQL or native string, which no compiler checks, and an ArchUnit rule guards it. Whole-table backup and restore is the one exception.
12. Every endpoint carries composable OpenAPI response meta-annotations with its honest success code, and error responses name the project's own problem schema, because generated clients trust the spec.

---

### Javadoc

Javadoc follows `java-coding-standards`, which carries the Java delta of the `coding-standards` Doc Comments rules. Nothing about Spring changes it.

---

### Which reference to open for which task

| Task | Reference |
| --- | --- |
| A hub rule needs its Pass and Fail example, the baseline detail, the production defaults, or the related skills | [references/core-rules.md](references/core-rules.md) |
| Controllers, DTOs, validation, the pagination envelope, the exception handler, versioning, OpenAPI response annotations | [references/rest-api-and-validation.md](references/rest-api-and-validation.md) |
| RestClient beans, Resilience4j retry and circuit breaker settings, timeouts, fallbacks | [references/outbound-and-resilience.md](references/outbound-and-resilience.md) |
| Redis cache manager, `@Async` executors, transactional events, scheduled jobs, request filters | [references/caching-async-and-events.md](references/caching-async-and-events.md) |
| Authentication, method authorization, SQL injection, password hashing, CSRF, secrets, uploads, rate limiting | [references/security.md](references/security.md) |
| OAuth 2.1 flows, refresh token rotation, JWT claim validation, the auth filter, session cookies | [references/oauth2-and-jwt.md](references/oauth2-and-jwt.md) |
| The full response header block, the CORS configuration source, mutual TLS between services | [references/headers-cors-mtls.md](references/headers-cors-mtls.md) |
| Entity mapping, Specifications instead of query strings, fetch strategy, N+1, projections, transactions, paging, indexing | [references/jpa.md](references/jpa.md) |
| HikariCP sizing formula, pool configuration, utilisation alerts | [references/connection-pooling.md](references/connection-pooling.md) |
| Test slices, `@InjectMocks`, test comments and size, MockMvc, pinned Testcontainers, fixtures, the JaCoCo gate | [references/testing.md](references/testing.md) |
| The six pre-merge phases, the scan commands, the report template, the re-run loop | [references/verification-pipeline.md](references/verification-pipeline.md) |

---

### Checklist

- [ ] Controllers parse and return, services hold behaviour, repositories reach the database, nothing skips a layer.
- [ ] No entity and no Spring Data `Page` appears in a response body.
- [ ] Every error response is a `ProblemDetail` from one `@ControllerAdvice`.
- [ ] Outbound HTTP goes through `RestClient`, with a retry, a circuit breaker, and explicit timeouts.
- [ ] `@Transactional` sits on service methods only, with `readOnly = true` on query paths.
- [ ] Every cache has a TTL, a size bound, and an eviction path.
- [ ] Every sensitive path carries an authorization rule, and every request body is a validated DTO.
- [ ] No association is eager, every paged query has a sort, and no N+1 is left as a follow-up.
- [ ] Every behaviour change started with a test that failed for the right reason, in the narrowest slice.
- [ ] No `@Query` string, every read a `Specification` or derived method, guarded by ArchUnit.
- [ ] Every endpoint has the OpenAPI response meta-annotations, honest codes and the problem schema.
- [ ] Repository tests run on the production engine through digest-pinned Testcontainers.
- [ ] The verification pipeline ran in order and every gate is green before the pull request opens.
