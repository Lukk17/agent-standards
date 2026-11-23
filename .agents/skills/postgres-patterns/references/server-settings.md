# Server settings

Open this for the SQL and reasoning behind the timeout, connection, preload and memory rules in [SKILL.md](../SKILL.md).

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
