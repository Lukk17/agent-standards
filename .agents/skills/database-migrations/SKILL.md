---
name: database-migrations
description: Safe, reversible schema and data migrations for production databases, covering lock-free column, index and constraint changes, expand-contract renames, batched backfills and rollback. Use when the user says "add a column to this table", "create this index without downtime", "rename a column safely" or "backfill ten million rows". Not for index choice and query tuning, use `postgres-patterns`.
---

# Database Migrations

Rules for changing a schema that is already carrying production traffic, where the failure mode is a locked table rather than a compile error. This file is the safety model every tool has to satisfy, and the tool-specific commands live in the references.

Written for PostgreSQL 18, MySQL 8.4 LTS and 9.7 LTS, and the migration tools named in the reference map below.

---

### When to activate

- Creating or altering a table, column, index, or constraint on a live database.
- Backfilling or transforming existing rows.
- Planning a schema change that must survive a rolling deploy.
- Choosing or configuring migration tooling on a new project.
- Reviewing a migration before it reaches a production database.
- Writing the rollback path for a migration.

---

### When not to activate

- Choosing an index type, reading a query plan, or tuning a slow query: use `postgres-patterns`.
- MongoDB document model and schema versioning: use `mongodb-patterns`.
- JPA and Hibernate entity mapping above the schema: use `springboot-patterns`.
- Deploy orchestration and rollback of the application itself: use `deployment-patterns`.
- Backup, restore, and retention policy: use `postgres-patterns`.

---

### Reference map

| Task or tool | Open |
| --- | --- |
| The Pass and Fail SQL behind any rule below, the Liquibase and Flyway examples, and the anti-pattern table | [references/safe-schema-changes.md](references/safe-schema-changes.md) |
| Prisma | [references/prisma.md](references/prisma.md) |
| Drizzle | [references/drizzle.md](references/drizzle.md) |
| Kysely | [references/kysely.md](references/kysely.md) |
| Django | [references/django.md](references/django.md) |
| golang-migrate | [references/golang-migrate.md](references/golang-migrate.md) |

---

### Core principles

1. Every change is a migration. Never alter a production database by hand.
2. Production is forward-only. A rollback is a new forward migration, not a re-run of a down file.
3. Schema and data changes are separate migrations. Never mix DDL and DML in one file.
4. Test against production-sized data. A migration that runs on 100 rows can lock on 10 million.
5. A deployed migration is immutable. Editing one that has already run produces drift between environments.
6. Migrations run as one step in the deploy pipeline, never on application startup, where concurrent replicas race each other.

---

### Rules

1. Add a column nullable, or with a constant default, which PostgreSQL 11 or newer stores in the catalogue without a rewrite. `NOT NULL` with no default on an existing table rewrites every row under an exclusive lock.
2. To reach a `NOT NULL` column with no sensible default: add it nullable, backfill in batches, then add the constraint as `NOT VALID` and `VALIDATE CONSTRAINT` separately, which takes a weaker lock.
3. Build an index on an existing table with `CREATE INDEX CONCURRENTLY`, because a plain build blocks every write for its duration. It cannot run inside a transaction block, so it needs its own migration and usually the tool's no-transaction opt-out.
4. A failed concurrent build leaves an invalid index: check `pg_index.indisvalid` and drop it before retrying.
5. Never rename in place, because old code and new schema overlap during any rolling deploy. Expand (add the new column), backfill in a separate data migration, deploy the code that writes both and reads the new one, then contract (drop the old column).
6. Drop a column in the reverse order: remove every application reference, deploy, then drop.
7. Backfill in bounded batches, each committed, selecting with `LIMIT ... FOR UPDATE SKIP LOCKED` on the condition the update clears, so a killed backfill simply restarts. Never one `UPDATE` over every row, which holds locks and bloats the WAL.
8. A `COMMIT` inside `DO` works only when the block runs in its own transaction, and inside a tool's wrapping transaction raises `invalid transaction termination`. Use the no-transaction opt-out, or drive batches from application code with one transaction each.
9. Name every constraint and index explicitly with a prefix: `ck_` check, `uq_` unique, `fk_` foreign key, `idx_` index. An auto-generated name differs between environments and cannot be dropped reliably later.
10. On an existing table, add a check or foreign key `NOT VALID` in one migration and `VALIDATE CONSTRAINT` in the next, which takes only `SHARE UPDATE EXCLUSIVE`. In one wrapped file the transaction would keep the stronger `ADD` lock for the whole scan.
11. Add a unique constraint by building the unique index `CONCURRENTLY`, then attaching it with `ADD CONSTRAINT ... UNIQUE USING INDEX`, a fast catalogue change.
12. Give every Liquibase changeset a `<rollback>` block, even when it looks redundant, because Liquibase infers a rollback for some operations and silently does nothing for others. Scope environment-only changesets, such as seed data, with `context`.
13. Preview the SQL before a production run: `liquibase ... updateSQL`, or Flyway's `-dryRunOutput`, which is Teams and Enterprise only. On community Flyway, review the migration files and rely on the staging run.
14. Keep the preview as a CI artifact, and require a database owner's sign-off whenever the change touches a table over a million rows.

---

### Attach EXPLAIN ANALYZE output

A migration that touches data in an existing table, meaning `UPDATE`, `DELETE`, `INSERT ... SELECT`, or a concurrent index build, carries its plan in the change description. The gate, its two triggers, and how to run it without changing data are stated once in `postgres-patterns`, under "Run EXPLAIN ANALYZE before the change lands".

---

### Related skills

- `postgres-patterns` for index choice, query plans, and the EXPLAIN ANALYZE gate this skill applies.
- `springboot-patterns` for the JPA entity mapping that has to move with the schema.
- `mongodb-patterns` for the document-model equivalent of these changes.
- `deployment-patterns` for sequencing a migration inside a rolling deploy.
- `backend-patterns` for keeping an application readable across an expand-contract window.

---

### Checklist

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
