# API Design Checklist

Run it before calling a contract, or a review of one, done.

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
