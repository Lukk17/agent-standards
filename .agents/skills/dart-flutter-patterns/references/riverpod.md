# Riverpod

State management and dependency injection with Riverpod. Open this when the project already uses Riverpod, or when choosing it. The rule that a feature uses one state manager is in [SKILL.md](../SKILL.md), and the table that picks between the options is in [architecture.md](architecture.md).

---

### When it fits

Riverpod fits when dependencies form a graph and most state derives from other state. It is also the DI
container, so do not add `get_it` beside it.

---

### The short form

```dart
@riverpod
class CartNotifier extends _$CartNotifier {
  @override
  List<CartItem> build() => const [];
  void clear() => state = const [];
}
```

---

### A worked example

The example drives the same user profile screen as the ones in [bloc.md](bloc.md) and [provider.md](provider.md).

Riverpod, when dependencies form a graph and state derives from other state:

```dart
final userProvider = AsyncNotifierProvider<UserNotifier, User>(UserNotifier.new);

class UserNotifier extends AsyncNotifier<User> {
  @override
  Future<User> build() => ref.watch(userRepositoryProvider).getUser('current');

  Future<void> reload(String userId) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => ref.read(userRepositoryProvider).getUser(userId));
  }
}

class UserProfileView extends ConsumerWidget {
  const UserProfileView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ref.watch(userProvider).when(
      loading: () => const CircularProgressIndicator(),
      error: (err, _) => ErrorView(message: '$err'),
      data: (user) => Text(AppLocalizations.of(context).greeting(user.name)),
    );
  }
}
```

---

### Testing

For Riverpod, drive a `ProviderContainer` with overrides and always register the teardown:

```dart
final container = ProviderContainer(overrides: [
  userRepositoryProvider.overrideWithValue(FakeUserRepository()),
]);
addTearDown(container.dispose);
```

A widget test wraps the widget in a `ProviderScope` with the same kind of override:

```dart
testWidgets('CartBadge shows the item count', (tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [cartNotifierProvider.overrideWith(() => FakeCartNotifier(count: 3))],
      child: const MaterialApp(home: CartBadge()),
    ),
  );

  expect(find.text('3'), findsOneWidget);
});
```
