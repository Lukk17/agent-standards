---
name: backend-patterns
description: 'Language-neutral backend design: idempotency, retries, the outbox, caches, shutdown. Use when the user says "make this endpoint safe to retry" or "our webhook fired twice". Not for HTTP contracts, use `api-design`.'
metadata:
  version: "1.1.0"
---

# Backend Patterns

Design rules for backend services that hold regardless of language or framework: what makes a write safe to repeat, what a retry may and may not do, and how a service stays correct while it is being replaced. Every example is pseudocode, because the decision is the deliverable and the syntax belongs in a runtime skill.

This skill owns the design of timeouts, capped retries, circuit breakers, graceful shutdown, and the cache invalidation rule. `observability-and-logging` owns the logs, metrics, and traces that watch them, and does not restate these rules.

HTTP semantics per RFC 9110, problem details per RFC 9457, contracts described in the OpenAPI version the project's toolchain supports.

| Task | Open |
| --- | --- |
| Designing or reviewing a pattern below: its reasoning, its pseudocode, the IETF citation, and its failing form | [patterns-in-depth.md](references/patterns-in-depth.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling a backend design or its review done | [checklist.md](references/checklist.md) |

---

### When not to activate

- Runtime and framework code, use `node-backend-patterns`, `springboot-patterns`, `python-patterns`, or `golang-patterns`.
- URL shape, status codes, versioning, and rate-limit headers, use `api-design`.
- Domain, port, and adapter boundaries, use `hexagonal-architecture`.

---

### Rules

1. Make every non-idempotent operation replayable. Accept a client-supplied key that identifies the attempt, not the content, and claim it with an insert before the effect runs. A repeat with a different body gets 422, a finished key replays the stored response, and one still in flight gets 409. The claim carries a lease, so a dead worker's claim can be taken over, and the key goes downstream to an external effect.
2. Give every outbound call a deadline before a retry: a per-attempt timeout, a capped attempt count, jittered backoff, retry only on timeout, connection error, 429, 502, 503 and 504, honour `Retry-After` within the budget, never retry 400, 401, 403, 404, 409 or 422 or an unkeyed POST, and keep the total under the caller's deadline. A circuit breaker opens on a failure ratio, serves a fallback, and lets one probe through before closing.
3. Do the work later, but decide first whether it may be lost. Lossy work may fire and forget, and work whose loss is a defect goes on a durable at-least-once queue with a dead-letter queue. Enqueue the identifier, not the object, and make the handler idempotent.
4. Publish through an outbox when a job must follow a committed write: insert the outbox row in the same transaction, and a relay claims, publishes and marks rows. Never `save` then `publish` inline.
5. A cache needs an invalidation rule, not just a TTL. This is the canonical rule, which `performance-optimization` follows once a measurement justifies a cache. Decide what the cache may be wrong about, evict in the same function as the write, version the key, never cache a per-caller response under a key without the caller, and on a cache error log at warn and read the origin.
6. Paginate large reads with a cursor and always bound the page. Seek on an indexed, immutable, tie-broken key, fetch one extra row for `has_next`, cap `limit` server-side, and keep the cursor opaque. Parameters and response fields are `api-design`'s.
7. Separate liveness from readiness, and drain on shutdown. `/health` checks nothing external, `/ready` returns 503 while starting or draining. On `SIGTERM`, fail readiness, wait for the balancer, stop accepting, finish in-flight work under a hard timer, close pools, exit. What readiness checks is `observability-and-logging`'s.
8. Layering and contracts live in their own skills: transport, application and infrastructure layers depending inward, with boundaries owned by `hexagonal-architecture` and the contract, including rate-limit headers and tiers, by `api-design`.
