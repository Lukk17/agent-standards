# Scope

Companion reference for the [node-backend-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Structuring an Express app or a Next.js `app/api` route into handler, service, and repository layers.
- The user says "structure my Express API", "fix the N+1 in this route", "cache this Prisma query", "rate limit this endpoint", or "my Node app never exits on SIGTERM".
- Removing an N+1 query or a `SELECT *` from a Node data-access path.
- Adding Redis caching, a rate limiter, or a background queue to a Node service.
- Wiring typed configuration, pino logging, or a graceful shutdown handler.
- Reviewing a Node service for error-handling and validation gaps.

---

### When not to activate

- Language-neutral backend design (idempotency, outbox, retries as a concept): use `backend-patterns`.
- HTTP contract questions such as URL shape, status codes, or pagination style: use `api-design`.
- Java or Spring services: use `springboot-patterns`. Python: use `python-patterns`. Go: use `golang-patterns`.
- Next.js rendering, Server Components, caching, or Server Actions: use `nextjs-app-router-patterns`.
- Port and adapter boundaries and dependency inversion: use `hexagonal-architecture`.
- SQL schema, index, and query-plan work: use `postgres-patterns`.

---

### Related skills

- `backend-patterns` for the language-neutral rules these patterns implement.
- `api-design` for URL shape, status codes, pagination, and the canonical rate-limit headers and problem body.
- `hexagonal-architecture` for the port and adapter boundaries behind the repository interface.
- `nextjs-app-router-patterns` for the rendering and caching half of a Next.js app.
- `postgres-patterns` and `database-migrations` for schema, indexes, and safe schema change.
- `observability-and-logging` for the startup banner, log levels, and trace correlation.
- `application-security-review` before shipping auth, payment, or personal-data handling.
- `api-design` for auth headers, the rate-limit tier table, and `ETag`, `Cache-Control` and conditional requests on the wire.
- `application-security-review` for session fixation, input handling, and brute-force and credential-stuffing defence beyond a request count, and the `security-auditor` agent for threat modelling.
- `keycloak-patterns` when the identity provider is Keycloak, for both the server and the .NET client.
- `postgres-patterns` for `FOR UPDATE SKIP LOCKED` queue mechanics and advisory locks, and when the right fix is an index rather than a cache.
- `observability-and-logging` for tracing a job back to its originating request.
