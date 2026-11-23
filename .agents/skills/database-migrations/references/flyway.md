# Flyway

Read this when running migrations with Flyway. The safety model every tool has to satisfy is in [SKILL.md](../SKILL.md), and the SQL behind it is in [safe-schema-changes.md](safe-schema-changes.md).

---

### Preview the SQL before a production run

Flyway generates the statements a run will execute through `-dryRunOutput`, but that flag is part of Flyway Teams and Enterprise, not the community edition. On community Flyway, review the migration files themselves and rely on the staging run instead.

```bash
flyway -url=jdbc:postgresql://prod/db -dryRunOutput=migration_preview.sql migrate
```

How long to keep the preview, and who signs it off, is in [safe-schema-changes.md](safe-schema-changes.md#preview-the-sql-before-a-production-run).
