# Drizzle migrations

Read this when running migrations with Drizzle ORM on a TypeScript or Node project.

---

### Workflow

Generate a SQL migration from the schema change:

```bash
npx drizzle-kit generate
```

Apply pending migrations:

```bash
npx drizzle-kit migrate
```

Push the schema straight to the database with no migration file. Development only, because there is no record of what
changed and no way to replay it:

```bash
npx drizzle-kit push
```

Inspect what the generator will do before it writes anything:

```bash
npx drizzle-kit check
```

---

### Schema

```typescript
import { pgTable, text, timestamp, uuid, boolean, index } from "drizzle-orm/pg-core";

export const users = pgTable("users", {
  id: uuid("id").primaryKey().defaultRandom(),
  email: text("email").notNull().unique(),
  name: text("name"),
  isActive: boolean("is_active").notNull().default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
}, (table) => [index("idx_users_email").on(table.email)]);
```

Use `timestamp(..., { withTimezone: true })` rather than a naive timestamp. A column without a time zone silently
records whatever the session zone happened to be.

---

### Hand-written SQL

Drizzle generates plain `.sql` files in the migrations folder, so editing one is the supported way to add what the
generator cannot express. Generate the file, then replace or extend its contents:

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email);
```

Keep a concurrent index in its own migration file, because Drizzle runs each file inside a transaction and
`CONCURRENTLY` cannot run inside one.

---

### Rules

- Commit the generated `.sql` files and the `meta/_journal.json` snapshot together. The journal is how Drizzle knows
  what has run.
- Never edit a migration that has been applied outside your machine. Generate a new one.
- Never use `push` against a shared database, however tempting it is for a small change. It leaves the environments with
  no shared history.

---

### Related skills

- `database-migrations` for the safety rules these commands have to satisfy.
- `node-backend-patterns` for the query layer built on the schema.
- `postgres-patterns` for index selection and query plans.
