---
name: database-migrations
description: Safe, reversible schema and data migrations for production databases, covering lock-free column, index and constraint changes, expand-contract renames, batched backfills and rollback. Use when the user says "add a column to this table", "create this index without downtime", "rename a column safely" or "backfill ten million rows". Not for index choice and query tuning, use `postgres-patterns`.
---

# Database Migrations

Rules for changing a schema that is already carrying production traffic, where the failure mode is a locked table
rather than a compile error. The tool-specific commands live in the references. This file is the safety model every
tool has to satisfy.

Written for PostgreSQL 18, MySQL 8.4 LTS or a later LTS line, and the migration tools named in the reference map
below.

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

| Tool | Open |
| --- | --- |
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

---

### Add a column without rewriting the table

```sql
-- PASS: nullable column, metadata-only change
ALTER TABLE users ADD COLUMN avatar_url TEXT;

-- PASS: PostgreSQL 11 or newer stores a constant default in the catalogue, so no rewrite happens
ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;

-- FAIL: NOT NULL with no default on an existing table rewrites every row under an exclusive lock
ALTER TABLE users ADD COLUMN role TEXT NOT NULL;
```

To reach a NOT NULL column with no sensible default, take three steps: add it nullable, backfill in batches, then add
the constraint as `NOT VALID` and `VALIDATE CONSTRAINT` separately, which takes a weaker lock.

---

### Build indexes concurrently

```sql
-- PASS
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);

-- FAIL: blocks every write to the table for the duration of the build
CREATE INDEX idx_users_email ON users (email);
```

`CONCURRENTLY` cannot run inside a transaction block, and most migration tools wrap each file in one, so the statement
needs its own migration and usually a tool-specific opt-out. A concurrent build that fails leaves an invalid index
behind: check `pg_index.indisvalid` and drop it before retrying.

---

### Rename with expand and contract, never in place

A rename is instantaneous for the database and fatal for the running application, because the old code and the new
schema overlap during any rolling deploy.

```sql
-- 001 expand: add the new column
ALTER TABLE users ADD COLUMN display_name TEXT;

-- 002 backfill: separate data migration, batched
UPDATE users SET display_name = username WHERE display_name IS NULL;

-- deploy the application version that writes both and reads the new column

-- 003 contract: drop the old column once nothing references it
ALTER TABLE users DROP COLUMN username;
```

Dropping a column follows the same order in reverse: remove every application reference, deploy, then drop.

---

### Backfill in bounded batches

```sql
-- FAIL: one transaction over every row, holding locks and bloating the WAL
UPDATE users SET normalized_email = LOWER(email);
```

```sql
-- PASS: bounded batches, each committed, skipping rows another worker holds
DO $$
DECLARE
  rows_updated INT;
BEGIN
  LOOP
    UPDATE users SET normalized_email = LOWER(email)
    WHERE id IN (
      SELECT id FROM users WHERE normalized_email IS NULL
      LIMIT 10000 FOR UPDATE SKIP LOCKED
    );
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    EXIT WHEN rows_updated = 0;
    COMMIT;
  END LOOP;
END $$;
```

Make the batch resumable by selecting on the condition the update clears, so a killed backfill can simply be restarted.

The `COMMIT` inside `DO` works only when the block runs in its own transaction. Most migration tools wrap each file in
one, and there the `COMMIT` raises `invalid transaction termination`. Run the file with the tool's no-transaction
opt-out, the same one `CONCURRENTLY` needs, or drive the batches from application code with one transaction each.

---

### Name every constraint explicitly

An auto-generated name differs between environments and cannot be dropped reliably in a later migration. On an
existing table, add each constraint in the form that does not lock writes for the length of a full scan.

```sql
-- FAIL: ACCESS EXCLUSIVE on orders for the whole scan and index build, plus a lock on customers
ALTER TABLE orders
  ADD CONSTRAINT ck_orders_amount_positive CHECK (amount > 0),
  ADD CONSTRAINT uq_orders_reference UNIQUE (reference_number),
  ADD CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers (id);
```

