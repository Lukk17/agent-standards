---
name: postgres-patterns
description: PostgreSQL working reference for index selection, data types, row-level security, cursor pagination, queues, anti-pattern queries, server settings, backups and erasure. Use when the user says "which index does this query need", "why is this query slow", "write an RLS policy for this table" or "find our unindexed foreign keys". Not for applying a schema change safely, use `database-migrations`.
---

# PostgreSQL Patterns

A working reference for PostgreSQL decisions that come up while writing queries and shaping schemas: which index, which type, which lock, and which query will tell you what the database is actually doing. For a full review of an existing data layer, hand the work to the `database-expert` subagent.

Written for PostgreSQL 18. Confirm the server version with `SELECT version();` before relying on a feature, and treat a release that has left community support as a version to upgrade rather than a version to target.

Based on Supabase Agent Skills (credit: Supabase team), MIT License.

| Task | Open |
| --- | --- |
| Index type per predicate, the column type table, RLS policy, upsert, cursor pagination, queue claim, and the anti-pattern detection queries | [references/indexes-types-and-queries.md](references/indexes-types-and-queries.md) |
| Server settings and timeouts, replica routing, alert thresholds, EXPLAIN ANALYZE examples, backups, and erasure | [references/operations.md](references/operations.md) |

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

### Rules

1. Match the index to the predicate: B-tree for equality and range, composite for `a = x AND b > y`, GIN for `jsonb @>` and full-text `@@`, BRIN for time-series range scans on an append-only table.
2. In a composite index put the equality columns first, then the range column. Reach for `INCLUDE` to avoid a heap lookup, and a partial index (`WHERE deleted_at IS NULL`) to keep it small on a soft-delete table.
3. Types: `bigint` identifiers, or `uuid` v7 when client-generated, never `int` or a random `uuid` v4 primary key. `text` not `varchar(255)`, `timestamptz` not `timestamp`, `boolean` for flags.
4. Money is `numeric(12,2)` or an integer count of minor units, never `float` or `real`, which cannot represent 0.1 and drift. `varchar(n)` buys no speed over `text`, and its limit becomes a migration.
5. In a row-level security policy wrap the auth call in a subquery, `(SELECT auth.uid()) = user_id`, so it runs once per statement, not per row. Index the column the policy filters on.
6. Upsert with `INSERT ... ON CONFLICT ... DO UPDATE`, never check-then-insert. Paginate by cursor (`WHERE id > $1 ORDER BY id LIMIT n`), never offset. Claim a queue row with `FOR UPDATE SKIP LOCKED`.
7. Find unindexed foreign keys, slow statements from `pg_stat_statements`, and dead-tuple bloat with the queries in the reference. A foreign key is covered only when its columns lead a non-partial index.
8. Set `statement_timeout` on the application role, never cluster-wide, which also kills migrations, `CREATE INDEX CONCURRENTLY`, `pg_dump` and maintenance. Set `idle_in_transaction_session_timeout` and `work_mem` cluster-wide with `ALTER SYSTEM` and `pg_reload_conf()`.
9. `max_connections` and `shared_preload_libraries` need a restart, not a reload. Preload `pg_stat_statements` before `CREATE EXTENSION`, and remember `ALTER SYSTEM SET shared_preload_libraries` replaces the whole list.
10. `work_mem` is per sort node, so one query can use several multiples of it. Size `max_connections` for the machine and put a pooler in front rather than raising it. Run `REVOKE ALL ON SCHEMA public FROM public;`.
11. Writes and read-your-own-writes go to the primary, and reads that tolerate eventual consistency to a replica. Alert on query duration over 500ms, pool utilisation over 80% for 30s, replication lag over 30s, disk over 80%.
12. Back up daily in full plus continuous WAL archiving, into a separate cloud account, AES-256 encrypted, with quarterly restore drills measuring real recovery time and RTO and RPO in the runbook. A backup nobody has restored is a hypothesis.
13. Answer a GDPR erasure request within one month, extendable by two for complex or numerous requests (Article 12(3)), by soft delete then purge, or by pseudonymising in place. Check cascades and audit-log retention before any hard delete.

---

### Run EXPLAIN ANALYZE before the change lands

Two triggers, either one of which requires the plan in the change description:

- Any query expected to touch more than 10,000 rows.
- Any migration that touches data in an existing table, meaning `UPDATE`, `DELETE`, `INSERT ... SELECT`, or a concurrent index build.

Use `EXPLAIN (ANALYZE, BUFFERS)`. `EXPLAIN ANALYZE` executes the statement it plans, so on an `UPDATE`, `DELETE` or `INSERT` it changes the data: run it inside `BEGIN` and `ROLLBACK`. The examples are in [references/operations.md](references/operations.md).

This is the one statement of the gate. `database-migrations` applies it to data migrations and points here rather than restating it.

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
