# Concurrency and Async

The event loop, when `async` is enough and when it is not, structured concurrency with futures and records, and
the two isolate patterns.

---

### The model

Dart runs on a single-threaded event loop per isolate. All Flutter application code runs on the main isolate by
default.

- `async` and `await` are non-blocking I/O. While a `Future` is pending the event loop keeps handling other
  events. They do not create a thread and they do not make CPU work cheaper.
- An isolate is Dart's unit of real parallelism. Isolates have separate heaps, share no state, and communicate by
  message passing.
- The main isolate renders the UI. Blocking it, even inside an `async` function, drops frames.
- A worker isolate takes CPU-bound work off the main isolate.

---

### Choosing an approach

| Work | Approach |
| --- | --- |
| I/O bound: HTTP, file, database read | `async` and `await` on the main isolate |
| CPU bound but under a frame budget | `async` and `await` on the main isolate |
| CPU bound, significant, one shot: decoding a large payload, image processing | `Isolate.run` |
| CPU bound, continuous, many messages over time | `Isolate.spawn` with `ReceivePort` and `SendPort` |

Measure before reaching for an isolate. Spawning one costs memory and a message round trip, so it only pays off
when the synchronous block genuinely exceeds a frame.

---

### Structured concurrency

Independent awaits should run together. Awaiting them in sequence costs the sum of their latencies for no reason.

```dart
// BAD, two round trips in series
final users = await userRepository.getAll();
final orders = await orderRepository.getRecent();

// GOOD, one round trip of wall time
final (users, orders) = await (
  userRepository.getAll(),
  orderRepository.getRecent(),
).wait;
```

The record `.wait` extension propagates a `ParallelWaitError` if any future fails, and that error carries the
per-future results so you can tell which one broke. Use `Future.wait` with a list when the futures are
homogeneous and their count is dynamic.

---

### Streams

Expose live data as a `Stream` from the repository and let the widget layer subscribe declaratively.

```dart
Stream<List<Item>> watchCartItems() =>
    _db.watchTable('cart_items').map((rows) => rows.map(Item.fromRow).toList());
```

```dart
StreamBuilder<List<Item>>(
  stream: cartRepository.watchCartItems(),
  builder: (context, snapshot) => switch (snapshot) {
    AsyncSnapshot(connectionState: ConnectionState.waiting) => const CircularProgressIndicator(),
    AsyncSnapshot(:final error?) => ErrorView(message: '$error'),
    AsyncSnapshot(:final data?) => CartList(items: data),
    _ => const SizedBox.shrink(),
  },
)
```

`StreamBuilder` owns the subscription and cancels it for you. When you subscribe manually with `listen`, store the
`StreamSubscription` and cancel it in `dispose`, or the callback outlives the widget.

---

### FutureBuilder

`FutureBuilder` is fine for a one-shot load, with one trap: calling the async function inside `build` restarts it
on every rebuild. Create the future once.

```dart
class _ProfilePageState extends State<ProfilePage> {
  late final Future<Profile> _profile = repository.loadProfile();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Profile>(
      future: _profile,
      builder: (context, snapshot) => switch (snapshot) {
        AsyncSnapshot(connectionState: ConnectionState.waiting) => const CircularProgressIndicator(),
        AsyncSnapshot(:final error?) => ErrorView(message: '$error'),
        AsyncSnapshot(:final data?) => ProfileView(profile: data),
        _ => const SizedBox.shrink(),
      },
    );
  }
}
```

---

### One-shot isolates

`Isolate.run` spawns an isolate, runs the closure, returns the value, and exits. Everything the closure captures
must be sendable, which in practice means primitives, collections of primitives, and plain data objects.

```dart
List<Object?> decodeHeavyJson(String jsonString) => jsonDecode(jsonString) as List<Object?>;

Future<List<Object?>> processInBackground(String rawJson) =>
    Isolate.run(() => decodeHeavyJson(rawJson));
```

`compute` from `package:flutter/foundation.dart` does the same thing with a single-argument callback and is
slightly more readable in widget-facing code. Either is correct.

---

### Long-lived worker isolates

Use `Isolate.spawn` when the work is continuous and messages flow both ways. The handshake is always the same:
the main isolate sends its `SendPort` in, the worker sends its own `SendPort` back, and both sides then have a
channel.

```dart
class WorkerManager {
  final ReceivePort _mainReceivePort = ReceivePort();
  SendPort? _workerSendPort;
  Isolate? _isolate;

  Future<void> initialize() async {
    _isolate = await Isolate.spawn(_workerEntry, _mainReceivePort.sendPort);

    _mainReceivePort.listen((message) {
      if (message is SendPort) {
        _workerSendPort = message;
        return;
      }
      _onResult(message);
    });
  }

  void send(Object task) => _workerSendPort?.send(task);

  static void _workerEntry(SendPort mainSendPort) {
    final workerReceivePort = ReceivePort();
    mainSendPort.send(workerReceivePort.sendPort);
    workerReceivePort.listen((message) => mainSendPort.send(process(message)));
  }

  void dispose() {
    _mainReceivePort.close();
    _isolate?.kill(priority: Isolate.immediate);
    _isolate = null;
  }
}
```

Closing both ports and killing the isolate in `dispose` is not optional. A live `ReceivePort` keeps the isolate,
and everything it references, alive for the process lifetime.

To call a plugin or platform channel from a background isolate, register it first with
`BackgroundIsolateBinaryMessenger.ensureInitialized(rootIsolateToken)`, passing a `RootIsolateToken` captured on
the main isolate.

---

### BuildContext after an await

Covered in the hub, repeated here because it is the most common async defect in Flutter code: after any `await`,
check `mounted` before touching `context`, or capture the context-derived object before the await.

---

### Checklist

- [ ] Independent awaits run concurrently through record `.wait` or `Future.wait`.
- [ ] No `await` sits inside a loop where the iterations are independent.
- [ ] Futures passed to `FutureBuilder` are created once, not inside `build`.
- [ ] Every manual `listen` has a matching `cancel` in `dispose`.
- [ ] An isolate was introduced only after measuring that the block exceeds a frame budget.
- [ ] Long-lived isolates close their ports and kill the isolate on dispose.
- [ ] Plugins used from a background isolate call `BackgroundIsolateBinaryMessenger.ensureInitialized` first.
- [ ] Every post-await `context` use is guarded.
