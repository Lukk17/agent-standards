# Indexes

Open this for the index table, the SQL and the reasoning behind the index rules in [SKILL.md](../SKILL.md), and for the query that finds a foreign key with no index.

---

### Pick the index that matches the predicate

| Query pattern | Index type | Example |
| --- | --- | --- |
| `WHERE col = value` | B-tree, the default | `CREATE INDEX idx ON t (col)` |
| `WHERE col > value` | B-tree | `CREATE INDEX idx ON t (col)` |
| `WHERE a = x AND b > y` | Composite | `CREATE INDEX idx ON t (a, b)` |
| `WHERE jsonb_col @> '{}'` | GIN | `CREATE INDEX idx ON t USING gin (col)` |
| `WHERE tsv @@ query` | GIN | `CREATE INDEX idx ON t USING gin (col)` |
| Time-series range scans on an append-only table | BRIN | `CREATE INDEX idx ON t USING brin (col)` |

Pass: equality columns first in a composite index, then the range column.

```sql
CREATE INDEX idx_orders_status_created ON orders (status, created_at);
```

Fail: `CREATE INDEX idx ON orders (created_at, status)` for `WHERE status = 'pending' AND created_at > $1`, which
cannot use the leading column for the equality and scans far more of the index than it needs.

Two variants worth reaching for:

```sql
CREATE INDEX idx_users_email_cover ON users (email) INCLUDE (name, created_at);
```

```sql
CREATE INDEX idx_users_email_active ON users (email) WHERE deleted_at IS NULL;
```

The first avoids a heap lookup when the query selects only the included columns. The second indexes only live rows, so
it stays small on a table dominated by soft-deleted ones.

---

### Find unindexed foreign keys

Unindexed foreign keys, which make every parent delete scan the child table. A foreign key counts as covered only when
its columns are the leading columns of a non-partial index, which is what the slice of `indkey` checks:

```sql
SELECT c.conrelid::regclass AS table_name, c.conname AS foreign_key
FROM pg_constraint c
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid
      AND i.indpred IS NULL
      AND (i.indkey::int2[])[0:cardinality(c.conkey) - 1] @> c.conkey
  );
```

The other diagnostic queries, for slow statements and dead rows, are in [diagnostic-queries.md](diagnostic-queries.md).
