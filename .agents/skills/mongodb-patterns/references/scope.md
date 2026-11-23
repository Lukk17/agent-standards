# Scope

Companion reference for the [mongodb-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Instantiating or configuring a MongoDB client, a connection pool, or driver timeouts.
- Diagnosing `ECONNREFUSED`, a socket timeout, pool exhaustion, or connection churn.
- Asking why a query is slow, which index it needs, or what a cluster's slow queries are.
- Designing a new schema, reviewing an existing one, or migrating a relational model into documents.
- Hitting the 16MB document limit, an unbounded array, or an Atlas Schema Suggestion.
- Adding schema validation, or modelling time series, polymorphic, or versioned documents.
- Building full-text, autocomplete, fuzzy, faceted, semantic or hybrid search, or RAG retrieval over a collection.
- The user says "configure the connection pool", "how do I index this", "design this schema", "embed vs reference" or "combine keyword and semantic search".

---

### When not to activate

- Applying a schema or index change safely to a live cluster. Use `database-migrations`.
- Relational modelling, indexing, and tuning on PostgreSQL. Use `postgres-patterns`.
- Idempotency, retries, and graceful shutdown in the service around the driver. Use `backend-patterns`.
- Measuring the endpoint before blaming the database. Use `performance-optimization`.
- Language-neutral design rules such as SOLID and DRY. Use `coding-standards`.
- Reviewing a diff or a pull request for defects. Use `code-reviewer`.

---

### Related skills

- `database-migrations` for changing a cluster already serving traffic.
- `postgres-patterns` for the relational half of a system that also runs MongoDB.
- `backend-patterns` for timeouts, retries, caching and pagination around the driver.
- `performance-optimization` for measuring the request before blaming the database.
- `coding-standards` for the cross-language floor, `code-reviewer` for reviewing a change.
