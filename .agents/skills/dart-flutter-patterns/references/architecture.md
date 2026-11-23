# Flutter Application Architecture

How to split a Flutter app into layers, pick and wire a state manager, inject dependencies, capture errors
globally, and separate build flavors.

---

### Contents

- [Core principles](#core-principles)
- [The layers](#the-layers)
- [Feature implementation order](#feature-implementation-order)
- [Data layer example](#data-layer-example)
- [State management, all three options](#state-management-all-three-options)
- [Dependency injection](#dependency-injection)
- [Global error handling](#global-error-handling)
- [Analysis options](#analysis-options)
- [Environment flavors](#environment-flavors)
- [Checklist](#checklist)

---

### Core principles

- Separation of concerns. Decouple UI rendering from business logic and data fetching. Organize into UI, Logic,
  and Data layers, then split by feature inside each layer.
- Single source of truth. Application data lives in the Data layer, and only that layer mutates it.
- Unidirectional data flow. State flows down from Data to UI. Events flow up from UI to Data.
- UI as a function of state. Drive widgets from immutable state objects and rebuild reactively.
- Never model async state with nullable optional fields. Use `AsyncValue<T>` or a sealed state class.

---

### The layers

Use two or three layers depending on complexity, and let each layer talk only to the one next to it.

UI layer (presentation). Views are lean widgets with no business or data-fetching logic, restricted to animation,
routing, and layout concerns. View models, providers, or cubits hold UI state, consume domain models, and expose
presentation-ready values plus the commands the view triggers.

Logic layer (domain), conditional. Add use cases or interactors only when client-side business logic is genuinely
complex enough to orchestrate several repositories. For a standard CRUD app, omit this layer and let view models
call repositories directly.

Data layer (model). The single source of truth. Split it into repositories and services.

- Services wrap one external data source each, stateless, no business logic beyond serialization. One service
  class per HTTP API, database, or platform plugin.
- Repositories are the source of truth for one domain entity. They consume services, own caching, offline sync,
  and retry, and transform raw models into clean domain models. Inject services as private members so the UI
  cannot reach past the repository.

---

### Feature implementation order

1. Define immutable domain models for the feature.
2. Implement the stateless services that fetch or store raw data.
3. Implement the repositories that consume those services and return domain models.
4. Implement the view models, providers, or cubits that consume the repositories and expose immutable state.
5. Implement the views that bind to that state and call its commands.
6. Run unit tests for services, repositories, and view models, plus widget tests for views. Fix and re-run until
   green.

---

### Data layer example

```dart
class UserApiService {
  const UserApiService(this._client);
  final HttpClient _client;

  Future<Map<String, dynamic>> fetchUserRaw(String userId) async {
    final response = await _client.get('/users/$userId');
    return response.data;
  }
}

@freezed
class User with _$User {
  const factory User({required String id, required String name}) = _User;
  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
}

class UserRepository {
  UserRepository(this._apiService);
  final UserApiService _apiService;
  User? _cachedUser;

  Future<User> getUser(String userId) async {
    final cached = _cachedUser;
    if (cached != null && cached.id == userId) {
      return cached;
    }

    final raw = await _apiService.fetchUserRaw(userId);
    final user = User(id: raw['id'] as String, name: raw['name'] as String);
    _cachedUser = user;
    return user;
  }
}
```

The cache snapshot is repository-internal and replaced atomically, never exposed mutably. Mutable fields scattered
through the data layer are the shared-mutable-state anti-pattern: keep any cache private and immutable.

---

### State management, all three options

Match the project. Never mix two in one feature. The same user profile screen is worked through once per option, in
[riverpod.md](riverpod.md), [bloc.md](bloc.md) and [provider.md](provider.md).

Which one fits:

| Situation | Pick |
| --- | --- |
| Deep dependency graph, lots of derived state, compile-time-checked injection | Riverpod |
| Event-driven flows, an audit trail of state transitions, a large team wanting one shape | BLoC |
| A small app, or local state for a single screen, with `Provider` already in the tree | `ChangeNotifier` |
| The project already uses one of them | Whatever it already uses |

---

### Dependency injection

- Riverpod providers are the DI container for Riverpod features. Do not add `get_it` beside them.
- BLoC without Riverpod uses `get_it` with `injectable`.
- Never mix Riverpod and BLoC inside one feature.

---

### Global error handling

Install both handlers in `main` before `runApp`, and replace the red error box in release builds.

```dart
void main() {
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    crashlytics.recordFlutterFatalError(details);
  };

  PlatformDispatcher.instance.onError = (error, stack) {
    crashlytics.recordError(error, stack, fatal: true);
    return true;
  };

  ErrorWidget.builder = ProductionErrorWidget.new;
  runApp(const App());
}
```

---

### Analysis options

Put the strict modes in `analysis_options.yaml` on day one. Retrofitting them into a large codebase is far more
work than starting with them.

```yaml
analyzer:
  language:
    strict-casts: true
    strict-inference: true
    strict-raw-types: true
```

---

### Environment flavors

Use three flavors, `dev`, `staging`, and `prod`, with one entry point each: `lib/main_dev.dart`,
`lib/main_staging.dart`, `lib/main_prod.dart`. Pass configuration with `--dart-define` and let
`flutter_flavorizr` generate the platform-specific flavor configuration.

```bash
flutter run --flavor dev -t lib/main_dev.dart --dart-define=FLAVOR=dev
```

---

### Checklist

- [ ] UI, Logic (if present), and Data layers only talk to their immediate neighbour.
- [ ] Exactly one service class per external data source, stateless, no business logic.
- [ ] Repositories own caching, sync, and mapping, and expose only immutable domain models.
- [ ] One state-management library per feature, matching the rest of the project.
- [ ] No `get_it` alongside Riverpod, and no Riverpod alongside BLoC in the same feature.
- [ ] `FlutterError.onError`, `PlatformDispatcher.instance.onError`, and `ErrorWidget.builder` are all set.
- [ ] Strict analyzer modes are on and `flutter analyze` is clean.
