---
name: dart-flutter-patterns
description: Dart 3 and Flutter patterns across architecture, layout, routing, forms, networking, persistence, concurrency, animation, accessibility, localization, native interop, app size, and testing. Use when you say "build a Flutter screen", "why does my Column overflow", "set up GoRouter with an auth guard", "parse this JSON without jank", or "write a widget test for this form". Not for language-neutral SOLID, naming, and error-handling rules, use `coding-standards`.
---

# Dart and Flutter Patterns

Production patterns for Dart 3 and Flutter, from project layout down to the individual widget, with a reference
file per topic. The hub carries the rules that apply everywhere, and each reference carries the depth for one area.

---

### Baseline

Assume Dart 3 and current stable Flutter. Verified here with `flutter --version` against Flutter 3.44.1 and Dart
3.12.1. Four defaults follow and change how code is written:

- Material 3 is the default for `ThemeData`. Do not set `useMaterial3`, it is the only behaviour left.
- Impeller is the default renderer on iOS and Android. Profile jank against Impeller, not the retired Skia path.
- `flutter build web --wasm` compiles to WebAssembly, where `dart:html`, `dart:js`, and `package:js` do not work.
  Use `package:web` and `dart:js_interop`.
- The `flutter_gen` synthetic package is removed, so localizations import as
  `package:<your_app>/l10n/app_localizations.dart`, never `package:flutter_gen/...`.

Turn the strict analyzer modes on in `analysis_options.yaml` so the rules below are enforced by tooling rather
than by review. The exact block is in [references/architecture.md](references/architecture.md).

---

### When to activate

- Writing or reviewing any Dart or Flutter code, including plain Dart packages with no widgets.
- Structuring a new Flutter project, or refactoring one whose layers have blurred.
- Debugging a layout overflow, a jank frame, a rebuild storm, or a `setState() called after dispose()` crash.
- Wiring navigation, deep links, forms, HTTP clients, local databases, or platform channels.
- Adding tests, localization, accessibility semantics, or a size budget to an existing app.
- Setting up a Linux, macOS, or Windows machine to build Flutter.

---

### When not to activate

- Language-neutral design rules such as SOLID, DRY, naming, and error-handling shape. Use `coding-standards`.
- Formatting and visual layout of source files in any language. Use `code-formatter`.
- The red, green, refactor loop itself rather than Flutter test mechanics. Use `tdd-workflow`.
- WCAG conformance for a web page or a non-Flutter front end. Use `web-accessibility`.
- Reviewing a diff or a pull request for defects. Use `code-reviewer`.
- Measuring and fixing backend or query latency behind the app. Use `performance-optimization`.

---

### Never force-unwrap

`!` turns a compile-time question into a runtime crash. Dart already has an expression that carries the null case,
and `late` is the same failure mode one step removed. Reserve `late` for a field initialised in `initState` before
any read, such as an `AnimationController`, and use a nullable field everywhere else.

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
if (!mounted) return;
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
examples of all three sit in [references/architecture.md](references/architecture.md).

---

### Match the project's HTTP client

`package:http` and `package:dio` are both correct. `http` is smaller and is what the Flutter team documents. `dio`
adds interceptors, cancellation, and typed errors, which pay off once you need token refresh or retries. Check
`pubspec.yaml` first and use whichever is there.

```dart
// package:http
final response = await client.get(Uri.https('api.example.com', '/users/$id'));
if (response.statusCode != 200) throw HttpException('GET /users/$id failed');
final user = User.fromJson(jsonDecode(response.body) as Map<String, dynamic>);

// package:dio
final response = await dio.get<Map<String, dynamic>>('/users/$id');
final user = User.fromJson(response.data!);
```

Both get the same treatment: build URLs with `Uri.https`, check the status code and throw rather than returning
null, and never leave a token in source.

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

### Doc comments

Default to none. A `///` block is usually a sign that the code failed to explain itself. Extract the unclear block
into a well-named method or widget class, rename the parameters so they carry their own meaning, and tighten the
types. Do that first and most doc comments have nothing left to say. Code that explains itself cannot go stale, a
comment can. When one is genuinely needed, the prose is capped at five lines and is usually one. Every note about
a parameter, the return, or a thrown exception is capped at one line and only appears when it adds something. If
it does not fit on one line, shorten it or drop it. `public_member_api_docs` demanding a comment on every public
member is not a reason to write a sentence that adds nothing. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. Describe a parameter, referenced as `[holdFor]`, only when the name and the type do not already convey it,
   meaning units, nullability, a valid range, or who owns it afterwards. `[orderId] the order identifier` is
   noise, delete it.
