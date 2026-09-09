---
name: backend-patterns
description: Language-neutral backend service design covering idempotency keys, timeouts and capped retries, the transactional outbox, cache invalidation, pagination of large reads, and graceful shutdown with liveness and readiness. Use when you say "make this endpoint safe to retry", "our webhook fired twice", "design the job queue", "this list endpoint times out on page 900", or "we drop requests during a deploy". Not for runtime-specific code, use `node-backend-patterns` or `springboot-patterns`.
---

# Backend Patterns

Design rules for backend services that hold regardless of language or framework: what makes a write safe to repeat,
what a retry may and may not do, and how a service stays correct while it is being replaced. Every example is
pseudocode, because the decision is the deliverable and the syntax belongs in a runtime skill.

Standards baseline, current as of September 2026: HTTP semantics per RFC 9110, error bodies per RFC 7807, service
contracts described in OpenAPI 3.1.

---

### When to activate

- Deciding whether an endpoint or a message handler is safe to call twice.
- Designing retries, timeouts, or a circuit breaker between two services.
- Choosing between a queue, an outbox, and a synchronous call for work that follows a write.
- Adding a cache and needing an invalidation rule rather than a TTL guess.
- Paginating a list endpoint that has outgrown offsets.
- Making a deployment or a restart invisible to callers.

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

### Make every non-idempotent operation replayable

A caller that times out cannot tell a lost request from a lost response, so it retries, and the charge happens twice.
Accept a client-supplied key, store it with the result inside the same transaction as the effect, and replay the stored
response on a repeat.

```text
on POST /orders with Idempotency-Key K:
  begin transaction
    row = select from idempotency where key = K for update
    if row exists and row.request_hash == hash(body): return row.response      # replay
    if row exists and row.request_hash != hash(body): return 422               # key reused
    result = perform the operation
    insert idempotency (key = K, request_hash = hash(body), response = result)
  commit
```

Fail: keying the record on the request body alone, so two genuinely distinct orders for the same amount collapse into
one. The key comes from the caller and identifies the attempt, not the content.

---

### Give every outbound call a deadline before you give it a retry

A retry on top of an unbounded wait multiplies the outage instead of absorbing it. Set the timeout first, then bound the
attempts, then add jitter so every client does not wake at the same instant.

```text
timeout   = 2s per attempt
attempts  = 3 maximum
backoff   = min(2^n * 200ms + random(0..200ms), 10s)
retry on  = timeout, connection error, 429, 502, 503, 504
never on  = 400, 401, 403, 404, 409, 422
budget    = total time across attempts < the caller's own deadline
```

Fail: retrying a 422, which fails identically every time, or retrying a POST that has no idempotency key, which
duplicates the effect the caller was trying to avoid.

When a dependency fails persistently, stop calling it. A circuit breaker that opens after a failure ratio, serves a
fallback while open, and lets one probe through before closing turns a slow cascade into a fast, contained error.

---

### Do the work later, but decide first whether it may be lost

Move anything the caller does not need in the response off the request path: emails, indexing, thumbnails, webhooks.
Then answer one question before choosing a mechanism.

| Loss is acceptable | Loss is a defect |
| --- | --- |
| Fire and forget after the response | Durable queue, at-least-once, with a dead-letter queue |
| Metrics, cache warming | Payments, notifications, downstream state changes |

Enqueue the identifier, not the object, so the worker reads current data. Assume at-least-once delivery, which makes an
idempotent handler mandatory rather than defensive.

---

### Publish through an outbox when the job must follow a committed write

Writing a row and publishing a message are two systems, and there is no transaction across both. If the publish wins
and the transaction rolls back, a consumer acts on a record that does not exist.

```text
begin transaction
  insert into orders (...)
  insert into outbox (topic = 'order.created', payload = {...})
commit

relay loop:
  claim a batch of unpublished outbox rows (skip rows another relay locked)
  publish each to the broker
  mark published
```

Fail: `save(order)` followed by `broker.publish(event)`, which produces phantom events on rollback and lost events on a
crash between the two lines.

---

### A cache needs an invalidation rule, not just a TTL

Decide what the cache is allowed to be wrong about before you decide how long it holds. Write the invalidation in the
same function that performs the write, and treat the TTL as the backstop for the key you forgot.

```text
read:   value = cache.get(key) ?? origin.load(key) then cache.put(key, value, ttl)
write:  origin.save(entity) then cache.evict(key(entity))
key:    <entity>:<schema version>:<id>            # bump the version to roll out a shape change
never:  cache a response whose content depends on who asked, under a key that omits the asker
```

A cache outage must degrade throughput, not availability: on a cache error, log at warn and read the origin.

Fail: a 24-hour TTL on a permission lookup, so a revoked role stays effective until tomorrow.

---

### Paginate large reads with a cursor, and always bound the page

Offset pagination makes the database scan and discard every skipped row, and it skips or repeats rows when the data
changes between pages. Use it only for small, fixed sets where a user expects page numbers.

```text
GET /orders?limit=20&cursor=<opaque>

  decode cursor -> (last_sort_value, last_id)
  select ... where (sort_key, id) > (last_sort_value, last_id)
  order by sort_key, id
  limit 21                        # one extra row answers has_next
  next_cursor = encode(last row)
```

Sort on an indexed, immutable, tie-broken key, and cap `limit` server-side so a caller cannot ask for the whole table.
Return the cursor opaque, so its encoding stays yours to change.

---

### Separate liveness from readiness, and drain on shutdown

Liveness answers whether the process should be restarted. Readiness answers whether it should receive traffic. Merging
them makes a transient dependency failure trigger a restart loop that fixes nothing.

```text
GET /health   -> 200 while the process is alive; checks nothing external
GET /ready    -> 200 when dependencies are usable, 503 otherwise; body lists each check

on SIGTERM:
  mark /ready as 503                 # the load balancer stops sending new work
  wait for the balancer to notice    # one or two probe intervals
  stop accepting new connections
  finish in-flight requests and jobs, bounded by a hard timer
  close pools and connections, then exit
```

Fail: exiting on `SIGTERM` immediately, which drops every in-flight request on every deploy.

---

### Layering and contracts live in their own skills

Keep the request path split into a transport layer that parses and responds, an application layer that holds the rule,
and an infrastructure layer that talks to the outside. Depend inward, and let each side effect be an interface the
application owns.

`hexagonal-architecture` is the authority on those boundaries, on where the port interfaces live, and on the composition
root that wires the adapters. `api-design` is the authority on the contract itself: resource naming, status codes, error
bodies, pagination parameters, versioning, and the rate-limit headers and tiers. Do not restate either here.

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
- [ ] List endpoints use cursor pagination with a server-side maximum page size.
- [ ] `/health` and `/ready` are separate, and `SIGTERM` drains before exit.
- [ ] Layering follows `hexagonal-architecture` and the contract follows `api-design`.
