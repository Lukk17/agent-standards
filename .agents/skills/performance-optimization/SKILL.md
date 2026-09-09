---
name: performance-optimization
description: Measure-first performance work for application code and data access, covering profiling, N+1 queries, fetch and index discipline, caching with an invalidation rule, streaming, and concurrent IO. Use when you say "this endpoint is slow", "the page takes four seconds to load", "profile this before I change anything", "did my change regress latency", or "this query runs inside a loop". Not for schema and index design on Postgres itself, use `postgres-patterns`.
---

# Performance Optimization

Make slow things fast without guessing, because performance work that is not driven by a measurement is decoration. The
cross-cutting principles hub is the `coding-standards` skill and this skill is the optimisation detail on top of it.

---

### When to activate

- An application, endpoint, or job is slow, or a deployment regressed a latency or throughput metric.
- You need a baseline before optimising, or want to confirm an optimisation actually moved the metric.
- Reviewing a change for an obvious performance trap: a query inside a loop, an unbounded fetch, sequential awaits of
  unrelated calls.

---

### When not to activate

- Designing a table, choosing a column type, or writing a migration. Use `postgres-patterns` for the schema and
  `database-migrations` for the change.
- Writing the tests that prove the fix holds. Use `tdd-workflow`, or the language skill (`python-patterns`,
  `golang-patterns`, `springboot-patterns`).
- Reducing container image size or build time. Use `docker-patterns`.
- Frontend rendering and bundle weight in a specific framework. Use `nextjs-app-router-patterns` or `angular`.
- A general code review that happens to mention speed. Use `code-reviewer` and pull this skill in for the performance
  findings only.

---

### Measure before you change anything

Profile, find the one real bottleneck, fix that one thing, then measure again. The bottleneck is almost never where
intuition points, and a change that moves cost from one layer to another looks like a win in the code and like nothing
in production.

Set a target before you start, a latency budget or a throughput number, so you know when to stop.

Fail: the diagnosis is a guess and the fix is unverifiable.

```text
The list page feels slow, so I added a cache to the serializer.
```

Pass: the diagnosis names a measured number, and the same measurement is repeated after.

```text
p95 for GET /orders was 1.8s. A profile showed 1.6s in 340 individual customer lookups.
Target: p95 under 300ms. After batching the lookups, p95 measured 210ms.
```

---

### Avoid the N+1 query

One query per row in a loop is the most common cause of a slow endpoint. Batch the related lookups into a single query,
or let the ORM fetch the relation eagerly.

Fail: one query for the list, then one more per row.

```python
orders = order_repository.list_recent(limit=100)
for order in orders:
    order.customer = customer_repository.get(order.customer_id)
```

Pass: one query for the list, one for every customer it references.

```python
orders = order_repository.list_recent(limit=100)
customers = customer_repository.get_many({order.customer_id for order in orders})
for order in orders:
    order.customer = customers[order.customer_id]
```

The same shape appears in every stack: `JOIN FETCH` or an entity graph in JPA, `select_related` / `prefetch_related` in
Django, a DataLoader in a GraphQL resolver. Confirm the fix by counting the queries the request issues, not by looking
at the code.

---

### Fetch and index only what is needed

Select the columns the caller actually reads and page large result sets rather than loading the whole table. Add the
indexes the real queries need, and confirm with the database's own query plan that they are used. An index nobody
queries is write cost for no read benefit.

Fail: unbounded and over-wide.

```sql
SELECT * FROM events WHERE tenant_id = $1 ORDER BY created_at DESC;
```

Pass: narrow, bounded, and backed by an index on `(tenant_id, created_at DESC)`.

```sql
SELECT id, kind, created_at FROM events WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 50 OFFSET $2;
```

---

### Cache with a stated invalidation rule

Cache where reads dominate and the data tolerates slight staleness. Name the staleness you accept and the event that
clears the entry, because a cache without an invalidation story is a correctness bug waiting to surface.

Fail: no expiry and no invalidation, so a rename never reaches readers.

```python
_cache: dict[str, Product] = {}

def get_product(product_id: str) -> Product:
    if product_id not in _cache:
        _cache[product_id] = product_repository.get(product_id)
    return _cache[product_id]
```

Pass: bounded lifetime, and the write path clears the entry it invalidated.

```python
def get_product(product_id: str) -> Product:
    cached = cache.get(f"product:{product_id}")
    if cached is not None:
        return cached
    product = product_repository.get(product_id)
    cache.set(f"product:{product_id}", product, ttl_seconds=300)
    return product

def rename_product(product_id: str, name: str) -> None:
    product_repository.rename(product_id, name)
    cache.delete(f"product:{product_id}")
```

---

### Keep memory bounded

Build a string from many pieces with a join or a buffer, never by repeated concatenation in a loop. Stream large data
lazily instead of loading all of it, because a file or result set that fits today overflows tomorrow.

Fail: the whole export is materialised in memory before the first byte is sent.

```python
rows = [format_row(row) for row in repository.fetch_all_orders()]
return Response("".join(rows), media_type="text/csv")
```

Pass: the rows are produced and released one at a time.

```python
def row_stream():
    for row in repository.iter_orders(chunk_size=1000):
        yield format_row(row)

return StreamingResponse(row_stream(), media_type="text/csv")
```

---

### Run independent IO concurrently

Sequential awaits of unrelated calls waste the whole duration of every call but the slowest. Start them together and
join once.

Fail (TypeScript): three independent calls cost the sum of their latencies.

```typescript
const profile = await api.getProfile(userId)
const orders = await api.getOrders(userId)
const preferences = await api.getPreferences(userId)
```

Pass (TypeScript): they cost the slowest one.

```typescript
const [profile, orders, preferences] = await Promise.all([
  api.getProfile(userId),
  api.getOrders(userId),
  api.getPreferences(userId),
])
```

Fail (Go): the same serial shape.

```go
profile, err := client.Profile(ctx, userID)
if err != nil {
    return err
}
orders, err := client.Orders(ctx, userID)
if err != nil {
    return err
}
```

Pass (Go): `errgroup` runs them together and returns the first error.

```go
var profile Profile
var orders []Order

g, ctx := errgroup.WithContext(ctx)
g.Go(func() (err error) { profile, err = client.Profile(ctx, userID); return err })
g.Go(func() (err error) { orders, err = client.Orders(ctx, userID); return err })
if err := g.Wait(); err != nil {
    return err
}
```

Two rules survive the translation to any language: only parallelise calls with no data dependency between them, and cap
the fan-out so a batch of 10,000 ids does not open 10,000 sockets.

---

### Related skills

- `coding-standards` is the hub for the shared engineering floor this skill sits on.
- `postgres-patterns` owns schema, index, and query design in Postgres itself.
- `database-migrations` owns applying an index or a schema change safely.
- `observability-and-logging` owns the metrics and traces that give you the baseline to measure against.
- `tdd-workflow` owns the regression test that keeps the optimisation from silently reverting.
- `code-reviewer` is the entry point when performance is one concern among several in a review.

---

### Checklist

- [ ] A profile or a metric, not a hunch, identified the bottleneck.
- [ ] A target number was set before the change and measured again after.
- [ ] No query runs inside a loop over rows a previous query returned.
- [ ] Queries select named columns and page their results.
- [ ] Every index added is confirmed used by the query plan.
- [ ] Every cache has a stated staleness budget and a stated invalidation event.
- [ ] Large payloads stream rather than materialise.
- [ ] Independent IO runs concurrently with a bounded fan-out.
- [ ] The metric moved, and the change did not just move the cost elsewhere.
