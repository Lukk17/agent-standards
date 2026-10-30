# Server settings, replicas, plans, backups and erasure

Open this for the SQL and reasoning behind the server settings, replica routing, monitoring thresholds, EXPLAIN ANALYZE gate, backup and erasure rules in [SKILL.md](../SKILL.md). The gate itself is stated once, in [SKILL.md](../SKILL.md) under "Run EXPLAIN ANALYZE before the change lands", and this file carries only its examples.

---

### Contents

- [Set the timeouts before you need them](#set-the-timeouts-before-you-need-them)
- [Route reads to replicas, except read-your-own-writes](#route-reads-to-replicas-except-read-your-own-writes)
- [EXPLAIN ANALYZE examples](#explain-analyze-examples)
- [Back up on a schedule you have actually tested](#back-up-on-a-schedule-you-have-actually-tested)
- [Erase personal data within the legal window](#erase-personal-data-within-the-legal-window)

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
