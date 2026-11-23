# Query patterns

Open this for the SQL behind the upsert, cursor pagination and queue claim rule in [SKILL.md](../SKILL.md).

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
