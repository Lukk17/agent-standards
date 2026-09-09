---
name: mongodb-patterns
description: "MongoDB across connection pooling, query optimisation and indexing, schema design and anti-patterns, and Atlas Search, Vector Search and Hybrid Search. Use when you say \"configure the connection pool\", \"why do I get ECONNREFUSED or pool exhaustion\", \"how do I optimize this query\", \"how do I index this\", \"what are the slow queries on my cluster\", \"design this schema\", \"embed vs reference\", \"unbounded arrays\", \"16MB limit\", \"schema validation\", \"time series\", \"polymorphic\", \"document versioning\", \"add autocomplete or fuzzy matching\", \"build RAG over this collection\", or \"combine keyword and semantic search\". Not for applying a schema change safely to a live cluster, use `database-migrations`."
license: Apache-2.0
compatibility: >-
  Best with MongoDB MCP server. Uses collection-indexes, collection-schema and explain when the connection string
  works; uses Atlas Performance Advisor when the Atlas API is configured. Without either, work from the query shape
  and the code alone. The user creates indexes in Atlas or in a migration unless the tooling allows otherwise.
---

# MongoDB Patterns

Connection configuration, query and index tuning, data modelling, and search, with a reference file per area. The hub
carries the rules that apply to every MongoDB task, and each reference carries the depth for one of them.

---

### Baseline

