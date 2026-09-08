# Databases and Caching

Local persistence with SQLite and its wrappers, repositories as the single source of truth, offline-first
synchronization, and the caching layers above it (files, images, scroll extents, and the Android engine).

---

### Picking a store

| Data | Store |
| --- | --- |
| Small key-value settings, theme, flags | `shared_preferences` |
| Secrets, tokens, credentials | `flutter_secure_storage`, never `shared_preferences` |
| Structured relational data | `sqflite`, or `drift` when you want typed queries and migrations |
| Structured document data | `hive_ce` or `isar_community` |
| Binary blobs and large media | The file system through `path_provider` |
| Remote images | `cached_network_image` |

`getApplicationDocumentsDirectory()` holds data the user would miss. `getTemporaryDirectory()` holds data the OS
may delete at any time. Put a cache in the second one.

---

### Repositories and services

The data layer splits in two, exactly as in [architecture.md](architecture.md).

Services are stateless wrappers around one source each: an HTTP client, a SQLite database, a platform plugin.
They perform no business logic beyond serialization and return raw models.

Repositories are the single source of truth for one domain entity. They consume services as private members,
own caching, polling, retry, and offline sync, and map raw models into domain models that carry only what the UI
needs. Strip backend-only fields such as pagination tokens and metadata before they leave the repository.

---

### SQLite service

- Add `sqflite` and `path`. Build the file path with `join(await getDatabasesPath(), 'app.db')` so it is correct
  on every platform.
- Declare table and column names as constants. A typo in a string literal fails at runtime, a typo in a constant
  fails at compile time.
- Use `id INTEGER PRIMARY KEY AUTOINCREMENT`.
- Always pass values through `whereArgs`. String interpolation into a `where` clause is SQL injection.

```dart
class DatabaseService {
  static const String _tableName = 'todos';
  static const String _colId = 'id';
  static const String _colTask = 'task';
  static const String _colIsSynced = 'is_synced';

  Database? _database;

  Future<Database> _open() async {
    final existing = _database;
    if (existing != null) return existing;

    final dbPath = join(await getDatabasesPath(), 'app_database.db');
    final opened = await openDatabase(
      dbPath,
      version: 1,
      onCreate: (db, version) => db.execute(
        'CREATE TABLE $_tableName('
        '$_colId INTEGER PRIMARY KEY AUTOINCREMENT, '
        '$_colTask TEXT NOT NULL, '
        '$_colIsSynced INTEGER NOT NULL DEFAULT 0)',
      ),
    );
    _database = opened;
    return opened;
  }

  Future<void> updateTodo(TodoDbModel todo) async {
    final db = await _open();
    await db.update(
      _tableName,
      todo.toMap(),
      where: '$_colId = ?',
      whereArgs: [todo.id],
    );
  }
}
```

Returning the non-null `Database` from `_open` removes the nullable handle from every call site, so no caller ever
reaches for `!`.

---

### Offline-first synchronization

Reads yield the cached rows first so the UI paints immediately, then fetch, write through, and yield fresh data.

```dart
class TodoRepository {
  TodoRepository({required DatabaseService database, required ApiClientService api})
      : _database = database,
        _api = api;

  final DatabaseService _database;
  final ApiClientService _api;

  Stream<List<Todo>> observeTodos() async* {
    final local = await _database.getAllTodos();
    if (local.isNotEmpty) yield local.map(Todo.fromDbModel).toList();

    try {
      final remote = await _api.fetchTodos();
      await _database.replaceAllTodos(remote);
      yield remote.map(Todo.fromApiModel).toList();
    } on Exception catch (error, stack) {
      log('todo refresh failed', error: error, stackTrace: stack);
    }
  }

  Future<void> createTodo(Todo todo) async {
    final draft = todo.toDbModel().copyWith(isSynced: false);
    await _database.insertTodo(draft);

    try {
      final saved = await _api.postTodo(todo.toApiModel());
      await _database.updateTodo(draft.copyWith(id: saved.id, isSynced: true));
    } on Exception catch (error, stack) {
      log('todo sync deferred', error: error, stackTrace: stack);
    }
  }
}
```

Writes pick one of two strategies:

- Online-only, when the server must agree before the user sees the change. Call the API first, write locally only
  on success.
- Offline-first, when availability matters more. Write locally at once, attempt the API, and on failure leave the
  row flagged unsynchronized for a background task to retry.

The `isSynced` flag lives on an immutable model, so flip it with `copyWith` and write the new instance back rather
than mutating in place. Run the retry sweep from `workmanager` or a `Timer`, selecting rows where the flag is
false.

Never swallow the exception silently. Log it, or surface an error state, so a permanently failing sync is visible.

---

### Image caching

Image decode and I/O are the most expensive things most apps do.

- Use `cached_network_image` for remote images. It handles the file-system cache and the placeholder.
- A custom `ImageProvider` overrides `createStream()` and `resolveStreamForKey()`. `resolve()` is deprecated.
- `ImageCache.maxByteSize` no longer grows automatically for a large image. Raise it explicitly, or subclass
  `ImageCache` with your own eviction, when the app loads images bigger than the default budget.
- Give `Image.network` a `cacheWidth` or `cacheHeight` matching the on-screen size so a 4000 pixel photo is not
  decoded at full resolution to fill a thumbnail.

---

### Scroll caching

Configure the off-screen retention of a `ListView`, `GridView`, or `Viewport` with `scrollCacheExtent`. The old
`cacheExtent` and `cacheExtentStyle` properties are deprecated.

```dart
ListView(
  scrollCacheExtent: const ScrollCacheExtent.pixels(500),
  children: items,
)
```

```dart
Viewport(
  scrollCacheExtent: const ScrollCacheExtent.viewport(0.5),
  slivers: slivers,
)
```

---

### Widget caching

- Do not override `operator ==` on a `Widget`. It makes rebuilds O(N squared).
- The one exception is a leaf widget with no children whose properties are cheap to compare and rarely change.
- Prefer `const` constructors. They let the framework short-circuit the rebuild without any comparison at all.

---

### Pre-warming the Android FlutterEngine

When Flutter is embedded in an existing Android app, the engine warm-up is visible as a blank frame. Cache it.

```kotlin
val flutterEngine = FlutterEngine(this)
flutterEngine.navigationChannel.setInitialRoute("/cached_route")
flutterEngine.dartExecutor.executeDartEntrypoint(DartEntrypoint.createDefault())
FlutterEngineCache.getInstance().put("my_engine_id", flutterEngine)
```

```kotlin
startActivity(FlutterActivity.withCachedEngine("my_engine_id").build(this))
```

Create and warm the engine in the `Application` class, and register that class in `AndroidManifest.xml`. The
initial route cannot be set through the activity builder once the engine is cached, so set it on the navigation
channel before executing the entrypoint.

---

### Checklist

- [ ] Secrets are in `flutter_secure_storage`, never `shared_preferences`.
- [ ] Every SQL value goes through `whereArgs`, with no interpolation into a `where` clause.
- [ ] Table and column names are constants.
- [ ] The database handle is returned non-null from an open helper, so no call site force-unwraps.
- [ ] Repositories are the only place that writes application data.
- [ ] The sync flag is flipped with `copyWith`, never mutated in place.
- [ ] Failed background syncs are logged or surfaced, never silently swallowed.
- [ ] Remote images go through `cached_network_image`, with `cacheWidth` where the display size is known.
- [ ] Scroll retention uses `scrollCacheExtent`, not the deprecated `cacheExtent`.
- [ ] Offline behaviour was exercised with the network actually disabled.
