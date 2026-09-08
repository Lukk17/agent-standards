# golang-migrate

Read this when running migrations with golang-migrate on a Go project.

---

### Workflow

Create the up and down file pair:

```bash
migrate create -ext sql -dir migrations -seq add_user_avatar
```

Apply every pending migration:

```bash
migrate -path migrations -database "$DATABASE_URL" up
```

Roll back the most recent migration:

```bash
migrate -path migrations -database "$DATABASE_URL" down 1
```

Show the current version:

```bash
migrate -path migrations -database "$DATABASE_URL" version
```

Clear a dirty state after a failed run, once you have checked by hand what actually landed:

```bash
migrate -path migrations -database "$DATABASE_URL" force VERSION
```

`force` only rewrites the version row. It applies nothing and rolls nothing back, so inspect the schema before using it
or you will mark a half-applied migration as complete.

---

### Migration files

```sql
-- migrations/000003_add_user_avatar.up.sql
ALTER TABLE users ADD COLUMN avatar_url TEXT;
```

```sql
-- migrations/000003_add_user_avatar.down.sql
ALTER TABLE users DROP COLUMN IF EXISTS avatar_url;
```

Write the down file at the same time as the up file, even when you expect never to run it. Writing it is what forces
you to notice that a migration is irreversible, and an irreversible one should say so in a comment rather than ship an
empty down.

---

### Concurrent indexes

golang-migrate wraps each file in a transaction by default, and `CREATE INDEX CONCURRENTLY` cannot run inside one. Add
the `x-multi-statement=false` behaviour by keeping the statement alone in its own migration and disabling the
transaction with a leading directive:

```sql
-- migrations/000004_add_avatar_index.up.sql
BEGIN;
COMMIT;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_avatar ON users (avatar_url) WHERE avatar_url IS NOT NULL;
```

Prefer running such a statement through a separate operational task rather than a migration when the tool fights you.
An index build that takes an hour does not belong in a deploy step either way.

---

### Embedding migrations in the binary

Use `//go:embed` with the `iofs` source driver so the deployed artifact carries its own migrations and cannot drift from
the schema it expects.

```go
//go:embed migrations/*.sql
var migrationsFS embed.FS
```

---

### Related skills

- `database-migrations` for the safety rules these commands have to satisfy.
- `golang-patterns` for the surrounding service code.
- `postgres-patterns` for index selection and query plans.
