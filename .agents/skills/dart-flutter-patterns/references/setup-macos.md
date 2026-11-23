# Environment Setup on macOS

Contents:

- [Install the toolchain](#install-the-toolchain)
- [Checklist](#checklist)

Installing a Flutter toolchain on a Mac for the iOS and macOS targets. Pinning the SDK, the `flutter doctor` loop and the CI gate are the same on every platform and are in [environment-setup.md](environment-setup.md).

---

### Install the toolchain

macOS is the only platform that can build for iOS, and it needs the Apple toolchains for both iOS and macOS
targets.

Install the current Xcode from the Mac App Store or the Apple Developer portal, then point the command-line tools
at it and run its first-launch setup:

```bash
sudo sh -c 'xcode-select -s /Applications/Xcode.app/Contents/Developer && xcodebuild -runFirstLaunch'
```

If Xcode lives somewhere other than `/Applications`, substitute the real path.

Accept the developer licence:

```bash
sudo xcodebuild -license
```

Install CocoaPods, which resolves the native dependencies of most Flutter plugins:

```bash
sudo gem install cocoapods
```

If it is already installed, update it instead:

```bash
sudo gem update cocoapods
```

Validate, and read the Xcode section of the output:

```bash
flutter doctor -v
```

At least one entry must show `macos` as the platform:

```bash
flutter devices
```

Troubleshooting:

- Missing command-line tools. Re-run `xcode-select` under `sudo`, pointing at the correct `.app` directory.
- CocoaPods installed but not detected. The Ruby gem binary directory is not on `PATH`. Add it and open a new
  shell.
- No `macos` device listed. Enable the desktop target:

```bash
flutter config --enable-macos-desktop
```

---

### Checklist

- [ ] macOS hosts have Xcode selected, its licence accepted, and CocoaPods on `PATH`.
