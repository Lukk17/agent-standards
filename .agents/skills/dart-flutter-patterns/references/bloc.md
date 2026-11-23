# BLoC

State management with `flutter_bloc`, cubits included. Open this when the project already uses BLoC, or when choosing it. The rule that a feature uses one state manager is in [SKILL.md](../SKILL.md), and the table that picks between the options is in [architecture.md](architecture.md).

---

### When it fits

BLoC fits event-driven features where the event log helps debugging and the team wants one rigid shape. Pair it
with `get_it` and `injectable` for DI.

---

### The short form

```dart
class AuthCubit extends Cubit<AuthState> {
  AuthCubit(this._service) : super(const AuthLoading());
  final AuthService _service;
  Future<void> login(String email, String password) async =>
      emit(AuthLoaded(await _service.login(email, password)));
}
```

---

### A worked example

The example drives the same user profile screen as the ones in [riverpod.md](riverpod.md) and [provider.md](provider.md).

BLoC, when a feature is event-driven and the emitted state log is worth having:

```dart
sealed class UserState {}
final class UserLoading extends UserState {}
final class UserLoaded extends UserState { UserLoaded(this.user); final User user; }
final class UserFailed extends UserState { UserFailed(this.message); final String message; }

class UserCubit extends Cubit<UserState> {
  UserCubit(this._repository) : super(UserLoading());
  final UserRepository _repository;

  Future<void> loadUser(String userId) async {
    emit(UserLoading());
    try {
      emit(UserLoaded(await _repository.getUser(userId)));
    } on Exception catch (e) {
      emit(UserFailed(e.toString()));
    }
  }
}

class UserProfileView extends StatelessWidget {
  const UserProfileView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<UserCubit, UserState>(
      builder: (context, state) => switch (state) {
        UserLoading() => const CircularProgressIndicator(),
        UserLoaded(:final user) => Text(AppLocalizations.of(context).greeting(user.name)),
        UserFailed(:final message) => ErrorView(message: message),
      },
    );
  }
}
```

---

### Testing

A cubit is tested with `blocTest`, with a fake service injected:

```dart
blocTest<AuthCubit, AuthState>(
  'emits loading then error on a failed login',
  build: () => AuthCubit(FakeAuthService(throwsOn: 'login')),
  act: (cubit) => cubit.login('user@test.com', 'wrong'),
  expect: () => [isA<AuthLoading>(), isA<AuthFailed>()],
);
```
