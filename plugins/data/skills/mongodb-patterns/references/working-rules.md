# Working rules in full

Open this for the full reasoning behind the baseline and the rules in [SKILL.md](../SKILL.md). Each topic file beside this one carries the depth for one area.

---

### Contents

- [Baseline](#baseline)
- [Gather context before recommending anything](#gather-context-before-recommending-anything)
- [Inspect the real cluster before guessing at it](#inspect-the-real-cluster-before-guessing-at-it)
- [Never run a write through MCP without explicit approval](#never-run-a-write-through-mcp-without-explicit-approval)
- [Data that is accessed together should be stored together](#data-that-is-accessed-together-should-be-stored-together)
- [Prefer an index over a rewrite, and order it by ESR](#prefer-an-index-over-a-rewrite-and-order-it-by-esr)
- [Never use $regex or $text for search](#never-use-regex-or-text-for-search)
- [Create the client once and reuse it](#create-the-client-once-and-reuse-it)

---

### Baseline

Assume MongoDB 8.0 or newer on Atlas, and an officially supported driver (Node.js, Python, Java, Go, C#, Ruby, PHP).
Four facts change what the right answer is, so establish them before advising anything:

- The deployment shape. Serverless functions, a long-running server, and an analytical job need different pools.
- The topology. Pools are per client and per server, so a replica set or a sharded cluster multiplies the total.
- The server version. MongoDB 8.0 adds `defaultMaxTimeMS` on Atlas, `$rankFusion` needs 8.0 and `$scoreFusion` 8.3.
- The workload. Read and write access patterns decide the document model, the indexes, and the pool size alike.

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
