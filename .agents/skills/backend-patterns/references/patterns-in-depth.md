# Patterns in Depth

Contents:

- [Make every non-idempotent operation replayable](#make-every-non-idempotent-operation-replayable)
- [Give every outbound call a deadline before you give it a retry](#give-every-outbound-call-a-deadline-before-you-give-it-a-retry)
- [Do the work later, but decide first whether it may be lost](#do-the-work-later-but-decide-first-whether-it-may-be-lost)
- [Publish through an outbox when the job must follow a committed write](#publish-through-an-outbox-when-the-job-must-follow-a-committed-write)
- [A cache needs an invalidation rule, not just a TTL](#a-cache-needs-an-invalidation-rule-not-just-a-ttl)
- [Paginate large reads with a cursor, and always bound the page](#paginate-large-reads-with-a-cursor-and-always-bound-the-page)
- [Separate liveness from readiness, and drain on shutdown](#separate-liveness-from-readiness-and-drain-on-shutdown)
- [Layering and contracts live in their own skills](#layering-and-contracts-live-in-their-own-skills)

Every backend rule in SKILL.md in full, with its reasoning, its pseudocode, the IETF Idempotency-Key citation, and its failing form. Load this file when designing or reviewing one of these patterns and the one-line summary in SKILL.md is not enough.

---

### Make every non-idempotent operation replayable

A caller that times out cannot tell a lost request from a lost response, so it retries, and the charge happens twice.
Accept a client-supplied key and claim it before the effect runs, so a concurrent second attempt finds the claim rather
than an empty table. A `select ... for update` on a key that does not exist yet locks nothing, which is why the claim
is an insert. Store the response once the effect finishes and replay it on a repeat. When the effect is an external
call, such as a charge, pass the same key downstream so the provider deduplicates too. When the effect is local, such
as rows in the same database, run the effect and the `done` update in one transaction, so a crash between them cannot
leave the effect applied and the key still claimed.

A claim needs a lease. Record `claimed_at` with the claim, and let a retry take over a claim older than the lease,
which is longer than the slowest successful attempt. Without it, a worker that dies after the claim leaves the key
answering 409 forever.

```text
on POST /orders with Idempotency-Key K:
  insert idempotency (key = K, request_hash = hash(body), state = 'in_progress', claimed_at = now())
    on conflict do nothing
  if no row inserted:
    row = select from idempotency where key = K
    if row.request_hash != hash(body): return 422      # key reused for a different request
    if row.state = 'done':            return row.response   # replay
    taken = update idempotency set claimed_at = now()
              where key = K and state = 'in_progress' and claimed_at < now() - LEASE
    if taken is 0 rows:               return 409      # the first attempt is still running
  result = perform the operation (pass K downstream as the provider's idempotency key)
  update idempotency set state = 'done', response = result where key = K
  if the operation fails: delete from idempotency where key = K   # the retry is safe, K deduplicates downstream
```

The 409 for a request still in flight follows the IETF Idempotency-Key draft, which says a retry "while the original
request is still being processed" SHOULD get a 409 (draft-ietf-httpapi-idempotency-key-header, section 2.7).

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
honour    = Retry-After on 429 and 503 when present, capped by the budget
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

This section is the canonical cache invalidation rule. `performance-optimization` decides when a measurement justifies
adding a cache at all, and follows this rule once it does.

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
changes between pages. Which kind fits which list, and the request parameters and response fields, are defined by
`api-design` in its `references/pagination-and-filtering.md`. This section
covers the query behind a cursor page.

```text
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
them makes a transient dependency failure trigger a restart loop that fixes nothing. The two paths are the ones
`api-design` defines, and what readiness checks, including which dependencies stay out of it, is owned by
`observability-and-logging`.

```text
GET /health   -> 200 while the process is alive; checks nothing external
GET /ready    -> 200 when this instance can serve; 503 while starting or draining; body lists each check

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
