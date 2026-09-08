# Functional Pipelines

The full treatment of the pipeline rule, with worked examples per language and the cases where an imperative loop is
the right answer. Load this file when converting a loop, or when deciding whether a given loop should be converted at
all.

---

When transforming a collection, filter then map then aggregate, prefer a pipeline with one operation per step
reading top down, over an imperative loop with an if-else cascade and an explicit accumulator. The pipeline reads as
what is being done to the data. The cascade reads as how the bookkeeping goes.

This is a code-shape rule, not a syntax-level formatting one. The sibling `code-formatter` skill says one chain step
per line. This rule says reach for the chain in the first place.

---

### Dart

```dart
// BAD: imperative cascade
final activeNames = <String>[];
for (final e in exercises) {
  if (e.isActive) {
    activeNames.add(e.name);
  }
}

// GOOD: pipeline
final activeNames = exercises
    .where((e) => e.isActive)
    .map((e) => e.name)
    .toList();
```

---

### Java

Java's `Stream` API and `Optional` are designed for exactly this. A loop with an `if` and a `list.add` where a stream
would do is a code smell in modern Java.

```java
// BAD
List<String> activeNames = new ArrayList<>();
for (Exercise e : exercises) {
    if (e.isActive()) {
        activeNames.add(e.name());
    }
}

// GOOD
List<String> activeNames = exercises.stream()
    .filter(Exercise::isActive)
    .map(Exercise::name)
    .toList();

// Same principle for nullable values: reach for Optional, not if-null
// BAD
Exercise e = repository.findById(id);
if (e != null) {
    return e.name();
} else {
    return "unknown";
}

// GOOD
return repository.findById(id)
    .map(Exercise::name)
    .orElse("unknown");
```

---

### Python

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

---

### When NOT to convert

- Side effects inside the loop body, such as writing to disk, calling an API with an index-dependent argument, or
  mutating an outside variable. Those belong in an explicit loop, because a pipeline should be pure.
- Early termination on a complex condition that does not map cleanly onto a take-while or a first-match operation.
- Cases where the cascade is genuinely clearer to a reader unfamiliar with the codebase style. Clarity outranks
  compactness.

The point is prefer, not always.
