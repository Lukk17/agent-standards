# Dart and Flutter Checklist

Run it before calling a Dart or Flutter change done. The rules behind each item are in [SKILL.md](../SKILL.md), and each topic reference ends with its own checklist.

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
