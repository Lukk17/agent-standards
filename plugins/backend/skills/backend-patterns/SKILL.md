---
name: backend-patterns
description: 'Language-neutral backend service design: idempotency keys, timeouts and capped retries, the transactional outbox, the cache invalidation rule, cursor reads, and graceful shutdown. Use when the user says "make this endpoint safe to retry", "our webhook fired twice", or "we drop requests during a deploy". Not for the HTTP contract itself, use `api-design`.'
---

# Backend Patterns

Design rules for backend services that hold regardless of language or framework: what makes a write safe to repeat,
what a retry may and may not do, and how a service stays correct while it is being replaced. Every example is
pseudocode, because the decision is the deliverable and the syntax belongs in a runtime skill.

This skill owns the design of timeouts, capped retries, circuit breakers, graceful shutdown, and the cache
invalidation rule.
`observability-and-logging` owns the logs, metrics, and traces that watch them, and does not restate these rules.

HTTP semantics per RFC 9110, problem details per RFC 9457, contracts described in the OpenAPI version the project's
toolchain supports.

| Task | Open |
| --- | --- |
| Designing or reviewing a pattern below: its reasoning, its pseudocode, the IETF citation, and its failing form | [references/patterns-in-depth.md](references/patterns-in-depth.md) |

---

### When to activate

- Deciding whether an endpoint or a message handler is safe to call twice.
- Designing retries, timeouts, or a circuit breaker between two services.
- Choosing between a queue, an outbox, and a synchronous call for work that follows a write.
- Adding a cache and needing an invalidation rule rather than a TTL guess.
- Paginating a list endpoint that has outgrown offsets.
- Making a deployment or a restart invisible to callers.
- The user says "make this endpoint safe to retry", "our webhook fired twice", "design the job queue", "this list
  endpoint times out on page 900", or "we drop requests during a deploy".

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

### Rules

1. Make every non-idempotent operation replayable. Accept a client-supplied key that identifies the attempt, not the content, and claim it with an insert before the effect runs (a `select ... for update` on a missing key locks nothing). A repeat with a different body gets 422, a finished key replays the stored response, and one still in flight gets 409 per the IETF Idempotency-Key draft. The claim carries a `claimed_at` lease longer than the slowest success, so a dead worker's claim can be taken over. Pass the key downstream for an external effect; run a local effect and the `done` update in one transaction; delete the key when the operation fails.
2. Give every outbound call a deadline before a retry: a per-attempt timeout, a capped attempt count, jittered backoff, retry only on timeout, connection error, 429, 502, 503 and 504, honour `Retry-After` within the budget, never retry 400, 401, 403, 404, 409 or 422 or an unkeyed POST, and keep the total under the caller's deadline. A circuit breaker opens on a failure ratio, serves a fallback, and lets one probe through before closing.
3. Do the work later, but decide first whether it may be lost. Lossy work may fire and forget; work whose loss is a defect goes on a durable at-least-once queue with a dead-letter queue. Enqueue the identifier, not the object, and make the handler idempotent.
4. Publish through an outbox when a job must follow a committed write: insert the outbox row in the same transaction, and a relay claims, publishes and marks rows. Never `save` then `publish` inline.
5. A cache needs an invalidation rule, not just a TTL. This is the canonical rule, which `performance-optimization` follows once a measurement justifies a cache. Decide what the cache may be wrong about, evict in the same function as the write, version the key (`<entity>:<schema version>:<id>`), never cache a per-caller response under a key without the caller, and on a cache error log at warn and read the origin.
6. Paginate large reads with a cursor and always bound the page. Seek on an indexed, immutable, tie-broken key, fetch one extra row for `has_next`, cap `limit` server-side, and keep the cursor opaque. Parameters and response fields are `api-design`'s.
7. Separate liveness from readiness, and drain on shutdown. `/health` checks nothing external, `/ready` returns 503 while starting or draining. On `SIGTERM`, fail readiness, wait for the balancer, stop accepting, finish in-flight work under a hard timer, close pools, exit. What readiness checks is `observability-and-logging`'s.
8. Layering and contracts live in their own skills: transport, application and infrastructure layers depending inward, with boundaries owned by `hexagonal-architecture` and the contract, including rate-limit headers and tiers, by `api-design`.

---

### Related skills

- `node-backend-patterns` for the Node, Express, and Next.js implementation of these rules.
- `springboot-patterns` for the Java and Spring Boot implementation, including its JPA data access.
- `python-patterns` and `golang-patterns` for the Python and Go implementations.
- `api-design` for the HTTP contract, and `hexagonal-architecture` for the internal boundaries.
- `observability-and-logging` for correlation identifiers, metrics, and the readiness banner.
- `database-migrations` when a change to a stored shape has to survive a rolling deploy.

---

### Checklist

- [ ] Every non-idempotent write accepts and enforces an idempotency key.
- [ ] Every outbound call has a timeout, and every retry has a cap, jitter, and a retryable-error list.
- [ ] Work that may not be lost goes through a durable queue with a dead-letter destination.
- [ ] Messages that must follow a committed write are published from an outbox, not inline.
- [ ] Every cached key has a named invalidation trigger, and cache failure degrades throughput only.
- [ ] Idempotency keys are claimed before the effect, a request still in flight gets 409, and the key goes downstream.
- [ ] Retries honour `Retry-After` on 429 and 503.
- [ ] List endpoints over unbounded data use cursor pagination with a server-side maximum page size.
- [ ] `/health` and `/ready` are separate, and `SIGTERM` drains before exit.
- [ ] Layering follows `hexagonal-architecture` and the contract follows `api-design`.
