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
