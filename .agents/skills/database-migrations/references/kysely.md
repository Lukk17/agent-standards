# Kysely migrations

Read this when running migrations with Kysely and kysely-ctl on a TypeScript or Node project.

---

### Workflow

Create the configuration file:

```bash
kysely init
```

Create a migration file:

```bash
kysely migrate make add_user_avatar
```

Apply every pending migration:

```bash
kysely migrate latest
```

Roll back the most recent migration:

```bash
kysely migrate down
```

Show what has run and what is pending:

```bash
kysely migrate list
```

---

### Migration file

```typescript
import { type Kysely, sql } from 'kysely'

export async function up(db: Kysely<any>): Promise<void> {
  await db.schema
    .createTable('user_profile')
    .addColumn('id', 'serial', (col) => col.primaryKey())
    .addColumn('email', 'varchar(255)', (col) => col.notNull().unique())
    .addColumn('avatar_url', 'text')
    .addColumn('created_at', 'timestamptz', (col) => col.defaultTo(sql`now()`).notNull())
    .execute()

  await db.schema
    .createIndex('idx_user_profile_avatar')
    .on('user_profile')
    .column('avatar_url')
    .execute()
}

export async function down(db: Kysely<any>): Promise<void> {
  await db.schema.dropTable('user_profile').execute()
}
```

Always type the parameter as `Kysely<any>`, never as your generated database interface. A migration is frozen at the
moment it was written, and typing it against the current interface makes an old migration stop compiling the moment the
schema moves on.

---

### Programmatic migrator

```typescript
import { Migrator, FileMigrationProvider } from 'kysely'
import { promises as fs } from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'

const migrationFolder = path.join(path.dirname(fileURLToPath(import.meta.url)), './migrations')

const migrator = new Migrator({ db, provider: new FileMigrationProvider({ fs, path, migrationFolder }) })

const { error, results } = await migrator.migrateToLatest()

results?.forEach((it) => {
  if (it.status === 'Error') logger.error({ migration: it.migrationName }, 'migration failed')
})

if (error) {
  logger.error({ err: error }, 'migration run failed')
  process.exit(1)
}
```

The `fileURLToPath` line is for ESM. Under CommonJS, use `__dirname` directly.

Leave `allowUnorderedMigrations` off. It disables timestamp-ordering validation, which is what stops two branches
merging into a history that applies differently in each environment.

---

### Related skills

- `database-migrations` for the safety rules these commands have to satisfy.
- `node-backend-patterns` for the repository layer built on the Kysely instance.
- `postgres-patterns` for index selection and query plans.
