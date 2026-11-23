# Environment Setup

Pinning and validating a Flutter toolchain on any machine, plus the CI wiring that sits on top of it. The packages, the IDE steps and the packaging for one operating system are in [setup-linux.md](setup-linux.md), [setup-macos.md](setup-macos.md) and [setup-windows.md](setup-windows.md).

---

### Common to every platform

Pin the SDK version rather than following whatever `flutter upgrade` last installed. FVM keeps the version in the
repository so every machine and CI runner builds with the same toolchain.

```bash
dart pub global activate fvm
```

```bash
fvm use 3.44.1
```

Validate any machine with the same two commands. `flutter doctor` reports what is missing, and `flutter devices`
proves the target is actually reachable.

```bash
flutter doctor -v
```

```bash
flutter devices
```

The loop is the same everywhere: run the doctor, read the section that failed, install what it names, run it
again, and repeat until that section passes.

---

### CI

- Run a matrix over the platforms you actually ship: macOS for iOS and macOS, Ubuntu for Android, Linux, and web,
  Windows for the Windows desktop target.
- Pin the SDK with FVM in CI exactly as on a developer machine, so a Flutter release cannot break the build
  overnight.
- Two checks gate every pull request: `flutter analyze` with zero issues, and `flutter test` with everything
  passing.
- Distribute through Fastlane, to TestFlight for iOS and Google Play for Android.

```bash
flutter analyze
```

```bash
flutter test --coverage
```

---

### Checklist

- [ ] The SDK version is pinned with FVM and committed, not left to `flutter upgrade`.
- [ ] `flutter doctor -v` passes every section relevant to the targets being built.
- [ ] `flutter devices` lists the intended target, not just a browser.
- [ ] Targets that are never built are disabled with `flutter config --no-enable-...`.
- [ ] CI pins the same SDK version and gates on `flutter analyze` and `flutter test`.
