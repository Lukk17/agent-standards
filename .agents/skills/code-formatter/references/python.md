# Python Formatting Examples

Contents:

- [Brace every inline exit](#brace-every-inline-exit)
- [Blank line after a wrapped signature](#blank-line-after-a-wrapped-signature)
- [Empty lines around try, catch and finally](#empty-lines-around-try-catch-and-finally)
- [Empty line above a standalone async call](#empty-line-above-a-standalone-async-call)
- [Empty line above a closing return](#empty-line-above-a-closing-return)
- [Blank line below a return inside a try with clauses](#blank-line-below-a-return-inside-a-try-with-clauses)
- [Empty line above an operation-terminating call](#empty-line-above-an-operation-terminating-call)
- [Comments above the line, never trailing](#comments-above-the-line-never-trailing)
- [Doc comments sit on their declaration](#doc-comments-sit-on-their-declaration)
- [One concept per blank-separated paragraph](#one-concept-per-blank-separated-paragraph)
- [One chain step per line](#one-chain-step-per-line)
- [Single-expression bodies stay on one line](#single-expression-bodies-stay-on-one-line)

The wrong and right form of each formatting rule in Python. Each section carries the name of its rule in SKILL.md, and the full body and reasoning of every rule is in [rules-in-depth.md](rules-in-depth.md). Where the project runs ruff format or black and it rewrites a construct, its output wins and the rule yields.

---

### Brace every inline exit

Wrong:

```python
if not rows: return None
```

Right:

```python
if not rows:
    return None
```

### Blank line after a wrapped signature

Right, where the formatter keeps the line:

```python
def schedule_reminder(
    owner_id: UUID,
    remind_at: datetime,
    channel: ReminderChannel,
) -> Reminder:

    reminder = Reminder(owner_id=owner_id, remind_at=remind_at, channel=channel)

    return repository.save(reminder)
```

### Empty lines around try, catch and finally

```python
logger = logging.getLogger(__name__)

try:
    service.backup()

    logger.info("backup complete")
except BackupError as e:
    logger.error("backup failed: %s", e)
```

### Empty line above a standalone async call

```python
state.running = True

await gateway.show(id=1001, title="Rest over", body="Time to lift")

logger.info("alarm fired")
```

### Empty line above a closing return

```python
async def add_work_log(exercise: Exercise, date: date) -> None:
    existing = await dao.get_for_date(date)

    for w in existing:
        if w.exercise.name == exercise.name:
            await dao.merge(w)

            return

    await dao.insert(WorkLog.create(exercise=exercise, on=date))
```

### Blank line below a return inside a try with clauses

The rule holds in Python as stated in [rules-in-depth.md](rules-in-depth.md#blank-line-below-a-return-inside-a-try-with-clauses). The worked wrong and right form is the Java one in [java.md](java.md#blank-line-below-a-return-inside-a-try-with-clauses).

### Empty line above an operation-terminating call

Operation-terminators in Python: `dialog.dismiss()`, `requests.post(...)`, `logger.info("phase done")`, `sys.exit(0)`.

```python
normalized = start_of_day(day)
state.selected_date = normalized
logger.info("Chosen date: %s", normalized)

dialog.dismiss()
```

### Comments above the line, never trailing

Wrong:

```python
delay = compute_backoff(retry_count)  # exponential, max 30s
```

Right:

```python
# Exponential backoff, capped at 30s to avoid hammering the server.
delay = compute_backoff(retry_count)
```

### Doc comments sit on their declaration

A tag line is an entry under `Args:`, `Returns:` or `Raises:` in a Python docstring, each on one physical line. The worked form is the Javadoc one in [java.md](java.md#doc-comments-sit-on-their-declaration).

### One concept per blank-separated paragraph

```python
async def save() -> None:
    navigator = activity.navigator
    selected_date = repository.selected_date

    updated = replace(
        original,
        name=name_field.text,
        body_parts=form.primary,
    )
    await dao.replace(updated)

    if is_destroyed():
        return

    event_bus.publish(ExercisesInvalidated())

    navigator.pop()
```

### One chain step per line

Python's idiomatic equivalent is a comprehension, so reach for that first. A Python project almost always runs ruff
format or black, which own how any chain wraps, so this rule rarely applies to Python at all. Both reflow a chain to fit the line, joining a short one back onto a single line, so where one of them runs, its output wins.

```python
active_names = [e.name for e in exercises if e.is_active]
```

### Single-expression bodies stay on one line

```python
def doubled(x: int) -> int:
    return x * 2

sorted(items, key=lambda i: i.priority)
```
