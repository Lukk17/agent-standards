# Dart and Flutter Core Rules in Depth

The baseline detail, the BAD and GOOD examples, and the reasoning behind each rule the SKILL.md hub states in one or two lines, plus the related skills. Open it when a hub rule needs its worked form or its full explanation. Written for Dart 3 and Flutter 3.

---

### Contents

- Baseline
- Never force-unwrap
- Model state as a sealed type, never as nullable flags
- Guard BuildContext across every await
- Extract widgets to classes, not to builder methods
- Match the project's state management
- Match the project's HTTP client
- Keep constraints bounded
- Move CPU work off the main isolate
- Route every user-facing string through localization
- Related skills

---

### Baseline

Written for Dart 3 and Flutter 3. Confirm the installed SDK with `flutter --version`. Four defaults follow and change how code is written:

- Material 3 is the default for `ThemeData`. Do not set `useMaterial3`, it is the only behaviour left.
- Impeller is the default renderer on iOS and Android. Profile jank against Impeller, not the retired Skia path.
- `flutter build web --wasm` compiles to WebAssembly, where `dart:html`, `dart:js`, and `package:js` do not work.
  Use `package:web` and `dart:js_interop`.
- The `flutter_gen` synthetic package is removed, so localizations import as
  `package:<your_app>/l10n/app_localizations.dart`, never `package:flutter_gen/...`.

Turn the strict analyzer modes on in `analysis_options.yaml` so the rules below are enforced by tooling rather
than by review. The exact block is in [references/architecture.md](architecture.md).

---

### Never force-unwrap

`!` turns a compile-time question into a runtime crash. Dart already has an expression that carries the null case,
and `late` is the same failure mode one step removed. Reserve `late` for a field initialised in `initState` before
any read, or a `late final` field with an inline initializer, such as an `AnimationController` built with
`vsync: this`, which runs on first read and so cannot be read unset. Use a nullable field everywhere else.

```dart
// BAD
final name = user!.name;
final ok = _formKey.currentState!.validate();

// GOOD
final name = user?.name ?? 'Unknown';
final ok = _formKey.currentState?.validate() ?? false;
```

---

### Model state as a sealed type, never as nullable flags

A bag of `isLoading`, `data`, and `error` can represent loading with an error and no data, which is not a real
state. A sealed hierarchy makes that unrepresentable and makes `switch` exhaustive.

```dart
// BAD
class UserState { bool isLoading = false; User? user; String? error; }

// GOOD
sealed class UserState {}
final class UserLoading extends UserState { const UserLoading(); }
final class UserLoaded extends UserState { const UserLoaded(this.user); final User user; }
final class UserFailed extends UserState { const UserFailed(this.message); final String message; }

Widget build(BuildContext context) => switch (state) {
  UserLoading() => const CircularProgressIndicator(),
  UserLoaded(:final user) => UserCard(user: user),
  UserFailed(:final message) => ErrorView(message: message),
};
```

Riverpod's `AsyncValue<T>` is this prebuilt. Generate data-class immutability with `freezed`, not by hand.

---

### Guard BuildContext across every await

After an `await` the widget may be gone and the captured `context` points at a dead element. Without a `mounted`
field, capture what you need before the await and use the captured object afterwards.

```dart
// BAD
await authService.login(email, password);
context.go('/home');

// GOOD
await authService.login(email, password);
if (!mounted) {
  return;
}
context.go('/home');
```

---

### Extract widgets to classes, not to builder methods

A `Widget _buildHeader()` returns a subtree owned by the caller's element, so it rebuilds with the caller and can
never be `const`. A separate class gets its own element and stops a rebuild dead. Push `const` as far up the tree
as it goes, and keep the widget that watches changing state small.

```dart
// BAD
Widget _buildHeader() => Padding(padding: const EdgeInsets.all(16), child: Text(title));

// GOOD
class _PageHeader extends StatelessWidget {
  const _PageHeader(this.title);
  final String title;
  @override
  Widget build(BuildContext c) => Padding(padding: const EdgeInsets.all(16), child: Text(title));
}
```

---

