---
name: mongodb-patterns
description: "MongoDB connection pooling, query and index tuning, schema design and anti-patterns, and Atlas Search, Vector Search and Hybrid Search. Use when the user says \"configure the connection pool\", \"how do I index this\", \"design this schema\", \"embed vs reference\" or \"combine keyword and semantic search\". Not for relational modelling on PostgreSQL, use `postgres-patterns`."
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
- The server version. MongoDB 8.0 adds `defaultMaxTimeMS` on Atlas, `$rankFusion` needs 8.0 and `$scoreFusion` 8.3.
- The workload. Read and write access patterns decide the document model, the indexes, and the pool size alike.

---

### When to activate

- Instantiating or configuring a MongoDB client, a connection pool, or driver timeouts.
- Diagnosing `ECONNREFUSED`, a socket timeout, pool exhaustion, or connection churn.
- Asking why a query is slow, which index it needs, or what the slow queries on a cluster are.
- Designing a new schema, reviewing an existing one, or migrating a relational model into documents.
- Hitting the 16MB document limit, an unbounded array, or an Atlas Schema Suggestion.
- Adding schema validation, or modelling time series, polymorphic, or versioned documents.
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

Every reference is listed here, so open the file for the task directly rather than routing through another reference.

Connections:

| Task | Reference |
| --- | --- |
| Pool sizing, timeouts, serverless reuse, connection errors, churn | [references/connection.md](references/connection.md) |
| Driver events, pool metrics, and the server connection counters to alert on | [references/monitoring-guide.md](references/monitoring-guide.md) |

Queries and indexes:

| Task | Reference |
| --- | --- |
| Slow queries, `explain` output, Performance Advisor, the diagnosis order | [references/query-optimizer.md](references/query-optimizer.md) |
| Compound index order, sort direction, collation, covered queries | [references/core-indexing-principles.md](references/core-indexing-principles.md) |
| Index anti-patterns with the bad and the good form side by side | [references/antipattern-examples.md](references/antipattern-examples.md) |
| Aggregation pipeline stage order, memory limits, disk spilling | [references/aggregation-optimization.md](references/aggregation-optimization.md) |
| Oplog-efficient updates and common update anti-patterns | [references/update-query-examples.md](references/update-query-examples.md) |

Schema design, starting from the principles in [references/schema-design.md](references/schema-design.md):

| Task | Reference |
| --- | --- |
| Embedding against referencing, relationship shapes, trees | [references/fundamental-embed-vs-reference.md](references/fundamental-embed-vs-reference.md) |
| Moving a relational model into documents | [references/fundamental-document-model.md](references/fundamental-document-model.md) |
| The 16MB limit and oversized documents | [references/fundamental-document-size.md](references/fundamental-document-size.md) |
| Schema validation on new or existing collections | [references/fundamental-schema-validation.md](references/fundamental-schema-validation.md) |
| Homogeneous data split across many collections | [references/antipattern-unnecessary-collections.md](references/antipattern-unnecessary-collections.md) |
| Over-normalised collections and frequent `$lookup` | [references/antipattern-excessive-lookups.md](references/antipattern-excessive-lookups.md) |
| Overlapping or unused indexes, and the hide, monitor, drop process | [references/antipattern-unnecessary-indexes.md](references/antipattern-unnecessary-indexes.md) |
| High-frequency counters that can be approximate | [references/pattern-approximation.md](references/pattern-approximation.md) |
| Moving historical data to cold storage | [references/pattern-archive.md](references/pattern-archive.md) |
| Many optional fields collapsed into key-value attributes | [references/pattern-attribute.md](references/pattern-attribute.md) |
| Grouping time-series or IoT data into buckets | [references/pattern-bucket.md](references/pattern-bucket.md) |
| Pre-computing expensive aggregations | [references/pattern-computed.md](references/pattern-computed.md) |
| Historical document state for audit and rollback | [references/pattern-document-versioning.md](references/pattern-document-versioning.md) |
| Caching fields from a referenced entity | [references/pattern-extended-reference.md](references/pattern-extended-reference.md) |
| A few documents far larger than the rest | [references/pattern-outlier.md](references/pattern-outlier.md) |
| Different entity types in one collection | [references/pattern-polymorphic.md](references/pattern-polymorphic.md) |
| Schema evolution, drift, and online migrations | [references/pattern-schema-versioning.md](references/pattern-schema-versioning.md) |
| Native time series collections | [references/pattern-time-series-collections.md](references/pattern-time-series-collections.md) |

Search, starting from the decision rules in [references/search-and-ai.md](references/search-and-ai.md):

| Task | Reference |
| --- | --- |
| Atlas Search index definitions, analyzers, autocomplete and fuzzy fields | [references/lexical-search-indexing.md](references/lexical-search-indexing.md) |
| Atlas Search query operators, compound queries, pagination, facets | [references/lexical-search-querying.md](references/lexical-search-querying.md) |
| Vector Search indexes, pre-filtering, and `$vectorSearch` queries for RAG | [references/vector-search.md](references/vector-search.md) |
| `$rankFusion`, `$scoreFusion`, and lexical prefilters for hybrid search | [references/hybrid-search.md](references/hybrid-search.md) |

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
