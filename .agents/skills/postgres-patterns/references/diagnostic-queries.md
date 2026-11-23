# Diagnostic queries

Open this for the queries that find the common anti-patterns in a running database. The query for unindexed foreign keys is in [indexes.md](indexes.md#find-unindexed-foreign-keys).

---

### Detect the common anti-patterns with a query

Slow statements by mean execution time:

```sql
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC;
```

Tables carrying dead rows that autovacuum is not keeping up with:

```sql
SELECT relname, n_dead_tup, last_vacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```
