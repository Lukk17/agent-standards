# Scope

Companion reference for the [backend-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Deciding whether an endpoint or a message handler is safe to call twice.
- Designing retries, timeouts, or a circuit breaker between two services.
- Choosing between a queue, an outbox, and a synchronous call for work that follows a write.
- Adding a cache and needing an invalidation rule rather than a TTL guess.
- Paginating a list endpoint that has outgrown offsets.
- Making a deployment or a restart invisible to callers.
- The user says "make this endpoint safe to retry", "our webhook fired twice", "design the job queue", "this list endpoint times out on page 900", or "we drop requests during a deploy".

---

### When not to activate

- Runtime and framework code: use `node-backend-patterns`, `springboot-patterns`, `python-patterns`, or
  `golang-patterns`.
- URL shape, status codes, versioning, and rate-limit headers: use `api-design`.
- Domain, port, and adapter boundaries: use `hexagonal-architecture`.
- Schema, index, and query-plan work: use `postgres-patterns` or `mongodb-patterns`.
- Safe schema change and backfills: use `database-migrations`.
- Log levels, tracing, metrics, and SLOs: use `observability-and-logging`.

---

### Related skills

- `node-backend-patterns` for the Node, Express, and Next.js implementation of these rules.
- `springboot-patterns` for the Java and Spring Boot implementation, including its JPA data access.
- `python-patterns` and `golang-patterns` for the Python and Go implementations.
- `api-design` for the HTTP contract, and `hexagonal-architecture` for the internal boundaries.
- `observability-and-logging` for correlation identifiers, metrics, and the readiness banner.
- `database-migrations` when a change to a stored shape has to survive a rolling deploy.
