# Database Migrations Checklist

Run it before a migration is merged or reaches a production database.

- [ ] The migration has a down file, or is explicitly documented as irreversible.
- [ ] No statement takes a lock that blocks writes on a large table.
- [ ] New columns are nullable or carry a constant default.
- [ ] Indexes on existing tables are built concurrently, in their own migration.
- [ ] Renames and drops follow expand and contract across at least two deploys.
- [ ] Backfills are batched, committed per batch, and resumable.
- [ ] Every constraint and index has an explicit, prefixed name.
- [ ] The migration was run against a copy of production-sized data.
- [ ] `EXPLAIN ANALYZE` output is attached when the `postgres-patterns` gate applies.
- [ ] The rollback path is written down, not assumed.
