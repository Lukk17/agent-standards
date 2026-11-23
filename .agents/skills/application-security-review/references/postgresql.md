# Row-Level Security in PostgreSQL

The PostgreSQL form of the row-level security rule: the policies, how the identity is set, and which role the application connects as. Open this when the database is PostgreSQL or a managed platform built on it. The rule itself is under Authorization in [application-controls.md](application-controls.md).

---

### Policies

Enable row-level security on every table holding user data, force it, and write the policy per operation.

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

CREATE POLICY users_select_own ON users
  FOR SELECT
  USING (id = nullif(current_setting('app.current_user_id', true), '')::uuid);

CREATE POLICY users_update_own ON users
  FOR UPDATE
  USING (id = nullif(current_setting('app.current_user_id', true), '')::uuid);
```

---

### Setting the identity

Set the identity per transaction with `set_config('app.current_user_id', $1, true)` (the `SET LOCAL` form), never per
connection, because a pooled connection serves the next user with whatever value it still holds. The second argument
of `current_setting` makes a setting that was never set read as null, but once a transaction that set it ends, the
setting reads as an empty string, which a bare `::uuid` cast rejects with an error. `nullif(..., '')` turns both into
null, so a request with no identity matches no row instead of raising.

```sql
SELECT set_config('app.current_user_id', $1, true);
```

---

### The connecting role

The application connects as a role that does not own the table and has no `BYPASSRLS`, because table owners
skip the policy unless it is forced, and superusers and `BYPASSRLS` roles always skip it.

Managed platforms expose their own equivalent, such as an `auth.uid()` function, and the policy shape is the same
either way. Row-level security is an addition to application authorization checks, never a replacement for them.
