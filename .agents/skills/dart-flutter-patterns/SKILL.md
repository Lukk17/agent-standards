---
name: dart-flutter-patterns
description: 'Dart 3 and Flutter 3 patterns: architecture, layout, routing, HTTP and tests. Use when the user says "build a Flutter screen" or "why does my Column overflow". Not for SOLID or naming, use `coding-standards`.'
metadata:
  version: "1.1.0"
---

# Dart and Flutter Patterns

Production patterns for Dart 3 and Flutter 3, from project layout down to the individual widget, with one reference per topic and per library. Confirm the installed SDK with `flutter --version`.

---

### When not to activate

- Language-neutral design rules such as SOLID, DRY, naming, and error-handling shape, use `coding-standards`.
- Blank lines, control-flow exits and chain breaking inside a Dart function body, use `code-formatter`.
- WCAG conformance for a web page or a non-Flutter front end, use `web-accessibility`.

---

### Rules

1. Rely on the Flutter 3 defaults in the core rules reference, and turn on the strict analyzer modes in `analysis_options.yaml`.
2. Never force-unwrap with `!`. Use `late` only for a field set in `initState` before any read, or a `late final` with an inline initializer.
3. Model async state as a sealed type with an exhaustive `switch`, never a bag of nullable fields.
4. Guard every `context` use after an `await` with `mounted`, or capture what you need before the await.
5. Extract subtrees into widget classes, never `_build...()` methods, and push `const` as far up as it goes.
6. Match the project's state management library, never two in one feature, and never expose a mutable collection.
7. Match the project's HTTP client. Never concatenate a URL, check the status and throw, and keep tokens out of source.
8. Route every user-facing string through localization, validators and semantics labels included.
9. Dispose every controller and subscription.
10. Doc comments follow the Doc Comments rules in `coding-standards`, written as `///` with `[name]` references and a `Throws` line for each exception a caller can act on.

---

### Reference files

| Open this | When |
| --- | --- |
| [core-rules.md](references/core-rules.md) | A rule above needs its example or reasoning. |
| [architecture.md](references/architecture.md) | Layers, a state manager, DI, error capture, flavors. |
| [riverpod.md](references/riverpod.md), [bloc.md](references/bloc.md), [provider.md](references/provider.md) | The project uses that state manager. |
| [layout.md](references/layout.md) | Overflow, flex boxes, responsive layouts. |
| [routing-and-navigation.md](references/routing-and-navigation.md) | `Navigator`, nested flows, deep links. |
| [go-router.md](references/go-router.md) | The project uses GoRouter. |
| [forms.md](references/forms.md) | Forms, validation, submit gating. |
| [http-and-json.md](references/http-and-json.md) | Picking an HTTP client. |
| [http-package.md](references/http-package.md), [dio.md](references/dio.md) | The project uses that client. |
| [json-serializable.md](references/json-serializable.md) | JSON code generation. |
| [databases-and-caching.md](references/databases-and-caching.md) | A store, offline sync, caches. |
| [sqflite.md](references/sqflite.md) | The project uses `sqflite`. |
| [concurrency.md](references/concurrency.md) | `Future`, `Stream`, isolates. |
| [animation.md](references/animation.md) | Animations and transitions. |
| [accessibility.md](references/accessibility.md) | Semantics, tap targets, contrast. |
| [localization.md](references/localization.md) | ARB files, `gen-l10n`, plurals. |
| [native-interop-and-platform-views.md](references/native-interop-and-platform-views.md) | Platform channels, FFI, native views, Wasm. |
| [pigeon.md](references/pigeon.md) | Generating a type-safe channel. |
| [app-size.md](references/app-size.md) | Bundle size, runtime performance. |
| [testing.md](references/testing.md) | Writing tests. |
| [environment-setup.md](references/environment-setup.md) | Pinning the SDK, `flutter doctor`, CI. |
| [setup-linux.md](references/setup-linux.md), [setup-macos.md](references/setup-macos.md), [setup-windows.md](references/setup-windows.md) | Installing on that system. |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job. |
| [checklist.md](references/checklist.md) | Before calling a change done. |
