---
name: database-migrations
description: 'Safe schema and data migrations on a live database: lock-free changes, renames, backfills. Use when the user says "add a column" or "create this index without downtime". Not for query tuning, use `postgres-patterns`.'
metadata:
  version: "1.1.0"
---

# Database Migrations

Rules for changing a schema that is already carrying production traffic, where the failure mode is a locked table rather than a compile error. This file is the safety model every tool has to satisfy.

Written for PostgreSQL 18, MySQL 8.4 LTS and 9.7 LTS, and the migration tools named in the reference map below.

---

### When not to activate

- Choosing an index type, reading a query plan, tuning a slow query, or backup, restore and retention policy, use `postgres-patterns`.
- MongoDB document model and schema versioning, use `mongodb-patterns`.
- Deploy orchestration and rollback of the application itself, use `deployment-patterns`.

---

### Reference map

| Task or tool | Open |
| --- | --- |
| The PostgreSQL Pass and Fail SQL behind a rule, the anti-pattern table, the plan to attach | [safe-schema-changes.md](references/safe-schema-changes.md) |
| Liquibase | [liquibase.md](references/liquibase.md) |
| Flyway | [flyway.md](references/flyway.md) |
| Prisma | [prisma.md](references/prisma.md) |
| Drizzle | [drizzle.md](references/drizzle.md) |
| Kysely | [kysely.md](references/kysely.md) |
| Django | [django.md](references/django.md) |
| golang-migrate | [golang-migrate.md](references/golang-migrate.md) |
| Before a migration is merged or reaches production | [checklist.md](references/checklist.md) |

---

### Core principles

1. Every change is a migration. Never alter a production database by hand.
2. Production is forward-only. A rollback is a new forward migration, not a re-run of a down file.
3. Schema and data changes are separate migrations. Never mix DDL and DML in one file.
4. Test against production-sized data. A migration that runs on 100 rows can lock on 10 million.
5. A deployed migration is immutable. Write a new one instead of editing it.
6. Migrations run as one step in the deploy pipeline, never on application startup.

---

### Rules

1. Add a column nullable, or with a constant default. `NOT NULL` with no default on an existing table rewrites every row under an exclusive lock.
2. To reach a `NOT NULL` column with no sensible default: add it nullable, backfill in batches, then add the constraint and validate it as separate steps.
3. Build an index on an existing table concurrently, in its own migration outside any transaction block, because a plain build blocks every write. A failed build leaves an invalid index: drop it before retrying.
4. Never rename in place, because old code and new schema overlap during any rolling deploy. Expand (add the new column), backfill in a separate data migration, deploy the code that writes both and reads the new one, then contract (drop the old column).
5. Drop a column in the reverse order: remove every application reference, deploy, then drop.
6. Backfill in bounded batches, each committed, selecting on the condition the update clears and skipping locked rows, so a killed backfill simply restarts. Never one `UPDATE` over every row.
7. Name every constraint and index explicitly, with the `ck_`, `uq_`, `fk_` or `idx_` prefix, because an auto-generated name differs between environments.
8. On an existing table, add a check or foreign key unvalidated in one migration and validate it in the next, so writes continue during the scan.
9. With a tool that infers rollbacks, such as Liquibase, write the rollback of every change yourself, because the tool infers one for some operations and silently does nothing for others. Scope environment-only changes, such as seed data, to their environment.
10. Preview the SQL a production run will execute with the tool's dry-run output, keep it as a CI artifact, and require a database owner's sign-off when the change touches a table over a million rows.
11. A migration that touches data in an existing table, or builds an index concurrently, carries its `EXPLAIN ANALYZE` plan in the change description.
