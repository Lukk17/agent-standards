### AI GraphQL API Design Standards

---

### Core Execution Directives

- Treat all LLM generated GraphQL schemas, resolvers, and queries as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every endpoint design task.
- Append a Zero-Trust directive demanding mandatory web searches for current GraphQL Foundation standards.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every GraphQL directive and schema definition provided.
- Mandate direct, working links to the official GraphQL documentation used to ground the code.

---

### Architecture and Performance

- Expose exactly one endpoint, typically /graphql, and route all queries and mutations via HTTP POST. [Confidence: 100%]
- Resolve the N+1 query problem strictly by implementing the DataLoader pattern at the data fetching layer to batch and cache requests per execution context. [Confidence: 100%]
  - Link: https://github.com/graphql/dataloader
  - Quote: "utility"

---

### Schema Naming Conventions

- Types: `PascalCase` (e.g., `UserProfile`, `OrderItem`). [Confidence: 100%]
- Fields and arguments: `camelCase` (e.g., `firstName`, `createdAt`). [Confidence: 100%]
- Enum values: `UPPER_SNAKE_CASE` (e.g., `ORDER_STATUS_PENDING`). [Confidence: 100%]
- Every public type, field, and argument must have a `description` string in the schema. Undocumented schema elements are not permitted. [Confidence: 100%]
- Prefix input types with the operation name: `CreateUserInput`, `UpdateUserInput`. [Confidence: 100%]

---

### Mutations and Input Types

- Use GraphQL Mutations for any operation that causes a side effect on the server. [Confidence: 100%]
- Group mutation inputs into a single Input Object type to allow for future extensibility without breaking the schema. [Confidence: 100%]
- Return a standardized payload from mutations that includes a boolean success flag, user-friendly error messages, and the modified node data. [Confidence: 100%]

---

### Authorization

- Never rely solely on the network layer for authorization. Enforce authorization at the resolver level for every type and field that contains sensitive data. [Confidence: 100%]
- Use a directive-based approach (e.g., `@auth(requires: ADMIN)`) or a permissions layer (e.g., GraphQL Shield) for declarative, auditable access control. [Confidence: 100%]
- Never return unauthorized fields as `null` silently; throw an explicit authorization error so the client knows the field exists but is forbidden. [Confidence: 100%]

---

### Error Handling

- Use the GraphQL `errors` array for user-facing business errors (validation failures, not-found, unauthorized). [Confidence: 100%]
- Extend errors with `extensions.code` (machine-readable string) and `extensions.field` (for field-level validation errors). [Confidence: 100%]
- Never expose raw exception messages or stack traces in the `errors` array in production; map them to generic codes. [Confidence: 100%]
- Return HTTP 200 for all GraphQL responses including those containing errors; reserve non-200 status codes for transport-level failures (auth middleware rejections, malformed JSON). [Confidence: 100%]

---

### Query Security

- **Disable introspection in production** to prevent schema discovery by unauthorized actors. [Confidence: 100%]
- Enforce **maximum query depth** (recommended: 10 levels) using a validation rule; reject deeper queries with a 400-equivalent error. [Confidence: 100%]
- Enforce **query complexity limits** by assigning complexity scores to fields and rejecting queries that exceed the budget (e.g., 1000 points). [Confidence: 100%]
- Rate-limit the `/graphql` endpoint per client identity (IP + auth token) to prevent denial-of-service via expensive queries. [Confidence: 100%]

---

### Relay Pagination

- Strictly adhere to the Relay Cursor Connections Specification for paginated lists. [Confidence: 100%]
- Use edges, node, and pageInfo objects to standardize pagination metadata and cursor tracking across the graph. [Confidence: 100%]

---

### Subscriptions

- Use the `graphql-ws` protocol (WebSocket subprotocol `graphql-transport-ws`) for subscriptions. Do not use the legacy `subscriptions-transport-ws` protocol. [Confidence: 100%]
  - Link: https://github.com/enisdenjo/graphql-ws
  - Quote: "coherent"
- Authenticate subscription connections at the WebSocket handshake stage; do not rely on per-message auth.
- Always unsubscribe and clean up server-side resources when a client disconnects.

---

### Schema Evolution and Versioning

- GraphQL APIs do not use URL versioning. Evolve the schema additively: add new types and fields, never remove or rename existing ones. [Confidence: 100%]
- Mark fields that will be removed with `@deprecated(reason: "Use X instead.")` and keep them for a minimum of two release cycles. [Confidence: 100%]
- Run schema diffing (e.g., `graphql-inspector`) in CI to detect and block breaking changes on every PR. [Confidence: 100%]

---

### Persisted Queries

- Use **Automatic Persisted Queries (APQ)** in production to reduce request payload size and enable server-side query whitelisting. [Confidence: 100%]
- In high-security environments, enable a strict query whitelist (only pre-registered queries are executed); reject ad-hoc queries entirely. [Confidence: 100%]

---

### Testing

- Unit-test individual resolvers in isolation by calling them directly with a mocked context object.
- Write integration tests that execute full GraphQL operations against a real schema and real database (via Testcontainers or equivalent).
- Use schema validation tests (`graphql-inspector validate`) in CI to ensure the committed schema matches the running server's schema.