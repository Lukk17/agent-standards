### AI REST API Design Standards

---

### Core Execution Directives

- Treat all LLM generated REST schemas, payloads, and routing logic as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every endpoint design task.
- Append a Zero-Trust directive demanding mandatory web searches for current OpenAPI specifications.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every HTTP status code and query parameter provided.
- Mandate direct, working links to the official API documentation used to ground the code.

---

### Resource Naming and Methods

- Model APIs around resources, not actions. Use nouns for endpoint paths, not verbs. [Confidence: 100%]
- Use standard HTTP methods to represent actions. GET for retrieval, POST for creation, PUT for full replacement, PATCH for partial updates, and DELETE for removal. [Confidence: 100%]
- Maintain hierarchical logic in paths. Use /resources/identifier/sub-resources to represent nested relationships. [Confidence: 100%]
- Enforce camelCase for all JSON request and response body properties to ensure consistency across web clients. [Confidence: 100%]

---

### API Versioning

- Use URI path versioning as the default strategy: `/api/v1/`, `/api/v2/`. [Confidence: 100%]
- Never remove or change the semantics of a versioned endpoint without first introducing a new version and deprecating the old one.
- Signal deprecation via the `Deprecation` response header (RFC 8594) and the `Sunset` header with the planned removal date. [Confidence: 100%]
- Maintain at least one prior major version in production for a minimum of 6 months after a new version is released.

---

### OpenAPI Specification

- Every REST API must have an OpenAPI 3.1 specification committed to the repository and verified in CI. [Confidence: 100%]
- Describe every endpoint with `operationId`, `summary`, `tags`, and all possible response schemas including error codes.
- Declare security schemes (`bearerAuth`, `apiKey`, `oauth2`) on every endpoint that requires authentication.
- Generate client SDKs and server stubs from the OpenAPI spec as the single source of truth; do not hand-write code that duplicates the spec.

---

### Status Codes and Error Payloads

- Map application states to proper HTTP status codes. Use 200 OK, 201 Created, 204 No Content for successes. Use 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict for client errors. [Confidence: 100%]
- Standardize error responses using a consistent envelope. Include a top-level error object containing a machine-readable code, a human-readable message, and an innererror object for deep context. [Confidence: 100%]
  - Link: https://learn.microsoft.com/en-us/azure/architecture/microservices/design/api-design
  - Quote: "when"
- Never leak stack traces or internal server implementation details in a 500 Internal Server Error payload. [Confidence: 100%]

---

### REST Pagination

- Implement cursor-based pagination instead of offset-based pagination for large datasets to prevent skipped or duplicated records. [Confidence: 100%]
- Provide next-page links directly in the API response payload or use the HTTP Link header to achieve HATEOAS compliance. [Confidence: 100%]
- Always include a `totalCount` field when the full set size is known and computationally cheap to retrieve.

---

### Filtering, Sorting, and Searching

- Use query parameters for filtering: `?filter[status]=active&filter[role]=admin`. [Confidence: 100%]
- Use a `sort` parameter with comma-separated field names; prefix with `-` for descending order: `?sort=-createdAt,name`. [Confidence: 100%]
- Use a `q` parameter for full-text search queries. Limit search to explicitly documented fields.
- Document all supported filter fields and sort keys in the OpenAPI spec; reject unsupported values with 400 and a descriptive error.

---

### Rate Limiting Headers

- Return rate limit metadata on every response from rate-limited endpoints: [Confidence: 100%]
  - `X-RateLimit-Limit`: total requests allowed in the window.
  - `X-RateLimit-Remaining`: requests remaining in the current window.
  - `X-RateLimit-Reset`: UTC epoch timestamp when the window resets.
  - `Retry-After`: seconds to wait (returned only on 429 responses).

---

### Idempotency

- Require clients to send an `Idempotency-Key` header (UUID v4) for all non-idempotent POST and PATCH operations that create or modify resources. [Confidence: 100%]
- Cache the response for a given Idempotency-Key for a minimum of 24 hours; return the cached response for duplicate requests within that window.
- Return 422 if an Idempotency-Key is reused with a different request body.

---

### Caching Headers

- Return `ETag` (resource version hash) and `Last-Modified` headers on cacheable GET responses. [Confidence: 100%]
- Support conditional requests: honour `If-None-Match` (returns 304 if ETag matches) and `If-Modified-Since`.
- Set explicit `Cache-Control` directives: `no-store` for sensitive data, `private, max-age=N` for user-specific resources, `public, max-age=N` for shared resources.

---

### Bulk Operations

- Provide a `POST /resources/batch` endpoint for bulk creates when more than one resource is commonly created together.
- Limit bulk request body size; return 413 Payload Too Large if the limit is exceeded.
- Process bulk operations atomically where possible; if partial success is allowed, return a multi-status (207) response with per-item results.

---

### Health and Readiness Endpoints

- Expose `/health` (liveness) and `/ready` (readiness) endpoints outside the versioned API path (no `/v1/` prefix). [Confidence: 100%]
- `/health` returns 200 if the process is alive; it must never check external dependencies.
- `/ready` returns 200 only when all critical dependencies (database, required caches) are reachable; returns 503 otherwise.