```sql
-- PASS, first migration: add the constraints without scanning the existing rows
ALTER TABLE orders ADD CONSTRAINT ck_orders_amount_positive CHECK (amount > 0) NOT VALID;
ALTER TABLE orders ADD CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers (id) NOT VALID;
```

```sql
-- PASS, next migration: validate under a lock that lets writes continue
ALTER TABLE orders VALIDATE CONSTRAINT ck_orders_amount_positive;
ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_customer;
```

```sql
-- PASS: build the unique index concurrently, then attach it as the constraint, which is a fast catalogue change
CREATE UNIQUE INDEX CONCURRENTLY uq_orders_reference ON orders (reference_number);
ALTER TABLE orders ADD CONSTRAINT uq_orders_reference UNIQUE USING INDEX uq_orders_reference;
CREATE INDEX CONCURRENTLY idx_orders_status ON orders (status) WHERE status <> 'completed';
```

`VALIDATE CONSTRAINT` takes only a `SHARE UPDATE EXCLUSIVE` lock, which is why it sits in a later migration than the
`ADD`: in one wrapped file the transaction would keep the stronger `ADD` lock for the whole scan. The `CONCURRENTLY`
file needs the tool's no-transaction opt-out, as in the index section above.

Prefixes: `ck_` check, `uq_` unique, `fk_` foreign key, `idx_` index.

---

### Give every Liquibase changeset a rollback block

```xml
<changeSet id="20240101-add-status-column" author="dev">
    <addColumn tableName="orders">
        <column name="status" type="VARCHAR(20)" defaultValue="pending">
            <constraints nullable="false"/>
        </column>
    </addColumn>
    <rollback>
        <dropColumn tableName="orders" columnName="status"/>
    </rollback>
</changeSet>
```

Liquibase infers a rollback for some operations and silently does nothing for others, so write the block even when it
looks redundant. Use `context` to scope a changeset to an environment, for example seed data that must never reach
production.

---

### Preview the SQL before a production run

Generate the statements a run will execute and attach them to the change for review.

```bash
liquibase --changeLogFile=changelog.xml updateSQL > migration_preview.sql
```

Flyway offers the same thing through `-dryRunOutput`, but that flag is part of Flyway Teams and Enterprise, not the
community edition. On community Flyway, review the migration files themselves and rely on the staging run instead.

```bash
flyway -url=jdbc:postgresql://prod/db -dryRunOutput=migration_preview.sql migrate
```

Keep the preview as a CI artifact, and require a database owner to sign off whenever the change touches a table over a
million rows.

---

### Attach EXPLAIN ANALYZE output

A migration that touches data in an existing table, meaning `UPDATE`, `DELETE`, `INSERT ... SELECT`, or a concurrent
index build, carries its plan in the change description. The gate, its two triggers, and how to run it without
changing data are stated once in `postgres-patterns`, under "Run EXPLAIN ANALYZE before the change lands".

---

### Anti-patterns

| Anti-pattern | Why it fails | Instead |
| --- | --- | --- |
| Manual SQL in production | No audit trail, unrepeatable | Always a migration file |
| Editing a deployed migration | Environments drift silently | Write a new migration |
| NOT NULL with no default | Exclusive lock, full rewrite | Nullable, backfill, then validate |
| Constraint added with a scan on a large table | Writes blocked for the whole scan | `NOT VALID`, then `VALIDATE CONSTRAINT` |
| Inline index on a large table | Blocks writes during the build | `CREATE INDEX CONCURRENTLY` |
| Schema and data in one file | Long transaction, hard to roll back | Separate migrations |
| Dropping a column before removing the code | The running release errors | Remove references, deploy, then drop |
| Migration on application startup | Concurrent replicas race each other | One migration step in the deploy pipeline |

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
