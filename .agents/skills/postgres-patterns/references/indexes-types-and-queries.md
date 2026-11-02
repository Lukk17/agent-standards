# Indexes, types and queries

Open this for the tables, SQL and reasoning behind the index, type, row-level security, statement and anti-pattern rules in [SKILL.md](../SKILL.md).

---

### Contents

- [Pick the index that matches the predicate](#pick-the-index-that-matches-the-predicate)
- [Choose the type that cannot be wrong](#choose-the-type-that-cannot-be-wrong)
- [Wrap the auth call in a row-level security policy](#wrap-the-auth-call-in-a-row-level-security-policy)
- [Use the right statement for the job](#use-the-right-statement-for-the-job)
- [Detect the common anti-patterns with a query](#detect-the-common-anti-patterns-with-a-query)

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

### Choose the type that cannot be wrong

| Use case | Correct type | Avoid |
| --- | --- | --- |
| Identifiers | `bigint`, or `uuid` v7 when it must be client-generated | `int`, random `uuid` v4 as a primary key |
| Strings | `text` | `varchar(255)` |
| Timestamps | `timestamptz` | `timestamp` |
| Money | `numeric(12,2)`, or an integer count of minor units | `float`, `real` |
| Flags | `boolean` | `varchar`, `int` |

Pass: `amount_minor bigint NOT NULL` for money, so no rounding exists to get wrong.

Fail: `price float`, which cannot represent 0.1 exactly and silently drifts across arithmetic.

`varchar(n)` buys no performance over `text` in PostgreSQL, and the length limit becomes a migration the first time the
business changes its mind.

---

### Wrap the auth call in a row-level security policy

```sql
-- PASS: the subquery is evaluated once per statement
CREATE POLICY orders_owner ON orders
  USING ((SELECT auth.uid()) = user_id);

-- FAIL: the function is re-evaluated for every row scanned
CREATE POLICY orders_owner ON orders
  USING (auth.uid() = user_id);
```

Index the column the policy filters on, or the policy turns every read into a sequential scan.

---

### Use the right statement for the job

Upsert without a race between the check and the insert:

```sql
INSERT INTO settings (user_id, key, value)
VALUES (123, 'theme', 'dark')
ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value;
```

Paginate by cursor, which is constant cost, rather than by offset, which is linear in the rows skipped:

```sql
SELECT * FROM products WHERE id > $1 ORDER BY id LIMIT 20;
```

Claim a queue row without two workers taking the same one:

```sql
UPDATE jobs SET status = 'processing'
WHERE id = (
  SELECT id FROM jobs WHERE status = 'pending'
  ORDER BY created_at LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

---

### Detect the common anti-patterns with a query

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

Slow statements by mean execution time:

```sql
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC;
```

Tables carrying dead rows that autovacuum is not keeping up with:

```sql
SELECT relname, n_dead_tup, last_vacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```
