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

Connections, query and index tuning, data modelling, and search. The rules apply to every MongoDB task, and each reference holds one area's depth.

Assume MongoDB 8.0 or newer on Atlas, and an officially supported driver (Node.js, Python, Java, Go, C#, Ruby, PHP).

---

### When to activate

- Instantiating or configuring a MongoDB client, a connection pool, or driver timeouts.
- Diagnosing `ECONNREFUSED`, a socket timeout, pool exhaustion, or connection churn.
- Asking why a query is slow, which index it needs, or what a cluster's slow queries are.
- Designing a new schema, reviewing an existing one, or migrating a relational model into documents.
- Hitting the 16MB document limit, an unbounded array, or an Atlas Schema Suggestion.
- Adding schema validation, or modelling time series, polymorphic, or versioned documents.
- Building full-text, autocomplete, fuzzy, faceted, semantic or hybrid search, or RAG retrieval over a collection.

---

### When not to activate

- Applying a schema or index change safely to a live cluster. Use `database-migrations`.
- Relational modelling, indexing, and tuning on PostgreSQL. Use `postgres-patterns`.
- Idempotency, retries, and graceful shutdown in the service around the driver. Use `backend-patterns`.
- Measuring the endpoint before blaming the database. Use `performance-optimization`.
- Language-neutral design rules such as SOLID and DRY. Use `coding-standards`.
- Reviewing a diff or a pull request for defects. Use `code-reviewer`.

---

### Rules

1. Establish four facts first: deployment shape (serverless, server and analytical job need different pools), topology (pools are per client and per server, so members multiply them), server version (Atlas `defaultMaxTimeMS` and `$rankFusion` need 8.0, `$scoreFusion` 8.3), and the workload.
2. Ask one question at a time, broad first, and when no answer comes, assume and say so. Every value carries its reason: `maxPoolSize` 50 from a peak of 40 plus 25 percent, never 100 by habit.
3. Measure through the MongoDB MCP server: `collection-schema`, `collection-indexes`, `explain`, `db-stats`, `atlas-get-performance-advisor`. Without a connection string or the Atlas API, say so and reason from the query shape.
4. Reads (`find`, `aggregate`, `collection-schema`, `db-stats`, `count`) may run to verify a claim. Before any write or destructive call, state the operation, collection and documents affected, and wait for an unambiguous yes. Run MCP `--readOnly` unless writes are needed.
5. Data accessed together is stored together: model the queries an endpoint runs, not relational entities. Embed when read and written together and bounded. Reference when accessed apart, many to many, or unbounded.
6. Index before rewriting. Order a compound index equality, sort, range (ESR), aim for a covered query, and keep a collection generally under 20 indexes, because each costs write throughput and memory.
7. Never `$regex` or `$text` for search: no relevance, fuzzy matching or language tokenisation, an unanchored pattern uses no index, and `$text` is legacy. Show the Atlas Search equivalent.
8. Create the `MongoClient` once and reuse it, in serverless outside the handler, and close connections only at shutdown. Server-side total is about `(maxPoolSize + 2) x replica set members x application instances`.

---

### Which reference to open for which task

Every reference is listed here, so open the one for the task directly. Each link text says when to open it.

| Area | Open |
| --- | --- |
| Rules | [the full reasoning behind each rule above](references/working-rules.md) |
| Connections | [pool sizing, timeouts, serverless reuse, errors, churn](references/connection.md), [driver events, pool metrics, alert counters](references/monitoring-guide.md) |
| Queries | [slow queries, `explain`, Performance Advisor](references/query-optimizer.md), [aggregation stage order and memory](references/aggregation-optimization.md), [oplog-efficient updates](references/update-query-examples.md) |
| Indexes | [ESR order, sort direction, collation, covered queries](references/core-indexing-principles.md), [bad and good index forms side by side](references/antipattern-examples.md) |
| Schema, read first | [design principles](references/schema-design.md) |
| Schema basics | [embed or reference](references/fundamental-embed-vs-reference.md), [moving from relational](references/fundamental-document-model.md), [the 16MB limit](references/fundamental-document-size.md), [schema validation](references/fundamental-schema-validation.md) |
| Schema anti-patterns | [like data split across collections](references/antipattern-unnecessary-collections.md), [frequent `$lookup`](references/antipattern-excessive-lookups.md), [overlapping or unused indexes](references/antipattern-unnecessary-indexes.md) |
| Design patterns | [approximate counters](references/pattern-approximation.md), [cold storage](references/pattern-archive.md), [many optional fields](references/pattern-attribute.md), [IoT buckets](references/pattern-bucket.md), [precomputed results](references/pattern-computed.md), [audit history](references/pattern-document-versioning.md), [cached referenced fields](references/pattern-extended-reference.md), [a few huge documents](references/pattern-outlier.md), [mixed entity types](references/pattern-polymorphic.md), [schema evolution](references/pattern-schema-versioning.md), [native time series](references/pattern-time-series-collections.md) |
| Search, read first | [search decision rules](references/search-and-ai.md) |
| Search | [analyzers, autocomplete, fuzzy](references/lexical-search-indexing.md), [operators, pagination, facets](references/lexical-search-querying.md), [`$vectorSearch` and RAG](references/vector-search.md), [`$rankFusion` and `$scoreFusion` hybrid search](references/hybrid-search.md) |

---

### Related skills

- `database-migrations` for changing a cluster already serving traffic.
- `postgres-patterns` for the relational half of a system that also runs MongoDB.
- `backend-patterns` for timeouts, retries, caching and pagination around the driver.
- `performance-optimization` for measuring the request before blaming the database.
- `coding-standards` for the cross-language floor, `code-reviewer` for reviewing a change.

---

### Checklist

- [ ] Deployment shape, topology, server version, and workload known or the assumption stated.
- [ ] The client is constructed once and reused, and in serverless lives outside the handler.
- [ ] Pool and timeout values have reasons, and the server-side connection total was calculated.
- [ ] Real indexes and schema inspected before proposing a new index or model.
- [ ] Compound indexes follow equality, sort, range, and no dead indexes remain.
- [ ] The model follows the access pattern, with no unbounded array and no document near 16MB.
- [ ] Search uses Atlas Search or Vector Search, never `$regex` or `$text`.
- [ ] Hybrid search was version checked before `$rankFusion` or `$scoreFusion` was suggested.
- [ ] No write, index creation, or destructive MCP call ran without explicit approval.
