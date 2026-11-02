# Safe schema changes with examples

Open this for the SQL, XML and command behind any rule in [SKILL.md](../SKILL.md): lock-free column, index and constraint changes, expand and contract, batched backfills, Liquibase rollback blocks, SQL previews, and the anti-pattern table. The tool-specific commands live in the per-tool files beside this one.

---

### Contents

- [Add a column without rewriting the table](#add-a-column-without-rewriting-the-table)
- [Build indexes concurrently](#build-indexes-concurrently)
- [Rename with expand and contract, never in place](#rename-with-expand-and-contract-never-in-place)
- [Backfill in bounded batches](#backfill-in-bounded-batches)
- [Name every constraint explicitly](#name-every-constraint-explicitly)
- [Give every Liquibase changeset a rollback block](#give-every-liquibase-changeset-a-rollback-block)
- [Preview the SQL before a production run](#preview-the-sql-before-a-production-run)
- [Anti-patterns](#anti-patterns)

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
