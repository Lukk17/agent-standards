# Python Examples

The language-neutral rules of this skill shown in Python. Open it when the code is Python.

---

### Functional pipeline

The rule and the cases where the loop stays are in [principles-in-depth.md](principles-in-depth.md#functional-pipelines-over-imperative-cascades).

Python's idiomatic equivalent is a comprehension, or a generator expression for a lazy stream. Reach for one of those
before reaching for an explicit loop with an `if` and a `list.append`.

```python
# BAD
active_names = []
for e in exercises:
    if e.is_active:
        active_names.append(e.name)

# GOOD
active_names = [e.name for e in exercises if e.is_active]

# When the transformation is heavier than a single expression, a
# generator + sum/max/min/any/all keeps the pipeline shape:
total_reps = sum(s.reps for s in series if s.reps > 0)
```
