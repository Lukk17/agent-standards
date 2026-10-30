# Worked Examples

Contents:

- [Measure before you change anything](#measure-before-you-change-anything)
- [Avoid the N+1 query](#avoid-the-n1-query)
- [Fetch and index only what is needed](#fetch-and-index-only-what-is-needed)
- [Add a cache only after a profile justifies it](#add-a-cache-only-after-a-profile-justifies-it)
- [Keep memory bounded](#keep-memory-bounded)
- [Run independent IO concurrently](#run-independent-io-concurrently)

Each rule in SKILL.md in full, with its reasoning and its pass and fail forms in Python, SQL, TypeScript and Go. Load this file when applying a rule and the one-line summary in SKILL.md is not enough.

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

Pass: narrow, bounded, paged by cursor, and backed by an index on `(tenant_id, created_at DESC, id DESC)`.

```sql
SELECT id, kind, created_at FROM events WHERE tenant_id = $1 AND (created_at, id) < ($2, $3) ORDER BY created_at DESC, id DESC LIMIT 50;
```

---

### Add a cache only after a profile justifies it

Add a cache only after a profile shows a read-dominated hot path, and follow `backend-patterns` for the invalidation
rule, which it owns. A cache added on a guess hides the real bottleneck and adds a staleness bug on top of it.

Fail: the diagnosis is a feeling, and the cache has no invalidation rule.

```text
The product page feels slow, so I cached get_product in a module-level dict.
```

Pass: the profile names the hot path, and the cache follows the `backend-patterns` rule.

```text
get_product is 71% of request time at p95 and is read 40 times per write. Cached with eviction on rename, per backend-patterns. p95 went from 620 ms to 140 ms.
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
