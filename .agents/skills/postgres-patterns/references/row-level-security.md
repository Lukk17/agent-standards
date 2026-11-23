# Row-level security

Open this for the policy SQL behind the row-level security rule in [SKILL.md](../SKILL.md).

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
