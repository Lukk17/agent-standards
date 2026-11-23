# Dart Formatting Examples

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

The wrong and right form of each formatting rule in Dart. Each section carries the name of its rule in SKILL.md, and the full body and reasoning of every rule is in [rules-in-depth.md](rules-in-depth.md). Where the project runs dart format and it rewrites a construct, its output wins and the rule yields.

---

### Brace every inline exit

Wrong:

```dart
if (rows.isEmpty) return null;
```

Right:

```dart
if (rows.isEmpty) {
  return null;
}
```

### Blank line after a wrapped signature

Right:

```dart
Future<Receipt> settle(
  Order order, {
  required PaymentMethod method,
  Duration timeout = const Duration(seconds: 30),
}) async {

  final payload = mapper.toPayload(order, method);

  return client.send(payload, timeout: timeout);
}
```

### Empty lines around try, catch and finally

```dart
final messenger = ScaffoldMessenger.of(context);

try {
  await service.backup();

  if (!mounted) {
    return;
  }

  messenger.showSnackBar(const SnackBar(content: Text('Backup created.')));
} on BackupException catch (e) {
  if (!mounted) {
    return;
  }

  messenger.showSnackBar(SnackBar(content: Text('Backup failed: $e')));
}
```

### Empty line above a standalone async call

```dart
state = state.copyWith(running: true);

await _gateway.show(id: 1001, title: 'Rest over', body: 'Time to lift');

logFine('alarm fired', name: _tag);
```

### Empty line above a closing return

```dart
Future<void> _addWorkLog(Exercise e, DateTime date) async {
  final list = await _dao.getForDate(date);

  for (final w in list) {
    if (w.exercise.name == e.name) {
      await _dao.merge(w);

      return;
    }
  }

  await _dao.insert(WorkLog.create(exercise: e, on: date));
}
```

### Blank line below a return inside a try with clauses

The rule holds in Dart as stated in [rules-in-depth.md](rules-in-depth.md#blank-line-below-a-return-inside-a-try-with-clauses). The worked wrong and right form is the Java one in [java.md](java.md#blank-line-below-a-return-inside-a-try-with-clauses).

### Empty line above an operation-terminating call

Operation-terminators in Dart and Flutter: `Navigator.pop(context)`, `messenger.showSnackBar(...)`, `state = state.copyWith(...)`,
`_ticker?.cancel()`, `logFine('phase done')`.

```dart
final normalized = _startOfDay(day);
ref.read(selectedDateProvider.notifier).state = normalized;
logFine('Chosen date: $normalized', name: _tag);

Navigator.of(context).pop();
```

### Comments above the line, never trailing

Wrong:

```dart
final delay = computeBackoff(retryCount); // exponential, max 30s
```

Right:

```dart
// Exponential backoff, capped at 30s to avoid hammering the server.
final delay = computeBackoff(retryCount);
```

### Doc comments sit on their declaration

A tag line is a plain sentence in a Dart doc comment, on one physical line. The worked form is the Javadoc one in [java.md](java.md#doc-comments-sit-on-their-declaration).

### One concept per blank-separated paragraph

```dart
Future<void> save() async {
  final navigator = Navigator.of(context);
  final selectedDate = ref.read(selectedDateProvider);

  final updated = widget.exercise.copyWith(
    name: _nameController.text,
    bodyParts: form.primary,
  );
  await _dao.replace(updated);

  if (!mounted) {
    return;
  }

  ref.invalidate(exercisesProvider);

  navigator.pop();
}
```

### One chain step per line

dart format reflows a chain to fit the line, joining a short one back onto a single line, so where it runs, its output wins and this rule does not apply.

```dart
final activeNames = exercises
    .where((e) => e.isActive)
    .map((e) => e.name)
    .toList();
```

### Single-expression bodies stay on one line

```dart
int doubled(int x) => x * 2;
DateTime startOfDay(DateTime d) => DateTime(d.year, d.month, d.day);
```
