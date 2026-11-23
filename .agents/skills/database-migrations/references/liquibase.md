# Liquibase

Read this when running migrations with Liquibase. The safety model every tool has to satisfy is in [SKILL.md](../SKILL.md), and the SQL behind it is in [safe-schema-changes.md](safe-schema-changes.md).

---

### Give every changeset a rollback block

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

Give every Liquibase changeset a `<rollback>` block. Liquibase infers a rollback for some operations and silently does nothing for others, so write the block even when it looks redundant. Use `context` to scope a changeset to an environment, for example seed data that must never reach production.

---

### Preview the SQL before a production run

Generate the statements a run will execute with `updateSQL` and attach them to the change for review.

```bash
liquibase --changeLogFile=changelog.xml updateSQL > migration_preview.sql
```

How long to keep the preview, and who signs it off, is in [safe-schema-changes.md](safe-schema-changes.md#preview-the-sql-before-a-production-run).
