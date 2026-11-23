---
name: api-design
description: 'HTTP and GraphQL contract design: naming, status codes, problem details, pagination, versioning. Use when the user says "design this endpoint" or "how do we deprecate v1". Not for service code, use `backend-patterns`.'
metadata:
  version: "1.1.0"
---

# API Design

Conventions for HTTP and GraphQL contracts that stay predictable as an API grows and gains external callers. The contract is the deliverable here, so everything is about what goes on the wire and nothing about the code that produces it.

HTTP semantics per RFC 9110, problem details per RFC 9457, contracts described in the OpenAPI version the project's toolchain supports, GraphQL subscriptions over the `graphql-ws` protocol.

---

### When not to activate

- Service structure, layering, or data access behind the endpoint, use `backend-patterns`.
- The handler code that serves the contract, use `node-backend-patterns` or `springboot-patterns`.
- Authentication mechanics and token verification, use `application-security-review`.

---

### Rules

1. Name resources as plural, kebab-case nouns, nest only for ownership, and use a verb segment only for a state transition no method expresses, such as `cancel` or `refund`.
2. Use the method that matches the semantics. PATCH is idempotent only when its body is a target state, not a delta.
3. Return the status code that describes what happened, never 200 carrying a failure. 201 carries `Location`, 429 and 503 carry `Retry-After`, and 500 carries no internal detail.
4. Return errors as RFC 9457 `application/problem+json`, the one shape the `coding-standards` error rule points to: `type`, `title` and `status` always, an `errors` array on validation, and no stack trace, SQL or vendor text.
5. Wrap success responses in one consistent envelope (`data`, `meta`, `links`) on a public API, never a mix of wrapped and bare. Cursor pagination is the default for unbounded collections, offset for small fixed sets.
6. Require an `Idempotency-Key` on non-idempotent writes: none is 400, the same key and body replays the stored response, a different body is 422, still running is 409.
7. Support conditional requests: `ETag` and `Last-Modified` on cacheable GETs with a 304, and `If-Match` on PUT or PATCH with 412 on a mismatch.
8. Return 207 from `POST /resources/batch` with per-item outcomes, cap items and body size with 413, and document whether the batch is atomic.
9. Keep liveness and readiness separate. This is the canonical definition of the paths: `GET /health` checks nothing external, `GET /ready` returns 503 when this instance cannot serve, both outside the versioned path, and no other skill renames them.
10. Advertise rate limits on every response. This is the canonical definition of the headers, the 429 and the tiers: `X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset` on successes too, a 429 problem body with `Retry-After`, and every public endpoint in one tier of the tiers table (Anonymous, Authenticated, Expensive, Authentication, Premium, Internal). Other skills implement without restating.
11. Version in the path, keep at most two active versions, give a deprecated one at least six months with `Deprecation` and `Sunset`, then return 410 Gone.

---

### Reference map

| Task | Open |
| --- | --- |
| Applying a rule above: its reasoning, wire examples, the status code list, the problem details fields, the rate-limit headers and the tiers table | [contract-rules.md](references/contract-rules.md) |
| Pagination, filtering, sorting, search, sparse fieldsets | [pagination-and-filtering.md](references/pagination-and-filtering.md) |
| Versioning strategy, deprecation, and sunset headers | [versioning.md](references/versioning.md) |
| GraphQL schema, resolvers, and production hardening | [graphql.md](references/graphql.md) |
| A working create handler as a Next.js route handler in TypeScript | [nextjs.md](references/nextjs.md) |
| The same handler in Python on Django REST Framework | [django-rest.md](references/django-rest.md) |
| The same handler in Go on `net/http` | [go.md](references/go.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling a contract or its review done | [checklist.md](references/checklist.md) |