3. Describe the return only when it is non-obvious.
4. Describe every exception a caller can act on, always. Dart has no checked exceptions and puts nothing about
   throwing in the signature, so this one is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract cannot be stated in fewer lines, for example
a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you justify in
review. The one-line cap on a note line has no exception: shorten it or delete it.

```dart
/// GOOD. One sentence, then only what the signature cannot say, one line per note.
/// Reserves stock for an order and holds it until the payment window closes.
///
/// [holdFor] is capped at 15 minutes.
/// Throws [InsufficientStockException] when the warehouse cannot cover it.
Future<Reservation> reserve(OrderId orderId, Duration holdFor);

/// BAD. Restates the signature and says nothing about the failure mode.
/// Reserves stock.
///
/// [orderId] the order identifier.
/// [holdFor] the hold duration.
/// Returns a reservation.
Future<Reservation> reserve(OrderId orderId, Duration holdFor);
```

---

### Which reference to open for which task

| Task | Reference |
| --- | --- |
| Layering a project, choosing a state manager, wiring DI, global error capture, flavors | [references/architecture.md](references/architecture.md) |
| Overflow errors, flex boxes, `Stack`, responsive and adaptive layouts | [references/layout.md](references/layout.md) |
| GoRouter, auth redirects, nested navigation, deep links, passing and returning data | [references/routing-and-navigation.md](references/routing-and-navigation.md) |
| `Form` and `TextFormField`, multi-field validation, submit gating, form tests | [references/forms.md](references/forms.md) |
| REST calls with `http` or `dio`, interceptors, JSON code generation, background parsing | [references/http-and-json.md](references/http-and-json.md) |
| SQLite and `drift`, repositories, offline-first sync, image and scroll caching | [references/databases-and-caching.md](references/databases-and-caching.md) |
| `Future`, `Stream`, structured concurrency, `Isolate.run`, long-lived workers | [references/concurrency.md](references/concurrency.md) |
| Implicit and explicit animations, `Hero`, staggering, physics, custom route transitions | [references/animation.md](references/animation.md) |
| Semantics, screen readers, tap targets, contrast, font scaling, web semantics | [references/accessibility.md](references/accessibility.md) |
| ARB files, `gen-l10n`, plurals and selects, locale resolution, iOS bundle setup | [references/localization.md](references/localization.md) |
| Platform channels, Pigeon, FFI, `AndroidView` and `UiKitView`, Wasm and JS interop | [references/native-interop-and-platform-views.md](references/native-interop-and-platform-views.md) |
| Measuring bundle size, tree shaking, obfuscation, asset audits, runtime performance | [references/app-size.md](references/app-size.md) |
| Unit, widget, and integration tests, fakes, coverage, golden and plugin tests | [references/testing.md](references/testing.md) |
| Installing the SDK and toolchain on Linux, macOS, or Windows, plus CI and packaging | [references/environment-setup.md](references/environment-setup.md) |

---

### Related skills

- `coding-standards` for the cross-language engineering floor these patterns sit on.
- `code-formatter` for source layout and reading flow in Dart and every other language here.
- `tdd-workflow` for the red, green, refactor discipline behind [references/testing.md](references/testing.md).
- `web-accessibility` for WCAG conformance when a Flutter web build sits inside a wider site.
- `code-reviewer` for reviewing a Dart diff against all of the above.
- `build-dependency-management` for pinning and admitting the packages named in these references.

---

### Checklist

- [ ] No `!` force-unwrap and no `late` that is not initialised in `initState`.
- [ ] Async state is a sealed type or `AsyncValue`, never a bag of nullable fields.
- [ ] Every `context` use after an `await` is guarded by `mounted` or a pre-await capture.
- [ ] Subtrees are widget classes, not `_build...()` methods, and `const` reaches as far up as it can.
- [ ] One state-management library per feature, matching what the project already uses.
- [ ] One HTTP client, matching `pubspec.yaml`, with URLs built through `Uri.https`.
- [ ] No user-facing literal anywhere, including validators and semantics labels.
- [ ] Every disposable (`AnimationController`, `TextEditingController`, `StreamSubscription`) is disposed.
- [ ] Doc comments follow the four rules above, and none merely restate a signature.
- [ ] `flutter analyze` is clean and `flutter test --coverage` passes at around 90% of real logic.
