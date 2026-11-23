# Java Examples

The language-neutral rules of this skill shown in Java. Open it when the code is Java.

---

### Functional pipeline

The rule and the cases where the loop stays are in [principles-in-depth.md](principles-in-depth.md#functional-pipelines-over-imperative-cascades).

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
