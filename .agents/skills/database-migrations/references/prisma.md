# Prisma migrations

Read this when running migrations with Prisma on a TypeScript or Node project.

---

### Workflow

Create a migration from the schema change during development:

```bash
npx prisma migrate dev --name add_user_avatar
```

Apply pending migrations in production. This never generates, never prompts, and never resets:

```bash
npx prisma migrate deploy
```

Regenerate the client after any schema change:

```bash
npx prisma generate
```

Reset the database, in development only, because it drops everything:

```bash
npx prisma migrate reset
```

Never run `migrate dev` against a shared or production database. It compares the schema to the migration history and
will offer to reset when it finds drift.

---

### Schema

```prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  avatarUrl String?  @map("avatar_url")
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")
  orders    Order[]

  @@map("users")
  @@index([email])
}
```

Map every field and model to its snake_case database name with `@map` and `@@map`, so the Prisma client reads
idiomatically in TypeScript while the schema stays idiomatic in SQL.

---

### Custom SQL for what Prisma cannot express

Concurrent indexes, batched backfills, partial indexes, and triggers need hand-written SQL. Create the migration
without applying it, then edit the generated file:

```bash
npx prisma migrate dev --create-only --name add_email_index
```

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email);
```

`CREATE INDEX CONCURRENTLY` cannot run inside a transaction block. Prisma wraps each migration in one, so this statement
must be the only statement in its migration file.

---

### Drift and history

- Never edit a migration that has run anywhere but your own machine. Prisma records a checksum per migration and refuses
  to proceed when it changes.
- `npx prisma migrate resolve --applied <migration>` marks a migration as applied when you had to run it by hand.
- Keep `prisma/migrations/` in version control in full. It is the history, not a build artifact.

---

### Related skills

- `database-migrations` for the safety rules these commands have to satisfy.
- `node-backend-patterns` for the repository layer that consumes the generated client.
- `postgres-patterns` for the index and query-plan side of a schema change.