### Match the project's state management

Riverpod, BLoC, and `ChangeNotifier` all work. Mixing two in one feature is worse than any of them alone, so read
the existing code first and follow it.

- Riverpod fits when dependencies form a graph and most state derives from other state. It is also the DI
  container, so do not add `get_it` beside it.
- BLoC fits event-driven features where the event log helps debugging and the team wants one rigid shape. Pair it
  with `get_it` and `injectable` for DI.
- `ChangeNotifier` with `Provider` fits small apps and a single screen's local state. It is a first-class Flutter
  class, not a deprecated one. It mutates in place, so keep the notified value immutable and replace it wholesale.

```dart
@riverpod
class CartNotifier extends _$CartNotifier {
  @override
  List<CartItem> build() => const [];
  void clear() => state = const [];
}

class AuthCubit extends Cubit<AuthState> {
  AuthCubit(this._service) : super(const AuthLoading());
  final AuthService _service;
  Future<void> login(String email, String password) async =>
      emit(AuthLoaded(await _service.login(email, password)));
}

class CartModel extends ChangeNotifier {
  List<CartItem> _items = const [];
  List<CartItem> get items => _items;
  void clear() { _items = const []; notifyListeners(); }
}
```

Never run two of these in the same feature, and never expose a mutable collection from any of them. Worked
examples of all three sit in [references/architecture.md](architecture.md).

---

### Match the project's HTTP client

`package:http` and `package:dio` are both correct. `http` is smaller and is what the Flutter team documents. `dio`
adds interceptors, cancellation, and typed errors, which pay off once you need token refresh or retries. Check
`pubspec.yaml` first and use whichever is there.

```dart
// package:http
final response = await client.get(Uri.https('api.example.com', '/users/$id'));
if (response.statusCode != 200) {
  throw HttpException('GET /users/$id failed');
}
final user = User.fromJson(jsonDecode(response.body) as Map<String, dynamic>);

// package:dio
final response = await dio.get<Map<String, dynamic>>('/users/$id');
final data = response.data;
if (data == null) {
  throw ApiException('GET /users/$id returned no body');
}
final user = User.fromJson(data);
```

Both get the same treatment: never concatenate a host or a query string, check the status code and throw rather
than returning null, and never leave a token in source. `package:http` builds its URL with `Uri.https`. `dio` takes
the host from `baseUrl` in its `BaseOptions` and query values through `queryParameters`.

---

### Keep constraints bounded

Constraints go down, sizes go up, the parent sets position. A scrollable inside a flex box gets unbounded space on
the main axis and throws. Bound it rather than hardcoding a height.

```dart
// BAD
Column(children: [const Text('Header'), ListView(children: items)])

// GOOD
Column(children: [const Text('Header'), Expanded(child: ListView(children: items))])
```

---

### Move CPU work off the main isolate

`async` and `await` do not create a thread, so an expensive synchronous parse still blocks the frame. I/O bound
work stays on the main isolate. Use `Isolate.run` only when a synchronous block measurably exceeds a frame budget,
and `Isolate.spawn` only when the work is long-lived and bidirectional.

```dart
// BAD
final photos = parsePhotos(response.body);

// GOOD
final photos = await Isolate.run(() => parsePhotos(response.body));
```

---

### Route every user-facing string through localization

A literal in a widget, a validator, or a semantics label cannot be translated and cannot be tested per locale.

```dart
// BAD
return Semantics(label: 'Delete item', child: const Icon(Icons.delete));

// GOOD
return Semantics(label: AppLocalizations.of(context).deleteItem, child: const Icon(Icons.delete));
```

---

### Related skills

- `coding-standards` for the cross-language engineering floor these patterns sit on.
- `code-formatter` for reading flow inside function bodies in Dart, Java and Python, and no other language.
- `tdd-workflow` for the red, green, refactor discipline behind [references/testing.md](testing.md).
- `web-accessibility` for WCAG conformance when a Flutter web build sits inside a wider site.
- `code-reviewer` for reviewing a Dart diff against all of the above.
- `build-dependency-management` for pinning and admitting the packages named in these references.
