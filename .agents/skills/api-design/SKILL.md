---
name: api-design
description: HTTP and GraphQL contract design covering resource naming, method and status-code semantics, RFC 7807 error bodies, pagination, idempotency, conditional requests, health endpoints, rate-limit headers and tiers, and versioning. Use when you say "design this endpoint", "what status code should this return", "review our API contract", "add cursor pagination to this list", or "how do we deprecate v1". Not for the service code behind the endpoint, use `backend-patterns`.
---

# API Design

Conventions for HTTP and GraphQL contracts that stay predictable as an API grows and gains external callers. The
contract is the deliverable here, so everything is about what goes on the wire and nothing about the code that produces
it.

Standards baseline, current as of September 2026: HTTP semantics per RFC 9110, problem responses per RFC 7807,
descriptions written in OpenAPI 3.1, GraphQL over the `graphql-ws` transport.

---

### When to activate

- Designing a new endpoint or reviewing an existing API contract.
- Choosing a status code, an error body, or a response envelope.
- Adding pagination, filtering, or sorting to a collection endpoint.
- Planning a versioning or deprecation path for a public or partner API.
- Deciding what an endpoint must accept to be safe to retry.

---

### When not to activate

- Service structure, layering, or data access behind the endpoint: use `backend-patterns`.
- Node, Express, or Next.js implementation of a handler: use `node-backend-patterns`.
- Spring Boot controllers and their error handling: use `springboot-patterns`.
- Authentication mechanics, token verification, and threat modelling: use `security-review`.
- SOAP and WSDL contracts: use `soap-webservices`.
- Writing the reference documentation for a finished contract: use `markdown-writer`.

---

### Reference map

| Task | Open |
| --- | --- |
| Pagination, filtering, sorting, search, sparse fieldsets | [references/pagination-and-filtering.md](references/pagination-and-filtering.md) |
| Versioning strategy, deprecation, and sunset headers | [references/versioning.md](references/versioning.md) |
| GraphQL schema, resolvers, and production hardening | [references/graphql.md](references/graphql.md) |
| A working handler in TypeScript, Python, or Go | [references/implementation-examples.md](references/implementation-examples.md) |

---

### Name resources as plural nouns

A URL identifies a thing. The method says what you are doing to it, so a verb in the path duplicates the method and
splits one resource across several names.

```text
# PASS
GET    /api/v1/team-members
GET    /api/v1/users/123/orders
POST   /api/v1/orders/456/cancel

# FAIL
GET    /api/v1/getUsers
GET    /api/v1/user
GET    /api/v1/team_members
GET    /api/v1/users/123/getOrders
```

Use kebab-case for multi-word resources, nest only to express ownership, and reserve a verb path segment for a genuine
state transition that no method expresses, such as `cancel` or `refund`.

---

### Use the method that matches the semantics

| Method | Idempotent | Safe | Use for |
| --- | --- | --- | --- |
| GET | Yes | Yes | Retrieving a resource |
| POST | No | No | Creating a resource, triggering an action |
| PUT | Yes | No | Replacing a resource in full |
| PATCH | Not inherently | No | Updating part of a resource |
| DELETE | Yes | No | Removing a resource |

PATCH becomes idempotent when the body describes a target state rather than a delta. `{"status": "shipped"}` is
idempotent, `{"increment_views": 1}` is not.

---

### Return the status code that describes what happened

```text
200 OK                     GET, PUT, PATCH with a response body
201 Created                POST, with a Location header pointing at the new resource
204 No Content             DELETE, or PUT with no body to return
207 Multi-Status           a bulk operation with per-item outcomes
304 Not Modified           a conditional GET whose resource is unchanged
400 Bad Request            malformed syntax, unparseable JSON
401 Unauthorized           missing or invalid credentials
403 Forbidden              authenticated, and still not allowed
404 Not Found              no such resource, or its existence is confidential
409 Conflict               duplicate, or a state that forbids this transition
422 Unprocessable Content  syntactically valid, semantically wrong
429 Too Many Requests      rate limit exceeded, with Retry-After
500 Internal Server Error  unexpected failure, never with internal detail
502 Bad Gateway            an upstream dependency failed
503 Service Unavailable    overloaded or draining, with Retry-After
```

Fail: `HTTP 200` carrying `{"status": 200, "success": false, "error": "Not found"}`, which forces every client to parse
the body before it knows whether the call worked, and defeats caches, proxies, and retry logic alike.

---

### Return errors as problem+json

Every error body uses `Content-Type: application/problem+json` and the RFC 7807 shape, so one client-side handler covers
every endpoint.

