---
name: code-formatter
description: Universal source-code formatting patterns the project owner expects, opinionated about visual hierarchy and reading flow rather than line length. Triggers on any new code, code review, or refactor across Dart, Java, Python, Kotlin, TypeScript, and Go. Apply these whenever you write or modify a function body so the next reader can locate control-flow exits and async phase transitions in one scan. Intentionally diverges from default auto-formatters (gofmt, dart format, black, google-java-format) in specific places; see each rule.
origin: workout_log
---

# Code Formatter

## When to activate

- Writing new source files in any language listed in the description.
- Editing existing files: apply these rules when the file is already in this style; don't silently auto-format an
  unrelated file.
- Reviewing a PR or a teammate's branch and flagging readability issues.

These rules are about *visual hierarchy*: how a reader's eyes find the landmarks of a function, not about line length
or column alignment. Default tooling tends to optimise for line length and consistency; this skill optimises for "the
next person reading this can locate the control-flow exits and async phase transitions in one scan."

## Rules

### Brace every inline `if (x) return y;` / `if (x) throw z;`

A control-flow exit should never share a line with its condition. The reader's eye should land on a `return` or
`throw` *as a line*, not as the tail of an `if`. Multi-line, braced, body indented.

**Java (wrong)**

```java
if (rows.isEmpty()) return null;
```

**Java (right)**

```java
if (rows.isEmpty()) {
    return null;
}
```

**Python (wrong)**

```python
if not rows: return None
```

**Python (right)**

```python
if not rows:
    return None
```

**Dart (wrong)**

```dart
if (rows.isEmpty) return null;
```

**Dart (right)**

```dart
if (rows.isEmpty) {
  return null;
}
```

### Empty lines around `try` / `catch` / `finally`

A `try` block is a control-flow landmark: it tells the reader "things can go wrong here." Give it room to breathe
before and after so the eye treats it as a phase, not buried text. Same for each `catch` / `finally` clause's body.

**Java**

```java
var logger = LoggerFactory.getLogger(getClass());

try {
    service.backup();

    logger.info("backup complete");
} catch (BackupException e) {
    logger.error("backup failed", e);
}
```

**Python**

```python
logger = logging.getLogger(__name__)

try:
    service.backup()

    logger.info("backup complete")
except BackupError as e:
    logger.error("backup failed: %s", e)
```

**Dart**

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

### Empty line above significant standalone `await` / async I/O

When an async call marks a phase transition in a function (setup, then I/O, then cleanup), give it a blank line
above. The reader's eye should register "now we hand off to the network/disk" as a distinct beat. This applies to
**standalone** awaits, not awaits embedded in an assignment expression.

**Java**

```java
state = state.toBuilder().running(true).build();

CompletableFuture<Void> shown = gateway.show(1001, "Rest over", "Time to lift");

logger.info("alarm fired");
```

**Python**

```python
state.running = True

await gateway.show(id=1001, title="Rest over", body="Time to lift")

logger.info("alarm fired")
```

**Dart**

```dart
state = state.copyWith(running: true);

await _gateway.show(id: 1001, title: 'Rest over', body: 'Time to lift');

logFine('alarm fired', name: _tag);
```

### Empty line above `return` when it ends a multi-statement block

When a function does several things and then returns, the `return` gets a blank line above so it reads as "and now
hand back the result" rather than blending into the last statement. Doesn't apply to single-statement bodies, arrow
functions, or one-line `def`s; the blank-line rules apply to *blocks*.

**Java**

```java
public Optional<WorkLog> findFor(Exercise e, LocalDate date) {
    var list = dao.getForDate(date);

    for (var w : list) {
        if (w.exercise().name().equals(e.name())) {
            dao.merge(w);

            return Optional.of(w);
        }
    }

    return Optional.empty();
}
```

**Python**

```python
async def add_work_log(exercise: Exercise, date: date) -> None:
    existing = await dao.get_for_date(date)

    for w in existing:
        if w.exercise.name == exercise.name:
            await dao.merge(w)

            return

    await dao.insert(WorkLog.create(exercise=exercise, on=date))
```

**Dart**

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

### Blank line below `return` inside a `try` that has `catch` / `finally`

When a `try` block ends with `return X;` and is followed by a `catch` or `finally` clause, leave a blank line between
the `return` and the closing `}` of the try. The blank line marks the hand-off from the happy-path body to the
failure / cleanup clauses, so the reader's eye can see the seam.

**Java (wrong)**

```java
try {
    String xml = xmlGenerationService.generateXml(documents);

    log.info("audit xml.generation success documentType={} bytes={}",
            documentType, subject, xml.length());

    return xml;
} catch (XmlMappingException ex) {
    ...
} finally {
    ...
}
```

**Java (right)**

```java
try {
    String xml = xmlGenerationService.generateXml(documents);

    log.info("audit xml.generation success documentType={} bytes={}",
            documentType, subject, xml.length());

    return xml;

} catch (XmlMappingException ex) {
    ...
} finally {
    ...
}
```

The same rule applies to a `throw` that ends a `try` body when a `catch` / `finally` follows it.

### Empty line above operation-terminating calls

