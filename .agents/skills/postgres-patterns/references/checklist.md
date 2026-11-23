# PostgreSQL Patterns Checklist

Run it before calling a schema, query or server change done.

- [ ] Every predicate that runs often has an index whose leading columns match it.
- [ ] Every foreign key has an index on the referencing side.
- [ ] Identifiers, money, and timestamps use the correct type, never `float` for money.
- [ ] Row-level security policies wrap the auth call in a subquery and filter on an indexed column.
- [ ] Pagination is cursor-based on anything unbounded.
- [ ] `statement_timeout` is set on the application role and `idle_in_transaction_session_timeout` cluster-wide.
- [ ] `pg_stat_statements` is preloaded, the extension created, and someone reads it.
- [ ] `EXPLAIN ANALYZE` output is attached when either trigger of the gate in [SKILL.md](../SKILL.md) applies.
- [ ] Backups are encrypted, off-account, and restored on a schedule.
- [ ] Erasure requests have a documented path that respects audit retention.
