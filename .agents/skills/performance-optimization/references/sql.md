# Performance Examples in SQL

The pass and fail query for the fetch and index rule. Open this when the slow path is a query. The reasoning is in [worked-examples.md](worked-examples.md), and schema and index design in Postgres itself belongs to `postgres-patterns`.

---

### Fetch and index only what is needed

Fail: unbounded and over-wide.

```sql
SELECT * FROM events WHERE tenant_id = $1 ORDER BY created_at DESC;
```

Pass: narrow, bounded, paged by cursor, and backed by an index on `(tenant_id, created_at DESC, id DESC)`.

```sql
SELECT id, kind, created_at FROM events WHERE tenant_id = $1 AND (created_at, id) < ($2, $3) ORDER BY created_at DESC, id DESC LIMIT 50;
```