Calls that *end* a phase get a blank line above. The eye should see "the act" separated from the local-var arithmetic
that prepared for it. Examples of operation-terminators in each language:

- **Java**: `dialog.dismiss()`, `httpClient.send(...)`, `logger.info("phase done", ...)`, `eventBus.publish(...)`
- **Python**: `dialog.dismiss()`, `requests.post(...)`, `logger.info("phase done")`, `sys.exit(0)`
- **Dart / Flutter**: `Navigator.pop(context)`, `messenger.showSnackBar(...)`, `state = state.copyWith(...)`,
  `_ticker?.cancel()`, `logFine('phase done')`

**Java**

```java
var normalized = startOfDay(day);
state.setSelectedDate(normalized);
logger.info("Chosen date: {}", normalized);

dialog.dismiss();
```

**Python**

```python
normalized = start_of_day(day)
state.selected_date = normalized
logger.info("Chosen date: %s", normalized)

dialog.dismiss()
```

**Dart**

```dart
final normalized = _startOfDay(day);
ref.read(selectedDateProvider.notifier).state = normalized;
logFine('Chosen date: $normalized', name: _tag);

Navigator.of(context).pop();
```

### Comments above the line they describe, never trailing

Trailing comments get truncated by long lines and force horizontal scrolling. A comment is a sentence about the next
thing the reader is about to see; write it on its own line, above.

**Java (wrong)**

```java
var delay = computeBackoff(retryCount); // exponential, max 30s
```

**Java (right)**

```java
// Exponential backoff, capped at 30s to avoid hammering the server.
var delay = computeBackoff(retryCount);
```

**Python (wrong)**

```python
delay = compute_backoff(retry_count)  # exponential, max 30s
```

**Python (right)**

```python
# Exponential backoff, capped at 30s to avoid hammering the server.
delay = compute_backoff(retry_count)
```

**Dart (wrong)**

```dart
final delay = computeBackoff(retryCount); // exponential, max 30s
```

**Dart (right)**

```dart
// Exponential backoff, capped at 30s to avoid hammering the server.
final delay = computeBackoff(retryCount);
```

Exception: throwaway tag comments tied to an issue tracker (e.g. `// TODO(ABC-123): drop after Q3`) sometimes trail by
team convention. Even then, prefer the comment above when there's room.

### One concept per blank-line-separated paragraph

Inside a function body, related lines stick together with no blank between them; a topic transition gets one blank.
Two blank lines anywhere inside a function body is a smell; extract a method.

**Java**

```java
public void save() {
    var navigator = activity.getNavigator();
    var selectedDate = repository.getSelectedDate();

    var updated = original.toBuilder()
        .name(nameField.getText())
        .bodyParts(form.getPrimary())
        .build();
    dao.replace(updated);

    if (isDestroyed()) {
        return;
    }

    eventBus.publish(new ExercisesInvalidated());

    navigator.pop();
}
```

**Python**

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

**Dart**

```dart
Future<void> save() async {
  final navigator = Navigator.of(context);
  final selectedDate = ref.read(selectedDateProvider);

  final updated = widget.exercise!.copyWith(
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

Each paragraph reads as a phase: capture context, build and persist, mounted-guard, invalidate dependents, exit.

### Method chains: line-break before each `.`

Fluent / functional pipelines (filter, map, reduce, take, toList, collect) read top-down, one transformation per
line. Easier to diff, easier to insert or remove a step.

**Java**

```java
var activeNames = exercises.stream()
    .filter(Exercise::isActive)
    .map(Exercise::name)
    .toList();
```

**Python**

Python's idiomatic equivalent is a comprehension; reach for that first. When you do chain (e.g. with a `pipe` helper
or pandas), keep one step per line:

```python
active_names = [e.name for e in exercises if e.is_active]

active_names = (pipe(exercises)
    .filter(lambda e: e.is_active)
    .map(lambda e: e.name)
    .to_list()
)
```

**Dart**

```dart
final activeNames = exercises
    .where((e) => e.isActive)
    .map((e) => e.name)
    .toList();
```

The *prefer chains over loops* part is a coding-standards rule, not a formatter one. The formatter point here is:
*when* you do chain, one step per line.

### Single-expression bodies stay on one line

The blank-line rules apply to *blocks*, not arrow functions or one-line `def`s. Don't expand a pure transformation
into a multi-line body just to satisfy a "blank line above return" rule that doesn't apply.

**Java**

```java
Function<Integer, Integer> doubled = x -> x * 2;
record Exercise(String id, String name) {
    boolean isActive() { return !name.isBlank(); }
}
```

**Python**

```python
def doubled(x: int) -> int:
    return x * 2

sorted(items, key=lambda i: i.priority)
```

**Dart**

```dart
int doubled(int x) => x * 2;
DateTime startOfDay(DateTime d) => DateTime(d.year, d.month, d.day);
```

## What this skill does not cover

- Naming conventions, class-member ordering, import ordering: those vary per language. See language-specific style
  guides (PEP 8, Google Java Style, Effective Dart) and the `coding-standards` skill.
- Line length caps: kept readable by extracting locals rather than wrapping. Each project sets its own column budget.
- Trailing commas, brace placement, indent width: handled by the default formatter for each language; this skill
  doesn't override those.
