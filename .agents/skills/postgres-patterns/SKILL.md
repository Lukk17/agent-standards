---
name: postgres-patterns
description: PostgreSQL working reference for index selection, data types, row-level security, cursor pagination, queues, anti-pattern queries, server settings, backups and erasure. Use when the user says "which index does this query need", "why is this query slow", "write an RLS policy for this table" or "find our unindexed foreign keys". Not for applying a schema change safely, use `database-migrations`.
---

# PostgreSQL Patterns

A working reference for PostgreSQL decisions that come up while writing queries and shaping schemas: which index, which
type, which lock, and which query will tell you what the database is actually doing. For a full review of an existing
data layer, hand the work to the `database-expert` subagent.

Written for PostgreSQL 18. Confirm the server version with `SELECT version();` before relying on a feature, and treat a
release that has left community support as a version to upgrade rather than a version to target.

Based on Supabase Agent Skills (credit: Supabase team), MIT License.

---

### When to activate

- Choosing an index for a query, or deciding whether one is even needed.
- Picking a column type for identifiers, money, timestamps, or flags, such as numeric against float.
- Writing or reviewing a row-level security policy.
- Diagnosing a slow query, table bloat, or a missing foreign-key index.
- Setting connection limits, statement timeouts, or monitoring thresholds.

---

### When not to activate

- Applying a schema change safely on a live table: use `database-migrations`.
- JPA and Hibernate entity mapping and fetch strategy: use `springboot-patterns`.
- MongoDB modelling and indexing: use `mongodb-patterns`.
- Application-level caching, retries, and layering: use `backend-patterns`.
- Profiling an endpoint end to end before blaming the database: use `performance-optimization`.

---

### Pick the index that matches the predicate

| Query pattern | Index type | Example |
| --- | --- | --- |
| `WHERE col = value` | B-tree, the default | `CREATE INDEX idx ON t (col)` |
| `WHERE col > value` | B-tree | `CREATE INDEX idx ON t (col)` |
| `WHERE a = x AND b > y` | Composite | `CREATE INDEX idx ON t (a, b)` |
| `WHERE jsonb_col @> '{}'` | GIN | `CREATE INDEX idx ON t USING gin (col)` |
| `WHERE tsv @@ query` | GIN | `CREATE INDEX idx ON t USING gin (col)` |
| Time-series range scans on an append-only table | BRIN | `CREATE INDEX idx ON t USING brin (col)` |

Pass: equality columns first in a composite index, then the range column.

```sql
CREATE INDEX idx_orders_status_created ON orders (status, created_at);
```

Fail: `CREATE INDEX idx ON orders (created_at, status)` for `WHERE status = 'pending' AND created_at > $1`, which
cannot use the leading column for the equality and scans far more of the index than it needs.

Two variants worth reaching for:

```sql
CREATE INDEX idx_users_email_cover ON users (email) INCLUDE (name, created_at);
```

```sql
CREATE INDEX idx_users_email_active ON users (email) WHERE deleted_at IS NULL;
```

The first avoids a heap lookup when the query selects only the included columns. The second indexes only live rows, so
it stays small on a table dominated by soft-deleted ones.

---

### Choose the type that cannot be wrong

| Use case | Correct type | Avoid |
| --- | --- | --- |
| Identifiers | `bigint`, or `uuid` v7 when it must be client-generated | `int`, random `uuid` v4 as a primary key |
| Strings | `text` | `varchar(255)` |
| Timestamps | `timestamptz` | `timestamp` |
| Money | `numeric(12,2)`, or an integer count of minor units | `float`, `real` |
| Flags | `boolean` | `varchar`, `int` |

Pass: `amount_minor bigint NOT NULL` for money, so no rounding exists to get wrong.

Fail: `price float`, which cannot represent 0.1 exactly and silently drifts across arithmetic.

`varchar(n)` buys no performance over `text` in PostgreSQL, and the length limit becomes a migration the first time the
business changes its mind.

---

### Wrap the auth call in a row-level security policy

```sql
-- PASS: the subquery is evaluated once per statement
CREATE POLICY orders_owner ON orders
  USING ((SELECT auth.uid()) = user_id);

-- FAIL: the function is re-evaluated for every row scanned
CREATE POLICY orders_owner ON orders
  USING (auth.uid() = user_id);
```

Index the column the policy filters on, or the policy turns every read into a sequential scan.

---

### Use the right statement for the job

Upsert without a race between the check and the insert:

```sql
INSERT INTO settings (user_id, key, value)
VALUES (123, 'theme', 'dark')
ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value;
```

Paginate by cursor, which is constant cost, rather than by offset, which is linear in the rows skipped:

```sql
SELECT * FROM products WHERE id > $1 ORDER BY id LIMIT 20;
```

Claim a queue row without two workers taking the same one:

