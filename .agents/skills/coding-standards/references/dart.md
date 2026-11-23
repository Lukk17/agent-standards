# Dart Examples

The language-neutral rules of this skill shown in Dart. Open it when the code is Dart.

---

### Functional pipeline

The rule and the cases where the loop stays are in [principles-in-depth.md](principles-in-depth.md#functional-pipelines-over-imperative-cascades).

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
