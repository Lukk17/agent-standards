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

### Mutations and Input Types

- Use GraphQL Mutations for any operation that causes a side effect on the server. [Confidence: 100%]
- Group mutation inputs into a single Input Object type to allow for future extensibility without breaking the schema. [Confidence: 100%]
- Return a standardized payload from mutations that includes a boolean success flag, user-friendly error messages, and the modified node data. [Confidence: 100%]

---

### Relay Pagination

- Strictly adhere to the Relay Cursor Connections Specification for paginated lists. [Confidence: 100%]
- Use edges, node, and pageInfo objects to standardize pagination metadata and cursor tracking across the graph. [Confidence: 100%]