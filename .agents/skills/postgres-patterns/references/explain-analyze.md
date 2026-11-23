# EXPLAIN ANALYZE examples

The gate itself is stated once, in [SKILL.md](../SKILL.md) under "Run EXPLAIN ANALYZE before the change lands", and this file carries only its examples.

---

### EXPLAIN ANALYZE examples

The gate and its two triggers are in [SKILL.md](../SKILL.md). A read query, with buffer counts:

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE created_at > '2024-01-01';
```

A data-changing statement, planned inside a transaction that rolls back, because `EXPLAIN ANALYZE` executes what it plans:

```sql
BEGIN;
EXPLAIN ANALYZE UPDATE orders SET status = 'active' WHERE created_at > '2024-01-01';
ROLLBACK;
```