Assume MongoDB 8.0 or newer on Atlas, and an officially supported driver (Node.js, Python, Java, Go, C#, Ruby, PHP).
Four facts change what the right answer is, so establish them before advising anything:

- The deployment shape. Serverless functions, a long-running server, and an analytical job need different pools.
- The topology. Pools are per client and per server, so a replica set or a sharded cluster multiplies the total.
- The server version. MongoDB 8.0 adds `defaultMaxTimeMS` on Atlas, `$rankFusion` needs 8.0 and `$scoreFusion` 8.2.
- The workload. Read and write access patterns decide the document model, the indexes, and the pool size alike.

---

### When to activate

- Instantiating or configuring a MongoDB client, a connection pool, or driver timeouts.
- Diagnosing `ECONNREFUSED`, a socket timeout, pool exhaustion, or connection churn.
- Asking why a query is slow, which index it needs, or what the slow queries on a cluster are.
- Designing a new schema, reviewing an existing one, or migrating a relational model into documents.
- Hitting the 16MB document limit, an unbounded array, or an Atlas Schema Suggestion.
- Building full-text search, autocomplete, fuzzy matching, faceted filtering, or semantic and hybrid search.
- Adding embeddings and retrieval for a RAG application on top of a collection.

---

### When not to activate

- Applying a schema or index change safely to a live production cluster. Use `database-migrations`.
- Relational modelling, indexing, and tuning on PostgreSQL. Use `postgres-patterns`.
- Idempotency, retries, and graceful shutdown in the service around the driver. Use `backend-patterns`.
- Measuring the endpoint before assuming the database is the bottleneck. Use `performance-optimization`.
- Language-neutral design rules such as SOLID, DRY, and error-handling shape. Use `coding-standards`.
- Reviewing a diff or a pull request for defects. Use `code-reviewer`.

---

### Gather context before recommending anything

Every area here fails the same way: a value applied without knowing the workload. A `maxPoolSize` copied from a blog
post, an index added because a field appeared in a filter, an embedded array chosen because the SQL table was joined.
Ask one question at a time, broad before specific, and when an answer never arrives make a reasonable assumption and
say out loud that you assumed it.

```text
GOOD: maxPoolSize 50, from your observed peak of 40 concurrent operations plus 25 percent headroom.
BAD:  maxPoolSize 100, because that is the default people use.
```

---

### Inspect the real cluster before guessing at it

The MongoDB MCP server turns most of this skill from advice into measurement. Use `collection-schema` for the real
field structure, `collection-indexes` for what already exists, `explain` for the plan, `db-stats` for size, and
`atlas-get-performance-advisor` for slow query logs and index suggestions. When neither the connection string nor the
Atlas API is available, say so plainly and reason from the query shape instead of pretending to have measured.

---

### Never run a write through MCP without explicit approval

Reads such as `find`, `aggregate`, `collection-schema`, `db-stats` and `count` are safe to run to verify a claim.
Anything that changes state (`create-index`, `update-many`, `insert-many`, `create-collection`) and anything
destructive (`delete-many`, `drop-collection`, `drop-database`) gets the same treatment first: state the exact
operation, name the collection and the estimated number of documents affected, then wait for an unambiguous yes.
Run the MCP server with `--readOnly` unless writes are genuinely needed.

---

### Data that is accessed together should be stored together

This is the one modelling rule the rest derive from. Design documents around the queries an endpoint actually runs,
not around the entities a relational schema happened to have. Embed when data is read and written together and the
array is bounded, reference when the sides are accessed independently, the relationship is many to many, or the array
can grow without limit. Queries and indexes cannot rescue a model that fights its own access pattern.

---

### Prefer an index over a rewrite, and order it by ESR

Most slow queries are an index problem, so reach for indexing first and rewrite the query second. Order a compound
index equality fields first, then the sort field, then the range fields. Aim for an index that covers the query so
the plan never touches the documents. Keep the count per collection sensible, generally under 20, because every index
costs write throughput and memory.

---

### Never use $regex or $text for search

Neither scales as a search feature. `$regex` has no relevance scoring, no fuzzy matching, and no language-aware
tokenization, and an unanchored pattern cannot use an index. `$text` is a legacy operator that does not hold up under
a real search workload. When a user asks for either, explain why and show the Atlas Search equivalent.

---

### Create the client once and reuse it

A `MongoClient` owns the pool, so constructing one per request destroys the reason pooling exists. In a serverless
runtime, build it outside the handler so warm invocations reuse it. Do not close connections manually except at
shutdown. Account for the monitoring connections when planning capacity: the total is roughly
`(maxPoolSize + 2) x replica set members x application instances`.

---

### Which reference to open for which task

Each entry below lists the deeper files for its own area, so open the entry first and let it route you further.

| Task | Reference |
| --- | --- |
| Pool sizing, timeouts, serverless reuse, connection errors, churn, pool monitoring | [references/connection.md](references/connection.md) |
| Slow queries, `explain` output, index choice, aggregation tuning, Performance Advisor | [references/query-optimizer.md](references/query-optimizer.md) |
| Embed versus reference, document model, validation, the 16MB limit, design patterns | [references/schema-design.md](references/schema-design.md) |
| Atlas Search, autocomplete and fuzzy matching, Vector Search, RAG, hybrid search | [references/search-and-ai.md](references/search-and-ai.md) |

---

### Related skills

- `database-migrations` for applying a schema or index change to a cluster that is already serving traffic.
- `postgres-patterns` for the relational half of a system that also runs MongoDB.
- `backend-patterns` for timeouts, retries, caching, and pagination in the service around the driver.
- `performance-optimization` for measuring the request before blaming the database.
- `coding-standards` for the cross-language engineering floor these patterns sit on.
- `code-reviewer` for reviewing a change against all of the above.

---

### Checklist

- [ ] The deployment shape, topology, server version, and workload are known or the assumption is stated.
- [ ] The client is constructed once and reused, and in serverless it lives outside the handler.
- [ ] Pool and timeout values each have a reason attached, and the server-side connection total was calculated.
- [ ] Existing indexes and the real schema were inspected before a new index or model was proposed.
- [ ] Compound indexes follow equality, sort, range, and the collection is not carrying dead indexes.
- [ ] The document model follows the access pattern, with no unbounded array and no document near 16MB.
- [ ] Search uses Atlas Search or Vector Search, never `$regex` or `$text`.
- [ ] Hybrid search was version checked before `$rankFusion` or `$scoreFusion` was suggested.
- [ ] No write, index creation, or destructive MCP call ran without explicit approval.
