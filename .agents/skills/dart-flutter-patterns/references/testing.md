# Testing Flutter Applications

Unit, widget, and integration tests, the fakes that make them cheap, and the coverage bar they have to clear.

---

### TDD and FIRST

Write the test first: red (a failing test), green (the minimum code that passes), refactor. Every suite keeps the
FIRST properties.

- Fast. Tests run in milliseconds so they get run constantly. Fake disk, network, and timers.
- Independent. No test depends on another's state or on ordering. Set up and tear down per test.
- Repeatable. Same result on any machine, with no reliance on wall-clock time, locale, or the network.
- Self-validating. Each test asserts a concrete expected value and passes or fails on its own.
- Timely. Written alongside or before the code it covers, not weeks later.

Every unit gets three path classes, not just the first:

- Happy path. Valid input produces the expected output.
- Error path. Invalid input, thrown exceptions, and failed dependencies are handled and asserted.
- Edge path. Boundaries and extremes: empty list, zero, one element, maximum size, null where allowed.

Target around 90% line coverage of real logic:

```bash
flutter test --coverage
```

That writes `coverage/lcov.info`. Never weaken or delete an assertion to make a test green. Fix the code or the
setup.

---

### The three test kinds

Unit tests verify one function, method, or class. Fake every external dependency. No disk I/O, no rendering, no
input from outside the process. Run them with `test` or `flutter_test`.

Widget tests verify that one widget looks and behaves correctly. `WidgetTester` provides the lifecycle, `Finder`
locates widgets, and `Matcher` asserts on them. No full app boot.

Integration tests verify that the pieces work together and capture performance on real hardware. Add the
`integration_test` package, run on a device, emulator, or Firebase Test Lab, and spend the budget on routing,
dependency injection, and the critical user journeys.

---

### What to test where

- View models and cubits. Unit tests, with fake repositories injected. No Flutter widgets involved.
- Repositories and services. Unit tests, with the HTTP client or database faked underneath.
- Views. Widget tests, with a fake or seeded view model passed in.
- Whole journeys. One integration test per critical flow.

Prefer a hand-written `Fake` over a mocking library for repositories and services. A fake has well-defined inputs
and outputs, reads like production code, and does not break when you rename a method. When mocking is genuinely
the right tool, use `mocktail`, not `mockito`.

---

### Unit tests

```dart
test('GetUserUseCase returns null for a missing user', () async {
  final repo = FakeUserRepository();
  final useCase = GetUserUseCase(repo);

  final result = await useCase('missing-id');

  expect(result, isNull);
});

test('GetActiveUsersUseCase returns an empty list when none are active', () async {
  final repo = FakeUserRepository()..seed([inactiveUser]);
  final useCase = GetActiveUsersUseCase(repo);

  final result = await useCase();

  expect(result, isEmpty);
});
```

```dart
blocTest<AuthCubit, AuthState>(
  'emits loading then error on a failed login',
  build: () => AuthCubit(FakeAuthService(throwsOn: 'login')),
  act: (cubit) => cubit.login('user@test.com', 'wrong'),
  expect: () => [isA<AuthLoading>(), isA<AuthFailed>()],
);
```

For Riverpod, drive a `ProviderContainer` with overrides and always register the teardown:

```dart
final container = ProviderContainer(overrides: [
  userRepositoryProvider.overrideWithValue(FakeUserRepository()),
]);
addTearDown(container.dispose);
```

---

### Widget tests

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

```dart
testWidgets('HomeScreen renders the seeded booking', (tester) async {
  final viewModel = HomeViewModel(
    bookingRepository: FakeBookingRepository()..createBooking(kBooking),
    userRepository: FakeUserRepository(),
  );

  await tester.pumpWidget(MaterialApp(home: HomeScreen(viewModel: viewModel)));

  expect(find.byType(ListView), findsOneWidget);
  expect(find.text(kBooking.title), findsOneWidget);
});
```

Pumping rules worth knowing:

- `pump()` advances one frame. `pump(duration)` advances the clock by that amount.
- `pumpAndSettle()` runs frames until none are scheduled. It hangs forever on a repeating animation, so use
  `pump(duration)` there instead. See [animation.md](animation.md).
- A widget that reads `AppLocalizations` needs `localizationsDelegates` and `supportedLocales` on the test
  `MaterialApp`, or it throws.
- Prefer `find.byKey` and `find.text` over `find.byType` for anything the test is actually asserting on. Type
  finders break the moment someone wraps the widget.

---

### Accessibility assertions

Widget tests can assert the guidelines directly, which is how tap-target and contrast regressions get caught in
CI rather than in a manual pass.

```dart
testWidgets('meets tap target and contrast guidelines', (tester) async {
  final handle = tester.ensureSemantics();
  await tester.pumpWidget(const MaterialApp(home: SettingsPage()));

  await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
  await expectLater(tester, meetsGuideline(textContrastGuideline));

  handle.dispose();
});
```

---

### Integration tests

```dart
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('tapping the FAB increments the counter', (tester) async {
    await tester.pumpWidget(const MyApp());
    expect(find.text('0'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('increment')));
    await tester.pumpAndSettle();

    expect(find.text('1'), findsOneWidget);
  });
}
```

Mobile, with a device or emulator attached:

```bash
flutter test integration_test/app_test.dart
```

Web, with ChromeDriver already listening on port 4444:

```bash
flutter drive --driver=test_driver/integration_test.dart --target=integration_test/app_test.dart -d chrome
```

Linux CI, which has no display of its own:

```bash
xvfb-run flutter test integration_test/app_test.dart -d linux
```

For Firebase Test Lab, build the app APK and the Android test APK, then upload both.

---

### Plugin testing

A plugin has to be tested on both sides of the channel.

- Dart unit and widget tests for the Dart-facing API, with the platform channel mocked.
- Native unit tests for isolated platform logic: JUnit in `android/src/test/`, XCTest in
  `example/ios/RunnerTests/` and `example/macos/RunnerTests/`, GoogleTest in `linux/test/` and `windows/test/`.
- Espresso or XCUITest when the plugin needs native UI interaction.
- At least one integration test per platform channel call, to prove the Dart and native halves actually agree.
- When a flow cannot be reached from an integration test, for example one requiring a faked device state,
  synthesize the call at the native method channel entry point and test the Dart public API separately.

---

### Checklist

- [ ] The test was written before or alongside the code, and it failed first.
- [ ] Happy, error, and edge paths are covered for every unit.
- [ ] Fakes are preferred over mocks, and any mocking uses `mocktail`.
- [ ] No test depends on another's state, on ordering, on the clock, or on the network.
- [ ] Widget tests carry the localization delegates when the widget reads localized strings.
- [ ] `pumpAndSettle` is never called on an animation that does not settle.
- [ ] Riverpod containers register `addTearDown(container.dispose)`.
- [ ] Accessibility guidelines are asserted in a widget test, not only checked by hand.
- [ ] Every platform channel call has at least one integration test.
- [ ] `flutter test --coverage` reports around 90% of real logic and no assertion was weakened to get there.
