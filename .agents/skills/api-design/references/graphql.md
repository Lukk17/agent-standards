# GraphQL API standards

Read this when designing a GraphQL schema, writing resolvers, or hardening a GraphQL endpoint for production.

---

### Schema naming

- Types are `PascalCase`: `UserProfile`, `OrderItem`.
- Fields are `camelCase`: `createdAt`, `totalAmount`.
- Enum values are `UPPER_SNAKE_CASE`: `ORDER_STATUS_PENDING`.
- Input types carry an `Input` suffix: `CreateOrderInput`.
- Mutation payload types carry a `Payload` suffix: `CreateOrderPayload`.
- Every field carries a description, enforced by schema linting rather than by review.

---

### Mutation payloads

Every mutation returns the same envelope, so a client handles one error shape instead of two. Business failures travel
in `errors`, not as transport-level GraphQL errors, which are reserved for malformed or unauthorized requests.

```graphql
type CreateOrderPayload {
  success: Boolean!
  errors: [UserError!]!
  order: Order
}

type UserError {
  field: String
  message: String!
  code: String!
}
```

---

### Prevent N+1 with a per-request loader

A naive resolver runs one query per parent object. Batch the lookups with DataLoader, and construct the loader once per
request so its cache never leaks across users.

```typescript
const userLoader = new DataLoader(async (ids: readonly string[]) => {
  const users = await db.users.findMany({ where: { id: { in: [...ids] } } })
  return ids.map((id) => users.find((u) => u.id === id) ?? null)
})
```

Fail: a module-level loader shared by every request, which serves one user's cached row to the next.

---

### Authorize at the field, and say so

Check authorization at field level and return an explicit error. Returning `null` for a field the caller may not see is
indistinguishable from a missing value, and clients build wrong logic on it. Use a shield or a directive so the rule is
declarative, rather than an `if` at the top of every resolver.

---

### Production hardening

A public GraphQL endpoint is a query engine pointed at your database, so the defaults are not safe.

- Disable introspection in production.
- Enforce a query depth limit (10 levels is a workable default).
- Assign a cost per field and reject queries above a complexity threshold.
- Use Automatic Persisted Queries so clients send a hash, which shrinks payloads and lets a CDN cache reads.
- Apply the same rate limiting as REST, keyed on the caller, and count complexity rather than request count.

---

### Pagination follows Relay cursor connections

Use the Relay Cursor Connections specification for every paginated field, so one client library handles all of them.

```graphql
type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}
type UserEdge {
  node: User!
  cursor: String!
}
type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

---

### Subscriptions

Use the `graphql-ws` protocol. The older `subscriptions-transport-ws` is unmaintained and its server implementations
have known denial-of-service issues.

---

### Evolve the schema additively

A GraphQL schema has no URL version to bump, so evolution is additive only.

- Never remove or rename a field or type without a deprecation cycle.
- Mark the old field `@deprecated(reason: "Use totalAmountMinor instead")`.
- Diff the schema in CI with `graphql-inspector` and fail the build on a breaking change.

---

### Related skills

- `api-design` for the REST half of the contract and the shared rate-limit rules.
- `node-backend-patterns` for resolver and data-loader wiring in a Node service.
- `security-review` before exposing a GraphQL endpoint to the public internet.
