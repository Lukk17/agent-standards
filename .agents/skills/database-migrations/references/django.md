# Django migrations

Read this when running migrations in a Django project.

---

### Workflow

Generate migrations from model changes:

```bash
python manage.py makemigrations
```

Apply pending migrations:

```bash
python manage.py migrate
```

Show what has run and what is pending:

```bash
python manage.py showmigrations
```

Create an empty migration to hold custom SQL or a data migration:

```bash
python manage.py makemigrations --empty app_name -n backfill_display_names
```

Print the SQL a migration will run, for review before it touches a production database:

```bash
python manage.py sqlmigrate app_name 0016
```

---

### Data migration

Keep data migrations in their own file, separate from the schema change that made them possible. Use
`apps.get_model()` rather than importing the model directly, because a migration must run against the historical model
as it existed then, not the current one.

```python
from django.db import migrations


def backfill_display_names(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    batch_size = 5000
    while True:
        batch = list(User.objects.filter(display_name="")[:batch_size])
        if not batch:
            break
        for user in batch:
            user.display_name = user.username
        User.objects.bulk_update(batch, ["display_name"], batch_size=batch_size)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0015_add_display_name")]

    operations = [
        migrations.RunPython(backfill_display_names, migrations.RunPython.noop),
    ]
```

Pass `migrations.RunPython.noop` as the reverse rather than an empty function, so the migration is explicitly reversible
and `migrate` backwards does not fail.

---

### Removing a column in two deploys

`SeparateDatabaseAndState` drops the field from Django's model state while leaving the column in place, so the running
code stops referencing it before the column disappears.

```python
class Migration(migrations.Migration):
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.RemoveField(model_name="user", name="legacy_field")],
            database_operations=[],
        ),
    ]
```

Deploy that, confirm nothing reads the column, then issue a plain `RemoveField` in the next migration to drop it for
real.

---

### Concurrent indexes

Django wraps each migration in a transaction, and `CREATE INDEX CONCURRENTLY` cannot run inside one. Use
`AddIndexConcurrently` from `django.contrib.postgres.operations` and set `atomic = False` on the migration class.

```python
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False
    operations = [AddIndexConcurrently("user", models.Index(fields=["email"], name="idx_user_email"))]
```

---

### Related skills

- `database-migrations` for the safety rules these commands have to satisfy.
- `python-patterns` for the surrounding application code.
- `postgres-patterns` for index selection and query plans.
