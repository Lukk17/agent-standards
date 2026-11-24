---
name: mongodb-patterns
description: 'MongoDB connection pooling, query and index tuning, schema design, Atlas Search and Vector Search. Use when the user says "how do I index this" or "embed vs reference". Not for PostgreSQL, use `postgres-patterns`.'
license: Apache-2.0
compatibility: >-
  Best with the MongoDB MCP server. Without it, work from the query shape and the code alone.
metadata:
  version: "1.1.0"
---

# MongoDB Patterns

Connections, query and index tuning, data modelling, and search.

Assume MongoDB 8.0 or newer on Atlas, and an officially supported driver.

---

### When not to activate

- Applying a schema or index change safely to a live cluster, use `database-migrations`.
- Relational modelling and tuning on PostgreSQL, use `postgres-patterns`.
- Idempotency, retries and graceful shutdown around the driver, use `backend-patterns`.

---

### Rules

1. Establish four facts first: deployment shape, topology, server version, and the workload.
2. Ask one question at a time, broad first, and when no answer comes, assume and say so. Every value carries its reason.
3. Measure through the MongoDB MCP server before advising, and say so when you could not.
4. Reads may run to verify a claim. Before any write or destructive call, state the operation, collection and documents affected, and wait for an unambiguous yes. Run MCP `--readOnly` unless writes are needed.
5. Data accessed together is stored together: model the queries an endpoint runs, not relational entities. Embed what is read and written together and bounded, reference the rest.
6. Index before rewriting. Order a compound index equality, sort, range (ESR), aim for a covered query, and keep a collection generally under 20 indexes.
7. Never `$regex` or `$text` for search. Show the Atlas Search equivalent.
8. Create the `MongoClient` once and reuse it, in serverless outside the handler, and close connections only at shutdown.

---

### Which reference to open for which task

| Area | Open |
| --- | --- |
| Rules | [full reasoning per rule](references/working-rules.md) |
| Connections | [pool sizing, timeouts, errors, churn](references/connection.md), [driver events and pool metrics](references/monitoring-guide.md) |
| Queries | [slow queries, `explain`, Performance Advisor](references/query-optimizer.md), [aggregation stage order and memory](references/aggregation-optimization.md), [oplog-efficient updates](references/update-query-examples.md) |
| Indexes | [ESR, sort direction, collation, covered queries](references/core-indexing-principles.md), [bad and good index forms](references/antipattern-examples.md) |
| Schema basics | [design principles, read first](references/schema-design.md), [embed or reference](references/fundamental-embed-vs-reference.md), [moving from relational](references/fundamental-document-model.md), [the 16MB limit](references/fundamental-document-size.md), [schema validation](references/fundamental-schema-validation.md) |
| Schema anti-patterns | [like data split across collections](references/antipattern-unnecessary-collections.md), [frequent `$lookup`](references/antipattern-excessive-lookups.md), [overlapping or unused indexes](references/antipattern-unnecessary-indexes.md) |
| Design patterns | [approximate counters](references/pattern-approximation.md), [cold storage](references/pattern-archive.md), [many optional fields](references/pattern-attribute.md), [IoT buckets](references/pattern-bucket.md), [precomputed results](references/pattern-computed.md), [audit history](references/pattern-document-versioning.md), [cached referenced fields](references/pattern-extended-reference.md), [a few huge documents](references/pattern-outlier.md), [mixed entity types](references/pattern-polymorphic.md), [schema evolution](references/pattern-schema-versioning.md), [native time series](references/pattern-time-series-collections.md) |
| Search | [decision rules, read first](references/search-and-ai.md), [analyzers, autocomplete, fuzzy](references/lexical-search-indexing.md), [operators, pagination, facets](references/lexical-search-querying.md), [`$vectorSearch` and RAG](references/vector-search.md), [`$rankFusion` and `$scoreFusion` hybrid search](references/hybrid-search.md) |
| Before calling the work done | [checklist](references/checklist.md) |
