# Flutter / Dart Standards

Applies to all Flutter applications. Universal rules in `universal-coding-standards.md` apply in addition to these.

---

## Architecture

Use **Clean Architecture** with three layers:

| Layer | Responsibility |
|---|---|
| Presentation | Widgets, BLoC/Cubit, Riverpod providers |
| Domain | Entities, use cases, repository interfaces (pure Dart, no Flutter imports) |
| Data | Repository implementations, data sources, API clients, local storage |

- The domain layer must have zero dependencies on Flutter or any external package.
- Data layer depends on domain. Presentation depends on domain. Domain depends on nothing.

---

## State Management

Use **Riverpod** (v2, code-generated with `riverpod_annotation`) as the default state management solution:
- Use `@riverpod` annotation for providers.
- Use `AsyncNotifier` for async state, `Notifier` for sync state.
- Use `ref.watch` in widgets, `ref.read` in callbacks only.

Use **BLoC / Cubit** (from `flutter_bloc`) for complex feature-level state that has many events and states:
- Prefer `Cubit` over `BLoC` when there is no need for event transformation or `EventTransformer`.
- Use `BLoC` when events require debouncing, throttling, or sequential processing.
- Emit a sealed class hierarchy of states (`sealed class MyState`).

Do not mix Riverpod and BLoC within the same feature; choose one per feature.

---

## Navigation

Use **GoRouter** for all navigation:
- Define all routes in a single `router.dart` file.
- Use named routes; never use anonymous `MaterialPageRoute` inline.
- Use `ShellRoute` for persistent navigation shells (e.g., bottom nav bar).
- Use `redirect` in GoRouter for authentication guards.

---

## Code Generation

Use `build_runner` with:
- `freezed` for immutable data classes and sealed state hierarchies.
- `json_serializable` for JSON serialization.
- `riverpod_generator` for Riverpod providers.

Run after any model change:
```bash
dart run build_runner build --delete-conflicting-outputs
```

---

## Data Classes

- Use `freezed` for all domain entities and state classes.
- Use `copyWith`, `==`, and `hashCode` from `freezed`; never write them manually.
- Use `@JsonSerializable()` on data-layer models; never write `fromJson`/`toJson` manually.

---

## Dart Language

- Enable `strict-casts`, `strict-inference`, and `strict-raw-types` in `analysis_options.yaml`.
- Never use `dynamic`; prefer `Object?` if the type is truly unknown and document why.
- Use `const` constructors wherever possible.
- Use named parameters for constructors and functions with more than two parameters.
- Use `sealed class` for exhaustive pattern matching on state hierarchies.
- Prefer `switch` expressions over `if-else` chains for exhaustive matching.

---

## Naming (Dart conventions)

- Files: `snake_case.dart`.
- Classes, enums, extensions: `PascalCase`.
- Variables, functions, parameters: `camelCase`.
- Constants: `lowerCamelCase` (Dart convention — not `UPPER_SNAKE_CASE`).
- Boolean variables must start with `is`, `has`, or `can`.

---

## Widgets

- Keep `build()` methods concise; extract complex subtrees to private widget methods or dedicated widget classes.
- Prefer `const` widgets at every leaf node.
- Do not perform business logic inside `build()`; delegate to providers/BLoC.
- Use `StatelessWidget` by default; only use `StatefulWidget` when local ephemeral UI state is truly needed (e.g., animation controllers, `TextEditingController`).
- Prefer `ConsumerWidget` (Riverpod) or `BlocBuilder` (BLoC) over `StatefulWidget` for state-driven UI.

---

## Error Handling

- Use a global `FlutterError.onError` handler for uncaught Flutter errors.
- Use `PlatformDispatcher.instance.onError` for uncaught Dart async errors.
- Represent async states with `AsyncValue` (Riverpod) or sealed state classes (BLoC) — never use nullable fields to indicate loading.

---

## Dependency Injection

- Use Riverpod providers as the DI container; do not use `get_it` alongside Riverpod.
- If BLoC is used without Riverpod, use `get_it` + `injectable` for DI.

---

## Localization

- Use Flutter's built-in `flutter_localizations` + ARB files (`l10n/`).
- Never hardcode user-visible strings; all strings must go through `AppLocalizations`.

---

## Testing

These rules extend `testing-standards.md`:

- Use `flutter_test` for widget tests.
- Use `mocktail` (not `mockito`) for mocking in Dart tests.
- Use `bloc_test` package for BLoC/Cubit unit tests.
- Use `ProviderContainer` for testing Riverpod providers in isolation.
- Widget tests must use `pumpWidget` with a `ProviderScope` wrapping when Riverpod is used.

---

## Accessibility

- Wrap every custom interactive widget with a `Semantics` widget that describes its role, label, and state.
- Use `MergeSemantics` to combine related widgets (icon + label) into a single accessibility node.
- Use `ExcludeSemantics` for purely decorative elements (background images, dividers).
- Enforce a minimum touch target size of **48×48 logical pixels** for all tappable elements (`GestureDetector`, `InkWell`).
- Test accessibility with the Flutter Accessibility Scanner and verify no `Semantics` nodes have missing labels.

---

## Performance Profiling

- Use **Flutter DevTools** (Performance view) to identify jank before shipping; maintain 60/120 fps on target devices.
- Wrap expensive subtrees in `RepaintBoundary` to isolate repaints; verify with the "Highlight repaints" overlay.
- Use `const` constructors on every leaf widget where possible; run `flutter analyze` to catch missing `const` annotations.
- Avoid expensive operations in `build()` methods; move computation to providers/BLoC or pre-compute in `initState`.

---

## Environment Configuration (Flavors)

- Define three flavors: `dev`, `staging`, `prod`, each with its own `main_<flavor>.dart` entry point.
- Pass environment-specific configuration via `--dart-define` or a generated `app_config.dart` (never hardcode URLs or keys).
- Use `flutter_flavorizr` or manual flavor configuration in `android/app/build.gradle` and `ios/Runner.xcconfig`.

---

## Platform-Specific Code

- Isolate platform-specific code behind a Dart interface with platform implementations; use `MethodChannel` or **Pigeon** for native communication.
- Always guard platform-specific calls with `Platform.isAndroid` / `Platform.isIOS` / `kIsWeb`.
- Use **Pigeon** for type-safe method channel communication; never write raw method channel boilerplate for new integrations.

---

## Deep Linking

- Configure universal links (iOS) and app links (Android) in `GoRouter` using path parameters.
- Register URL schemes and associated domains in `Info.plist` and `AndroidManifest.xml`.
- Test deep link routing in both cold-start and warm-start scenarios.

---

## CI/CD

- Use **GitHub Actions** (or equivalent) with a matrix build for both Android (APK/AAB) and iOS (IPA).
- Use **Fastlane** for signing and distribution to TestFlight and Google Play Internal Track.
- Enforce `flutter analyze` and `flutter test` as required PR checks before any merge.
- Pin the Flutter SDK version in `.fvmrc` (Flutter Version Management) and commit it to the repo; all team members and CI must use the same version.

---

## App Size Optimisation

- Enable deferred components for large optional features (e.g., heavy onboarding flows) to reduce initial download size.
- Use `flutter build apk --analyze-size` and `flutter build ios --analyze-size` in CI to track size regressions.
- Compress all bundled image assets; use `.webp` format for raster images and `flutter_svg` for vector assets.
