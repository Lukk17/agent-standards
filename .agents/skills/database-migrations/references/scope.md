# Scope

Companion reference for the [database-migrations](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Creating or altering a table, column, index, or constraint on a live database.
- Backfilling or transforming existing rows.
- Planning a schema change that must survive a rolling deploy.
- Choosing or configuring migration tooling on a new project.
- Reviewing a migration before it reaches a production database.
- Writing the rollback path for a migration.
- The user says "add a column to this table", "create this index without downtime", "rename a column safely" or "backfill ten million rows".

---

### When not to activate

- Choosing an index type, reading a query plan, or tuning a slow query: use `postgres-patterns`.
- MongoDB document model and schema versioning: use `mongodb-patterns`.
- JPA and Hibernate entity mapping above the schema: use `springboot-patterns`.
- Deploy orchestration and rollback of the application itself: use `deployment-patterns`.
- Backup, restore, and retention policy: use `postgres-patterns`.

---

### Related skills

- `postgres-patterns` for index choice, query plans, and the EXPLAIN ANALYZE gate this skill applies.
- `springboot-patterns` for the JPA entity mapping that has to move with the schema.
- `mongodb-patterns` for the document-model equivalent of these changes.
- `deployment-patterns` for sequencing a migration inside a rolling deploy.
- `backend-patterns` for keeping an application readable across an expand-contract window.
- `node-backend-patterns` for the repository or query layer built on the Prisma client, the Drizzle schema or the Kysely instance.
- `golang-patterns` for the service code around golang-migrate.
- `python-patterns` for the application code around Django migrations.