```sql
UPDATE jobs SET status = 'processing'
WHERE id = (
  SELECT id FROM jobs WHERE status = 'pending'
  ORDER BY created_at LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

---

### Detect the common anti-patterns with a query

Unindexed foreign keys, which make every parent delete scan the child table. A foreign key counts as covered only when
its columns are the leading columns of a non-partial index, which is what the slice of `indkey` checks:

```sql
SELECT c.conrelid::regclass AS table_name, c.conname AS foreign_key
FROM pg_constraint c
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid
      AND i.indpred IS NULL
      AND (i.indkey::int2[])[0:cardinality(c.conkey) - 1] @> c.conkey
  );
```

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

---

### Set the timeouts before you need them

Settings a reload applies, cluster-wide:

```sql
ALTER SYSTEM SET work_mem = '8MB';
ALTER SYSTEM SET idle_in_transaction_session_timeout = '30s';
SELECT pg_reload_conf();
```

Set `statement_timeout` on the application role, never cluster-wide. A global value also kills migrations,
`CREATE INDEX CONCURRENTLY`, `pg_dump` and maintenance jobs, and the PostgreSQL manual calls setting it in
`postgresql.conf` not recommended because it affects all sessions.

```sql
ALTER ROLE app_user SET statement_timeout = '30s';
```

`max_connections` and `shared_preload_libraries` take effect only at server start, so `pg_reload_conf()` leaves them
unchanged. `pg_stat_statements` needs its library preloaded before `CREATE EXTENSION` does anything useful, and
`ALTER SYSTEM SET shared_preload_libraries` replaces the whole list, so include any library already in it.

```sql
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
```

Restart the server, then:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

`work_mem` is per sort node, not per connection, so a single complex query can use several multiples of it. Size
`max_connections` for the machine and put a pooler in front rather than raising it. Revoke the default rights on the
`public` schema as well, with `REVOKE ALL ON SCHEMA public FROM public;`.

---

### Route reads to replicas, except read-your-own-writes

- Writes go to the primary.
- Reads that tolerate eventual consistency go to a replica.
- A read in the same request as a preceding write goes to the primary, or the user sees their own change missing.

Alert on these before a user reports them:

| Metric | Alert threshold |
| --- | --- |
| Query duration | over 500ms |
| Connection pool utilization | over 80% for more than 30s |
| Replication lag | over 30s |
| Disk usage | over 80% |

---

### Run EXPLAIN ANALYZE before the change lands

Two triggers, either one of which requires the plan in the change description:

- Any query expected to touch more than 10,000 rows.
- Any migration that touches data in an existing table, meaning `UPDATE`, `DELETE`, `INSERT ... SELECT`, or a
  concurrent index build.

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE created_at > '2024-01-01';
```

`EXPLAIN ANALYZE` executes the statement it plans, so on an `UPDATE`, `DELETE` or `INSERT` it changes the data. Run
it inside a transaction and roll back:

```sql
BEGIN;
EXPLAIN ANALYZE UPDATE orders SET status = 'active' WHERE created_at > '2024-01-01';
ROLLBACK;
```

This is the one statement of the gate. `database-migrations` applies it to data migrations and points here rather than
restating it.

---

### Back up on a schedule you have actually tested

- Daily full backup plus continuous WAL archiving.
- Backups stored in a separate cloud account from the application.
- AES-256 encryption at rest.
- Quarterly restore drills that measure the real recovery time, not the intended one.
- RTO and RPO written in the runbook, next to the measured numbers from the last drill.

A backup nobody has restored is a hypothesis.

---

### Erase personal data within the legal window

GDPR requires an answer to an erasure request without undue delay and within one month of receipt, extendable by two
further months for complex or numerous requests (Article 12(3)). Two workable shapes:

1. Soft delete then purge: set `deleted_at`, exclude the row everywhere, delete it for real after the window.
2. Pseudonymize in place: overwrite the identifying columns with a non-reversible value, keeping the row for referential
   integrity and aggregates.

Never hard-delete before checking cascade behaviour and audit-log retention, because a `DELETE` that cascades into an
audit trail destroys the evidence that the erasure was lawful.

---

### Related skills

- `database-migrations` for applying any of these changes safely on a live table.
- `backend-patterns` and `node-backend-patterns` for connection pooling and caching above the database.
- `springboot-patterns` when the queries are generated by Hibernate rather than written by hand.
- `performance-optimization` for measuring an endpoint before assuming the database is the bottleneck.
- `security-review` for access control and personal-data handling beyond row-level security.
- The `database-expert` subagent for a full review of an existing data layer.

---

### Checklist

- [ ] Every predicate that runs often has an index whose leading columns match it.
- [ ] Every foreign key has an index on the referencing side.
- [ ] Identifiers, money, and timestamps use the correct type, never `float` for money.
- [ ] Row-level security policies wrap the auth call in a subquery and filter on an indexed column.
- [ ] Pagination is cursor-based on anything unbounded.
- [ ] `statement_timeout` is set on the application role and `idle_in_transaction_session_timeout` cluster-wide.
- [ ] `pg_stat_statements` is preloaded, the extension created, and someone reads it.
- [ ] `EXPLAIN ANALYZE` output is attached when either trigger above applies.
- [ ] Backups are encrypted, off-account, and restored on a schedule.
- [ ] Erasure requests have a documented path that respects audit retention.
