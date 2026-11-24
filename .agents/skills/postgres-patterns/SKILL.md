---
name: postgres-patterns
description: 'PostgreSQL reference: indexes, data types, row-level security, queues, backups. Use when the user says "which index does this query need" or "why is this query slow". Not for schema changes, use `database-migrations`.'
metadata:
  version: "1.1.0"
---

# PostgreSQL Patterns

A working reference for PostgreSQL decisions that come up while writing queries and shaping schemas: which index, which type, which lock, and which query will tell you what the database is actually doing.

Written for PostgreSQL 18. Confirm the server version with `SELECT version();` before relying on a feature, and treat a release that has left community support as one to upgrade, not to target.

Based on Supabase Agent Skills (credit: Supabase team), MIT License.

| Task | Open |
| --- | --- |
| Choosing an index, or finding an unindexed foreign key | [indexes.md](references/indexes.md) |
| Picking a column type | [data-types.md](references/data-types.md) |
| Writing or reviewing a row-level security policy | [row-level-security.md](references/row-level-security.md) |
| An upsert, cursor pagination, or claiming a queue row | [query-patterns.md](references/query-patterns.md) |
| Finding slow statements or dead-row bloat | [diagnostic-queries.md](references/diagnostic-queries.md) |
| Timeouts, connections, preloaded libraries, `work_mem`, schema rights | [server-settings.md](references/server-settings.md) |
| Running the plan for the gate below | [explain-analyze.md](references/explain-analyze.md) |
| Replica routing, alert thresholds, backups, and GDPR erasure | [operations.md](references/operations.md) |
| Before calling the work done | [checklist.md](references/checklist.md) |

---

### When not to activate

- Applying a schema change safely on a live table, use `database-migrations`.
- JPA and Hibernate entity mapping and fetch strategy, use `springboot-patterns`.
- MongoDB modelling and indexing, use `mongodb-patterns`.

---

### Rules

1. Match the index type to the predicate, from the index table: B-tree for equality and range, then composite, GIN or BRIN.
2. In a composite index put the equality columns first, then the range column. Use `INCLUDE` to avoid a heap lookup, and a partial index on a soft-delete table.
3. Types: `bigint` identifiers, or `uuid` v7 when client-generated, `text` not `varchar(255)`, `timestamptz` not `timestamp`, `boolean` for flags.
4. Money is `numeric(12,2)` or an integer count of minor units, never `float` or `real`.
5. In a row-level security policy wrap the auth call in a subquery, so it runs once per statement, not per row. Index the column the policy filters on.
6. Upsert with `INSERT ... ON CONFLICT ... DO UPDATE`, never check-then-insert. Paginate by cursor, never offset. Claim a queue row with `FOR UPDATE SKIP LOCKED`.
7. Find unindexed foreign keys, slow statements and dead-tuple bloat with the diagnostic queries.
8. Set `statement_timeout` on the application role, never cluster-wide, where it also kills migrations and maintenance. Set `idle_in_transaction_session_timeout` cluster-wide.
9. `max_connections` and `shared_preload_libraries` need a restart, not a reload, and `work_mem` is per sort node, not per connection. Sizing, the pooler, preloading and the `public` schema rights are in the server settings reference.
10. Writes and read-your-own-writes go to the primary, other reads to a replica. Alert on query duration, pool use, replication lag and disk.
11. Back up daily in full plus continuous WAL archiving, off-account and encrypted, with quarterly restore drills.
12. Answer a GDPR erasure request within one month, by soft delete then purge or by pseudonymising in place, after checking cascades and audit-log retention.

---

### Run EXPLAIN ANALYZE before the change lands

Two triggers, either one of which requires the plan in the change description:

- Any query expected to touch more than 10,000 rows.
- Any migration that touches data in an existing table, meaning `UPDATE`, `DELETE`, `INSERT ... SELECT`, or a concurrent index build.

Use `EXPLAIN (ANALYZE, BUFFERS)`. `EXPLAIN ANALYZE` executes the statement it plans, so on an `UPDATE`, `DELETE` or `INSERT` it changes the data: run it inside `BEGIN` and `ROLLBACK`.

This is the one statement of the gate, and `database-migrations` points here.
