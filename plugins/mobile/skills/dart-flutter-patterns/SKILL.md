---
name: dart-flutter-patterns
description: "Dart 3 and Flutter 3 patterns across architecture, layout, routing, forms, networking, persistence, concurrency, animation, accessibility, localization, native interop, app size and testing. Use when the user says \"build a Flutter screen\", \"why does my Column overflow\" or \"write a widget test for this form\". Not for language-neutral SOLID, naming and error-handling rules, use `coding-standards`."
---

# Dart and Flutter Patterns

Production patterns for Dart 3 and Flutter, from project layout down to the individual widget, with a reference file per topic. The hub carries the rules that apply everywhere, and each reference carries the depth for one area.

Written for Dart 3 and Flutter 3. Confirm the installed SDK with `flutter --version`.

---

### When to activate

- Writing or reviewing any Dart or Flutter code, including plain Dart packages with no widgets.
- The user says "build a Flutter screen", "why does my Column overflow", "set up GoRouter with an auth guard", "parse this JSON without jank", or "write a widget test for this form".
- Structuring a new Flutter project, or refactoring one whose layers have blurred.
- Debugging a layout overflow, a jank frame, a rebuild storm, or a `setState() called after dispose()` crash.
- Wiring navigation, deep links, forms, HTTP clients, local databases, or platform channels.
- Adding tests, localization, accessibility semantics, or a size budget to an existing app.
- Setting up a Linux, macOS, or Windows machine to build Flutter.

---

### When not to activate

- Language-neutral design rules such as SOLID, DRY, naming, and error-handling shape. Use `coding-standards`.
- Blank lines, control-flow exits and chain breaking inside a Dart function body. Use `code-formatter`, which covers Dart, Java and Python only. Any other language follows its language skill or its default formatter.
- The red, green, refactor loop itself rather than Flutter test mechanics. Use `tdd-workflow`.
- WCAG conformance for a web page or a non-Flutter front end. Use `web-accessibility`.
- Reviewing a diff or a pull request for defects. Use `code-reviewer`.
- Measuring and fixing backend or query latency behind the app. Use `performance-optimization`.

---

### Rules

1. Rely on the defaults: Material 3 with no `useMaterial3`, Impeller for profiling, `package:web` and `dart:js_interop` for Wasm, and localizations from `package:<your_app>/l10n/`, never `flutter_gen`.
2. Turn on the strict analyzer modes in `analysis_options.yaml`.
3. Never force-unwrap with `!`. Use `late` only for a field set in `initState` before any read or a `late final` with an inline initializer.
4. Model async state as a sealed type with an exhaustive `switch`, or Riverpod's `AsyncValue`, and generate immutability with `freezed`.
5. Guard every `context` use after an `await` with `mounted`, or capture what you need before the await.
6. Extract subtrees into widget classes, never `_build...()` methods, push `const` as far up as it goes, and keep the widget that watches changing state small.
7. Match the project's state management, Riverpod, BLoC or `ChangeNotifier`, never two in one feature and never a mutable collection exposed.
8. Match the project's HTTP client from `pubspec.yaml`. Build URLs with `Uri.https` or dio's `baseUrl` and `queryParameters`, check the status and throw, and keep tokens out of source.
9. Bound a scrollable inside a flex box with `Expanded` rather than a hardcoded height.
10. Move a synchronous block that measurably exceeds a frame to `Isolate.run`, and use `Isolate.spawn` only for long-lived bidirectional work.
11. Route every user-facing string, validators and semantics labels included, through localization, and dispose every controller and subscription.

---

### Doc comments

Doc comments follow the Doc Comments rules in `coding-standards`. Dart delta: write them as `///` and refer to a parameter or a type in square brackets, such as `[holdFor]` or `[InsufficientStockException]`, so `dart doc` links it. Dart has no tags and no checked exceptions, so every exception a caller can act on gets a plain `Throws [SomeException] when ...` line, which is the contract slot. The `public_member_api_docs` lint wanting a comment on every public member is not a reason to write a sentence that adds nothing.

---

### Which reference to open for which task

| Task | Reference |
| --- | --- |
| A hub rule needs its example, its reasoning, the baseline detail, or the related skills | [references/core-rules.md](references/core-rules.md) |
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

### Checklist

- [ ] No `!` force-unwrap, and no `late` that is neither initialised in `initState` nor a `late final` initializer.
- [ ] Async state is a sealed type or `AsyncValue`, never a bag of nullable fields.
- [ ] Every `context` use after an `await` is guarded by `mounted` or a pre-await capture.
- [ ] Subtrees are widget classes, not `_build...()` methods, and `const` reaches as far up as it can.
- [ ] One state-management library per feature, matching what the project already uses.
- [ ] One HTTP client, matching `pubspec.yaml`, with URLs built through `Uri.https` or dio's `baseUrl`.
- [ ] No user-facing literal anywhere, including validators and semantics labels.
- [ ] Every disposable (`AnimationController`, `TextEditingController`, `StreamSubscription`) is disposed.
- [ ] Doc comments follow `coding-standards`, use `///` with `[name]` references, and name every exception under a `Throws` line.
- [ ] `flutter analyze` is clean and `flutter test --coverage` passes at around 90% of real logic.