```json
{
  "type": "https://example.com/errors/validation",
  "title": "Validation Failed",
  "status": 422,
  "detail": "3 fields failed validation",
  "instance": "/orders/123",
  "errors": [
    { "field": "email", "message": "Invalid format", "code": "INVALID_EMAIL" }
  ]
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `type` | Yes | URI identifying the problem class, stable across releases |
| `title` | Yes | Short human-readable summary of the class |
| `status` | Yes | The HTTP status code, repeated for clients that lost it |
| `detail` | No | What went wrong on this occurrence |
| `instance` | No | URI of this specific occurrence |
| `errors` | No | Extension array of field-level failures |

Fail: a body carrying a stack trace, an SQL fragment, or an upstream vendor's error text. `detail` is for the caller,
not for your logs.

---

### Wrap success responses in a consistent envelope

```json
{
  "data": [{ "id": "abc-123", "name": "Alice" }],
  "meta": { "has_next": true, "next_cursor": "eyJpZCI6MTQzfQ" },
  "links": { "self": "/api/v1/users?limit=20", "next": "/api/v1/users?limit=20&cursor=eyJpZCI6MTQzfQ" }
}
```

A `data` wrapper leaves room to add `meta` and `links` later without breaking clients, which is why it suits public
APIs. Returning the bare resource is fine for an internal API, provided every endpoint does it. What is never fine is
mixing the two across one surface.

Cursor pagination is the default for any collection that grows without bound. Offset is for small fixed sets. The
mechanics, plus filtering and sorting, are in
[references/pagination-and-filtering.md](references/pagination-and-filtering.md).

---

### Require an idempotency key on non-idempotent writes

A client that times out cannot tell a lost request from a lost response. Give it a safe way to retry.

```text
POST /api/v1/orders
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

- Store the response for 24 hours, keyed by the idempotency key.
- The same key with the same request body replays the stored response without re-executing.
- The same key with a different body returns 422.

---

### Support conditional requests on cacheable reads

Return `ETag` and `Last-Modified` on cacheable GETs, and honour `If-None-Match` and `If-Modified-Since` with a 304. The
same `ETag` in `If-Match` on a PUT or PATCH gives you optimistic concurrency for free: a mismatch is a 412.

```text
HTTP/1.1 200 OK
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
Last-Modified: Tue, 15 Jan 2025 10:30:00 GMT
```

---

### Return 207 from bulk endpoints, and bound the batch

Use `POST /resources/batch` for bulk work and report per-item outcomes, because one failed item must not discard the
other ninety-nine.

```json
{
  "results": [
    { "id": "1", "status": 201, "data": {} },
    { "id": "2", "status": 422, "error": "Invalid email" }
  ]
}
```

Cap the number of items and the body size, and return 413 when a caller exceeds either. Process atomically when the
domain requires it, and say which behaviour applies in the documentation.

---

### Keep liveness and readiness separate

```text
GET /health   liveness:  200 while the process runs, checks nothing external
GET /ready    readiness: 200 when dependencies are usable, 503 otherwise
```

```json
{ "status": "degraded", "checks": { "db": "ok", "redis": "timeout" } }
```

Both sit outside the versioned path, because they describe the process rather than the API. Fail: one `/health` that
checks the database, so a transient outage makes the orchestrator restart a perfectly healthy process.

---

### Advertise rate limits on every response

This section is the canonical definition of the rate-limit headers and tiers for this repository. Other skills
implement it and must not restate the values.

```text
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1714000000
```

```text
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1714000000
Retry-After: 60
Content-Type: application/problem+json

{ "type": "https://example.com/errors/rate-limit-exceeded", "title": "Too Many Requests", "status": 429 }
```

`X-RateLimit-Reset` is a UTC epoch in seconds. Send the three headers on successful responses too, because a client
cannot back off from a budget it cannot see.

| Tier | Limit | Window | Applies to |
| --- | --- | --- | --- |
| Anonymous | 30/min | Per IP | Public endpoints |
| Authenticated | 100/min | Per user | Standard API access |
| Premium | 1000/min | Per API key | Paid plans |
| Internal | 10000/min | Per service | Service-to-service calls |

---

### Version in the path, and announce every retirement

Put the version in the URL, keep at most two active versions, and give a deprecated one at least six months. Announce
the end on the response with `Deprecation` and `Sunset`, then return 410 Gone after the date. The full policy, including
which changes need a version at all, is in [references/versioning.md](references/versioning.md).

---

### Related skills

- `backend-patterns` for idempotency storage, retries, and readiness behind the contract.
- `node-backend-patterns` and `springboot-patterns` for handler-level implementations.
- `hexagonal-architecture` for keeping transport concerns out of the domain.
- `security-review` before exposing an endpoint that touches credentials, payments, or personal data.
- `soap-webservices` when the contract is WSDL rather than HTTP and JSON.
- `observability-and-logging` for correlating a request identifier across services.

---

### Checklist

- [ ] Resource URLs are plural, kebab-case nouns with no verbs outside genuine state transitions.
- [ ] The method matches the semantics, and PATCH bodies describe a target state.
- [ ] Status codes are used semantically, never 200 for a failure.
- [ ] Every error body is `application/problem+json` and leaks no internal detail.
- [ ] The success envelope is consistent across every endpoint on the surface.
- [ ] List endpoints paginate, default to cursors when unbounded, and cap page size server-side.
- [ ] Non-idempotent POST and PATCH require `Idempotency-Key`.
- [ ] Cacheable GETs return `ETag` and `Last-Modified` and honour the conditional headers.
- [ ] Bulk endpoints return 207 with per-item results and bound the batch.
- [ ] `/health` and `/ready` exist, are separate, and sit outside the versioned path.
- [ ] `X-RateLimit-*` headers are on every rate-limited response, with `Retry-After` on the 429.
- [ ] Deprecated endpoints carry `Deprecation` and `Sunset` and return 410 after the date.
- [ ] Input is schema-validated and authorization is checked per resource, not only per role.
- [ ] The OpenAPI description is updated in the same change as the endpoint.
