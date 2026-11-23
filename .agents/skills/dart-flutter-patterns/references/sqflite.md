# sqflite

A SQLite service built on `sqflite`. Open this when the project stores relational data with `sqflite`. Picking a store, repositories and offline-first sync are in [databases-and-caching.md](databases-and-caching.md).

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
    if (existing != null) {
      return existing;
    }

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
