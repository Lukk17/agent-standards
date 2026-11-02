---
name: api-design
description: 'HTTP and GraphQL contract design: resource naming, method and status semantics, RFC 9457 problem details, pagination, idempotency keys, conditional requests, health paths, rate-limit headers and tiers, and versioning. Use when the user says "design this endpoint", "what status code should this return", or "how do we deprecate v1". Not for the service code behind it, use `backend-patterns`.'
---

# API Design

Conventions for HTTP and GraphQL contracts that stay predictable as an API grows and gains external callers. The
contract is the deliverable here, so everything is about what goes on the wire and nothing about the code that produces
it.

HTTP semantics per RFC 9110, problem details per RFC 9457, contracts described in the OpenAPI version the project's
toolchain supports, GraphQL subscriptions over the `graphql-ws` protocol.

---

### When to activate

- Designing a new endpoint or reviewing an existing API contract.
- Choosing a status code, an error body, or a response envelope.
- Adding pagination, filtering, or sorting to a collection endpoint.
- Planning a versioning or deprecation path for a public or partner API.
- Deciding what an endpoint must accept to be safe to retry.
- The user says "design this endpoint", "what status code should this return", "review our API contract", "add
  cursor pagination to this list", or "how do we deprecate v1".

---

### When not to activate

- Service structure, layering, or data access behind the endpoint: use `backend-patterns`.
- Node, Express, or Next.js implementation of a handler: use `node-backend-patterns`.
- Spring Boot controllers and their error handling: use `springboot-patterns`.
- Authentication mechanics and token verification: use `security-review`. Threat modelling: use the `security-auditor`
  agent.
- SOAP and WSDL contracts: use `soap-webservices`.
- Writing the reference documentation for a finished contract: use `markdown-writer`.

---

### Reference map

| Task | Open |
| --- | --- |
| Applying a contract rule below: its reasoning, wire examples, the status code list, the problem details field table, the rate-limit headers | [references/contract-rules.md](references/contract-rules.md) |
| Pagination, filtering, sorting, search, sparse fieldsets | [references/pagination-and-filtering.md](references/pagination-and-filtering.md) |
| Versioning strategy, deprecation, and sunset headers | [references/versioning.md](references/versioning.md) |
| GraphQL schema, resolvers, and production hardening | [references/graphql.md](references/graphql.md) |
| A working handler in TypeScript, Python, or Go | [references/implementation-examples.md](references/implementation-examples.md) |

---

### Rules

1. Name resources as plural, kebab-case nouns, nest only for ownership, and use a verb segment only for a state transition no method expresses, such as `cancel` or `refund`.
2. Use the method that matches the semantics. PATCH is idempotent only when its body is a target state, not a delta.
3. Return the status code that describes what happened, never 200 carrying a failure. 201 carries `Location`, 304 answers an unchanged conditional GET, 422 is valid syntax with wrong meaning, 429 and 503 carry `Retry-After`, and 500 carries no internal detail.
4. Return errors as RFC 9457 `application/problem+json`, the one shape the `coding-standards` error rule points to: `type`, `title` and `status` always (clients must not require the optional ones), `detail` and `instance` when they help, an `errors` array of `detail` and JSON `pointer` on validation. No stack trace, SQL or vendor text.
5. Wrap success responses in one consistent envelope (`data`, `meta`, `links`) on a public API; a bare resource is fine internally if every endpoint does it, never a mix. Cursor pagination is the default for unbounded collections, offset for small fixed sets.
6. Require an `Idempotency-Key` on non-idempotent writes: none is 400, the response is stored for 24 hours, the same key and body replays, a different body is 422, still running is 409. The storage behind it is `backend-patterns`'s.
7. Support conditional requests: `ETag` and `Last-Modified` on cacheable GETs, 304 for `If-None-Match` and `If-Modified-Since`, and `If-Match` on PUT or PATCH with 412 on a mismatch.
8. Return 207 from `POST /resources/batch` with per-item outcomes, cap items and body size with 413, and document whether the batch is atomic.
9. Keep liveness and readiness separate. This is the canonical definition of the paths: `GET /health` checks nothing external, `GET /ready` returns 503 when this instance cannot serve, both outside the versioned path, and no other skill renames them. What readiness checks is `observability-and-logging`'s.
10. Advertise rate limits on every response. This is the canonical definition of the headers, the 429 and the tiers: `X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset` (UTC epoch seconds) on successes too, and a 429 problem body with `Retry-After`. Add `RateLimit` and `RateLimit-Policy` once draft-ietf-httpapi-ratelimit-headers is an RFC, and document the value format sent. Every public endpoint sits in a tier below, the keying policy is `security-review`'s, and other skills implement without restating.
11. Version in the path, keep at most two active versions, give a deprecated one at least six months with `Deprecation` and `Sunset`, then return 410 Gone.

| Tier | Keyed on | Applies to |
| --- | --- | --- |
| Anonymous | Client address | Public endpoints |
| Authenticated | User | Standard API access |
| Expensive | User, or client address when anonymous | Search, export, and anything that scans or fans out |
| Authentication | Client address, plus a failed-attempt counter per target account with backoff | Login, password reset, signup |
| Premium | API key | Paid plans |
| Internal | Calling service | Service-to-service calls |

The values belong to each application, set from measured load and documented: Expensive and Authentication stay tighter than Authenticated, and Anonymous stays tighter than Authenticated.

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
- [ ] Every error body is RFC 9457 `application/problem+json`, and leaks no internal detail.
- [ ] The success envelope is consistent across every endpoint on the surface.
- [ ] List endpoints paginate, default to cursors when unbounded, and cap page size server-side.
- [ ] Non-idempotent POST and PATCH require `Idempotency-Key`, with 409 while the first attempt is in flight.
- [ ] Cacheable GETs return `ETag` and `Last-Modified` and honour the conditional headers.
- [ ] Bulk endpoints return 207 with per-item results and bound the batch.
- [ ] `/health` and `/ready` exist, are separate, and sit outside the versioned path.
- [ ] `X-RateLimit-*` headers are on every rate-limited response, with `Retry-After` on the 429.
- [ ] Deprecated endpoints carry `Deprecation` and `Sunset` and return 410 after the date.
- [ ] Input is schema-validated and authorization is checked per resource, not only per role.
- [ ] The OpenAPI description is updated in the same change as the endpoint.
