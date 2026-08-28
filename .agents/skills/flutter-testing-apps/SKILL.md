---
name: flutter-testing-apps
description: Implements unit, widget, and integration tests for a Flutter app. Use when ensuring code quality and preventing regressions through automated testing.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Thu, 12 Mar 2026 22:22:10 GMT

---
# Testing Flutter Applications

---

### Contents
- [Core Testing Strategies](#core-testing-strategies)
- [Architectural Testing Guidelines](#architectural-testing-guidelines)
- [Plugin Testing Guidelines](#plugin-testing-guidelines)
- [Workflows](#workflows)
- [Examples](#examples)

---

### TDD and FIRST

Write tests test-first: red (failing test), green (minimum code to pass), refactor. Every suite must keep the FIRST
properties:

- Fast: Tests run in milliseconds so they are run constantly. Mock disk, network, and timers.
- Independent: No test depends on another's state or ordering. Set up and tear down per test.
- Repeatable: Same result every run, on any machine, with no reliance on wall-clock time, locale, or network.
- Self-validating: Each test asserts a concrete expected value and passes or fails on its own, with no manual
  inspection.
- Timely: Write the test alongside (or before) the code it covers, not weeks later.

Every suite must cover three path classes, not just the happy path:

- Happy path: The expected, valid input produces the expected output.
- Error path: Invalid input, thrown exceptions, and failed dependencies are handled and asserted.
- Edge path: Boundaries and empty or extreme inputs (empty list, zero, single element, maximum size, null where
  allowed).

Target around 90% line coverage of real logic. Measure it with `flutter test --coverage`, which writes
`coverage/lcov.info`. Never weaken or delete an assertion to make a test green; fix the code or the test setup instead.

---

### Core Testing Strategies

Balance your testing suite across three main categories to optimize for confidence, maintenance cost, dependencies, and
execution speed.

#### Unit Tests
Use unit tests to verify the correctness of a single function, method, or class under various conditions.
- Mock all external dependencies.
- Do not involve disk I/O, screen rendering, or user actions from outside the test process.
- Execute using the `test` or `flutter_test` package.

#### Widget Tests
Use widget tests (component tests) to ensure a single widget's UI looks and interacts as expected.
- Provide the appropriate widget lifecycle context using `WidgetTester`.
- Use `Finder` classes to locate widgets and `Matcher` constants to verify their existence and state.
- Test views and UI interactions without spinning up the full application.

#### Integration Tests
Use integration tests (end-to-end or GUI testing) to validate how individual pieces of an app work together and to
capture performance metrics on real devices.
- Add the `integration_test` package as a dependency.
- Run on physical devices, OS emulators, or Firebase Test Lab.
- Prioritize integration tests for routing, dependency injection, and critical user flows.

---

### Architectural Testing Guidelines

Design your application for observability and testability. Ensure all components can be tested both in isolation and
together.

- ViewModels: Write unit tests for every ViewModel class. Test the UI logic without relying on Flutter libraries or
  testing frameworks.
- Repositories & Services: Write unit tests for every service and repository. Mock the underlying data sources (e.g.,
  HTTP clients, local databases).
- Views: Write widget tests for all views. Pass faked or mocked ViewModels and Repositories into the widget tree to
  isolate the UI.
- Fakes over Mocks: Prefer creating `Fake` implementations of your repositories (e.g., `FakeUserRepository`) over using
  mocking libraries when testing ViewModels and Views to ensure well-defined inputs and outputs.

---

### Plugin Testing Guidelines

When testing plugins, combine Dart tests with native platform tests to ensure full coverage across the method channel.

- Dart Tests: Use Dart unit and widget tests for the Dart-facing API. Mock the platform channel to validate Dart logic.
- Native Unit Tests: Implement native unit tests for isolated platform logic.
  - Android: Configure JUnit tests in `android/src/test/`.
  - iOS/macOS: Configure XCTest tests in `example/ios/RunnerTests/` and `example/macos/RunnerTests/`.
  - Linux/Windows: Configure GoogleTest tests in `linux/test/` and `windows/test/`.
- Native UI Tests: Use Espresso (Android) or XCUITest (iOS) if the plugin requires native UI interactions.
- Integration Tests: Write at least one integration test for each platform channel call to verify Dart-to-Native
  communication.
- End-to-End Fallback: If integration tests cannot cover a flow (e.g., mocking device state), synthesize calls to the
  method channel entry point using native unit tests, and test the Dart public API using Dart unit tests.

---

### Workflows

#### Workflow: Implementing a Component Test Suite
Copy and track this checklist when implementing tests for a new architectural feature.

- [ ] Task Progress
  - [ ] Create `Fake` implementations for any new Repositories or Services.
  - [ ] Write Unit Tests for the Repository (mocking the API/Database).
  - [ ] Write Unit Tests for the ViewModel (injecting the Fake Repositories).
  - [ ] Write Widget Tests for the View (injecting the ViewModel and Fake Repositories).
  - [ ] Write an Integration Test for the critical path involving this feature.
  - [ ] Cover happy, error, and edge paths for each unit under test.
  - [ ] Run `flutter test --coverage` and confirm around 90% line coverage of real logic before declaring done.
  - [ ] Run validator -> review coverage -> fix missing edge cases (never weaken an assertion to pass).

#### Workflow: Running Integration Tests
Follow conditional logic based on the target platform when executing integration tests.

1. If testing on Mobile (Local):
   - Connect the Android/iOS device or emulator.
   - Run: `flutter test integration_test/app_test.dart`
2. If testing on Web:
   - Install and launch ChromeDriver: `chromedriver --port=4444`
   - Run: `flutter drive --driver=test_driver/integration_test.dart --target=integration_test/app_test.dart -d chrome`
3. If testing on Linux (CI System):
   - Invoke an X server using `xvfb-run` to provide a display environment.
   - Run: `xvfb-run flutter test integration_test/app_test.dart -d linux`
4. If testing via Firebase Test Lab:
   - Build the Android test APKs: `flutter build apk --debug` and `./gradlew app:assembleAndroidTest`
   - Upload the App APK and Test APK to the Firebase Console.

---

### Examples

#### Example: ViewModel Unit Test
Demonstrates testing a ViewModel using a Fake Repository.

```dart
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('HomeViewModel tests', () {
    test('Load bookings successfully', () {
      // the repository is seeded with exactly one known booking
      final viewModel = HomeViewModel(
        bookingRepository: FakeBookingRepository()..createBooking(kBooking),
        userRepository: FakeUserRepository(),
      );

      // read the exposed bookings
      final bookings = viewModel.bookings;

      // the count and the booking content match the seeded data
      expect(bookings, hasLength(1));
      expect(bookings.single.id, kBooking.id);
      expect(bookings.single.title, kBooking.title);
    });
  });
}
```

#### Example: View Widget Test
Demonstrates testing a View by pumping a localized widget tree with fake dependencies.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('HomeScreen tests', () {
    late HomeViewModel viewModel;
    late FakeBookingRepository bookingRepository;

    setUp(() {
      bookingRepository = FakeBookingRepository()..createBooking(kBooking);
      viewModel = HomeViewModel(
        bookingRepository: bookingRepository,
        userRepository: FakeUserRepository(),
      );
    });

    testWidgets('renders bookings list', (WidgetTester tester) async {
      // a HomeScreen wired to a view model with one seeded booking is pumped, and the first frame builds
      await tester.pumpWidget(
        MaterialApp(
          home: HomeScreen(viewModel: viewModel),
        ),
      );

      // the list renders and the seeded booking is visible
      expect(find.byType(ListView), findsOneWidget);
      expect(find.text('Booking 1'), findsOneWidget);
    });
  });
}
```

#### Example: Integration Test
Demonstrates a full end-to-end test using the `integration_test` package.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:my_app/main.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('end-to-end test', () {
    testWidgets('tap on the floating action button, verify counter', (tester) async {
      // the app is loaded at its initial counter state of 0
      await tester.pumpWidget(const MyApp());
      expect(find.text('0'), findsOneWidget);

      // the increment button is tapped and the frame settles
      final fab = find.byKey(const ValueKey('increment'));
      await tester.tap(fab);
      await tester.pumpAndSettle();

      // the counter advances to exactly 1
      expect(find.text('1'), findsOneWidget);
    });
  });
}
```
