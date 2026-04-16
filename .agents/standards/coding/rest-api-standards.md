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