---
name: flutter-architecting-apps
description: Architects a Flutter application using the recommended layered approach (UI, Logic, Data). Use when structuring a new project or refactoring for scalability.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Thu, 12 Mar 2026 22:13:42 GMT

---
# Architecting Flutter Applications

## Contents
- [Core Architectural Principles](#core-architectural-principles)
- [Structuring the Layers](#structuring-the-layers)
- [Implementing the Data Layer](#implementing-the-data-layer)
- [Feature Implementation Workflow](#feature-implementation-workflow)
- [Examples](#examples)

## Core Architectural Principles

Design Flutter applications to scale by strictly adhering to the following principles:

*   **Enforce Separation of Concerns:** Decouple UI rendering from business logic and data fetching. Organize the codebase into distinct layers (UI, Logic, Data) and further separate by feature within those layers.
*   **Maintain a Single Source of Truth (SSOT):** Centralize application state and data in the Data layer. Ensure the SSOT is the only component authorized to mutate its respective data.
*   **Implement Unidirectional Data Flow (UDF):** Flow state downwards from the Data layer to the UI layer. Flow events upwards from the UI layer to the Data layer.
*   **Treat UI as a Function of State:** Drive the UI entirely via immutable state objects. Rebuild widgets reactively when the underlying state changes.

> **Rule:** Do not use `ChangeNotifier` for application state. Use Riverpod `AsyncNotifier`/`Notifier` providers or BLoC `Cubit` classes.

> **Rule:** Never model async state with nullable optional fields. Use `AsyncValue<T>` (Riverpod) or sealed state classes (BLoC):

```dart
// BLoC sealed state
sealed class UserState {}
class UserInitial extends UserState {}
class UserLoading extends UserState {}
class UserLoaded extends UserState { final User user; UserLoaded(this.user); }
class UserError extends UserState { final String message; UserError(this.message); }

// Riverpod
final userProvider = AsyncNotifierProvider<UserNotifier, User>(UserNotifier.new);
class UserNotifier extends AsyncNotifier<User> {
  @override
  Future<User> build() => ref.watch(userRepositoryProvider).fetchUser();
}
// In widget: ref.watch(userProvider) returns AsyncValue<User>
// Use .when(data: ..., loading: ..., error: ...)
```

## Structuring the Layers

Separate the application into 2 to 3 distinct layers depending on complexity. Restrict communication so that a layer only interacts with the layer directly adjacent to it.

### 1. UI Layer (Presentation)
*   **Views (Widgets):** Build reusable, lean widgets. Strip all business and data-fetching logic from the widget tree. Restrict widget logic to UI-specific concerns (e.g., animations, routing, layout constraints).
*   **ViewModels / Providers / Cubits:** Manage the UI state. Consume domain models from the Data/Logic layers and transform them into presentation-friendly formats. Expose state to the Views and handle user interaction events. Implement as **Riverpod `AsyncNotifier`/`Notifier` providers** or **BLoC `Cubit` classes** — not `ChangeNotifier`.

### 2. Logic Layer (Domain) - *Conditional*
*   **If the application requires complex client-side business logic:** Implement a Logic layer containing Use Cases or Interactors. Use this layer to orchestrate interactions between multiple repositories before passing data to the UI layer.
*   **If the application is a standard CRUD app:** Omit this layer. Allow ViewModels/providers to interact directly with Repositories.

### 3. Data Layer (Model)
*   **Responsibilities:** Act as the SSOT for all application data. Handle business data, external API consumption, event processing, and data synchronization.
*   **Components:** Divide the Data layer strictly into **Repositories** and **Services**.

## Implementing the Data Layer

### Services
*   **Role:** Wrap external APIs (HTTP servers, local databases, platform plugins).
*   **Implementation:** Write Services as stateless Dart classes. Do not store application state here.
*   **Mapping:** Create exactly one Service class per external data source.

### Repositories
*   **Role:** Act as the SSOT for domain data.
*   **Implementation:** Consume raw data from Services. Handle caching, offline synchronization, and retry logic.
*   **Transformation:** Transform raw API/Service data into clean Domain Models formatted for consumption by ViewModels/providers.

## Feature Implementation Workflow

Follow this sequential workflow when adding a new feature to the application.

**Task Progress:**
- [ ] **Step 1: Define Domain Models.** Create immutable Dart classes representing the core data structures required by the feature.
- [ ] **Step 2: Implement Services.** Create stateless Service classes to handle raw data fetching (e.g., HTTP GET/POST).
- [ ] **Step 3: Implement Repositories.** Create Repository classes that consume the Services, handle caching, and return Domain Models.
- [ ] **Step 4: Implement ViewModels/Providers.** Create Riverpod `AsyncNotifier`/`Notifier` providers or BLoC `Cubit` classes that consume the Repositories. Expose immutable state and define methods (commands) for user actions. Do not use `ChangeNotifier`.
- [ ] **Step 5: Implement Views.** Create Flutter Widgets that bind to the provider/Cubit state and trigger methods on user interaction.
- [ ] **Step 6: Run Validator.** Execute unit tests for Services, Repositories, and ViewModels/providers. Execute widget tests for Views.
    *   *Feedback Loop:* Review test failures -> Fix logic/mocking errors -> Re-run tests until passing.

## Examples

### Data Layer: Service and Repository

```dart
// 1. Service (Stateless API Wrapper)
class UserApiService {
  final HttpClient _client;

  UserApiService(this._client);

  Future<Map<String, dynamic>> fetchUserRaw(String userId) async {
    final response = await _client.get('/users/$userId');
    return response.data;
  }
}

// 2. Domain Model (Immutable — use freezed in production)
class User {
  final String id;
  final String name;

  const User({required this.id, required this.name});
}

// 3. Repository (SSOT & Data Transformer)
class UserRepository {
  final UserApiService _apiService;
  User? _cachedUser;

  UserRepository(this._apiService);

  Future<User> getUser(String userId) async {
    if (_cachedUser != null && _cachedUser!.id == userId) {
      return _cachedUser!;
    }

    final rawData = await _apiService.fetchUserRaw(userId);
    final user = User(id: rawData['id'], name: rawData['name']);

    _cachedUser = user; // Cache data
    return user;
  }
}
```

### UI Layer: Riverpod AsyncNotifier and View

```dart
// 4a. Riverpod provider (preferred)
// State is AsyncValue<User> — no nullable fields for loading/error
final userProvider = AsyncNotifierProvider<UserNotifier, User>(UserNotifier.new);

class UserNotifier extends AsyncNotifier<User> {
  @override
  Future<User> build() =>
      ref.watch(userRepositoryProvider).getUser('current');

  Future<void> reload(String userId) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(userRepositoryProvider).getUser(userId),
    );
  }
}

// 5a. View consuming Riverpod provider
class UserProfileView extends ConsumerWidget {
  const UserProfileView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userAsync = ref.watch(userProvider);
    return userAsync.when(
      loading: () => const CircularProgressIndicator(),
      error: (err, _) => Text('Error: $err'),
      data: (user) => Text('Hello, ${user.name}'),
    );
  }
}
```

### UI Layer: BLoC Cubit and View

```dart
// 4b. BLoC Cubit (use for complex event-driven features)
// State is a sealed class — no nullable fields for loading/error
sealed class UserState {}
class UserInitial extends UserState {}
class UserLoading extends UserState {}
class UserLoaded extends UserState {
  final User user;
  UserLoaded(this.user);
}
class UserError extends UserState {
  final String message;
  UserError(this.message);
}

class UserCubit extends Cubit<UserState> {
  UserCubit(this._repository) : super(UserInitial());
  final UserRepository _repository;

  Future<void> loadUser(String userId) async {
    emit(UserLoading());
    try {
      final user = await _repository.getUser(userId);
      emit(UserLoaded(user));
    } catch (e) {
      emit(UserError(e.toString()));
    }
  }
}

// 5b. View consuming BLoC Cubit
class UserProfileView extends StatelessWidget {
  const UserProfileView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<UserCubit, UserState>(
      builder: (context, state) => switch (state) {
        UserInitial() => const SizedBox.shrink(),
        UserLoading() => const CircularProgressIndicator(),
        UserLoaded(:final user) => Text('Hello, ${user.name}'),
        UserError(:final message) => Text('Error: $message'),
      },
    );
  }
}
```
