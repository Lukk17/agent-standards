# Environment Setup

Installing and validating a Flutter toolchain on Linux, macOS, and Windows, plus the packaging and CI wiring that
sits on top of it.

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

### Linux

Flutter's Linux desktop target compiles native code through the C and C++ toolchain and renders with GTK, so both
have to be present before `flutter doctor` will pass.

Update the package lists on a Debian or Ubuntu system:

```bash
sudo apt-get update -y
```

Install the core utilities, the build tools, and the GTK libraries in one go:

```bash
sudo apt-get install -y curl git unzip xz-utils zip libglu1-mesa clang cmake ninja-build pkg-config libgtk-3-dev libstdc++-12-dev
```

Install VS Code, Android Studio, or an IntelliJ IDE, then add the official Dart and Flutter extensions so the
language server and the debugger work.

On a Chromebook, turn on Linux support in ChromeOS settings first and update the container with the commands
above before installing anything else.

Confirm the desktop target is available. At least one entry must show `linux` as the platform:

```bash
flutter devices
```

Packaging for the Snap Store. Install the build tools:

```bash
sudo snap install snapcraft --classic
```

```bash
sudo snap install lxd
```

Initialize LXD:

```bash
sudo lxd init
```

Add yourself to the `lxd` group, then log out and back in for it to take effect:

```bash
sudo usermod -a -G lxd "$USER"
```

Build the snap from the project root, which must contain `snap/snapcraft.yaml`:

```bash
snapcraft --use-lxd
```

A baseline `snap/snapcraft.yaml`:

```yaml
name: super-cool-app
version: 0.1.0
summary: Super Cool App
description: Super Cool App that does everything.

confinement: strict
base: core22
grade: stable

slots:
  dbus-super-cool-app:
    interface: dbus
    bus: session
    name: org.bar.super_cool_app

apps:
  super-cool-app:
    command: super_cool_app
    extensions: [gnome]
    plugs:
      - network
    slots:
      - dbus-super-cool-app

parts:
  super-cool-app:
    source: .
    plugin: flutter
    flutter-target: lib/main.dart
```

---

### macOS

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

### Windows

Windows builds the Windows desktop target and Android. Two different Microsoft products are involved and they are
easy to confuse: Visual Studio compiles the native C++ for Windows desktop, VS Code is a code editor and cannot
do that job.

Install the SDK. Chocolatey handles the download, extraction, and `PATH` entry in one step:

```powershell
choco install flutter
```

Without Chocolatey, download the stable SDK zip and extract it to a path your user account owns. Never extract it
under `C:\Program Files`, because the tool writes into its own directory and will fail on permissions:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\flutter_windows_stable.zip" -DestinationPath C:\src
```

Append the SDK `bin` directory to the user `PATH`:

```powershell
[Environment]::SetEnvironmentVariable('Path', "$([Environment]::GetEnvironmentVariable('Path','User'));C:\src\flutter\bin", 'User')
```

Open a new terminal so the change takes effect, then confirm the tool resolves:

```powershell
(Get-Command flutter).Source
```

Install Visual Studio with the C++ workload, which is mandatory for the Windows desktop target:

```powershell
choco install visualstudio2022community --package-parameters "--add Microsoft.VisualStudio.Workload.NativeDesktop --includeRecommended"
```

Install an editor and add the official Flutter and Dart extensions:

```powershell
choco install vscode
```

Validate the whole toolchain:

```powershell
flutter doctor -v
```

Accept the Android SDK licences, which `flutter doctor` will otherwise keep reporting as missing:

```powershell
flutter doctor --android-licenses
```

Confirm the targets, which must list `windows` and any attached Android device:

```powershell
flutter devices
```

Targeting Android from Windows:

- Physical device. Enable Developer Options and USB debugging on the phone, and install the OEM USB driver.
- Emulator. In the AVD manager, set Emulated Performance, Graphics acceleration to a Hardware option, or the
  emulator will run unusably slowly.

Disable any target you do not build for, so `flutter doctor` stops checking its toolchain:

```powershell
flutter config --no-enable-web
```

Packaging a Windows desktop release. Build it:

```powershell
flutter build windows
```

The output lands in `build\windows\x64\runner\Release\`. A distributable archive needs the executable, every
`.dll` beside it, the whole `data` directory, and the Visual C++ redistributables `msvcp140.dll`,
`vcruntime140.dll`, and `vcruntime140_1.dll`.

```powershell
Compress-Archive -Path build\windows\x64\runner\Release\* -DestinationPath dist\my_flutter_app.zip
```

The archive must have this shape:

```text
my_flutter_app.zip
    my_flutter_app.exe
    flutter_windows.dll
    msvcp140.dll
    vcruntime140.dll
    vcruntime140_1.dll
    data/
        app.so
        icudtl.dat
```

Self-signed certificate for MSIX packaging or local testing. Install OpenSSL and put its `bin` directory on
`PATH`, then generate the private key:

```powershell
openssl genrsa -out mykeyname.key 2048
```

Generate the certificate signing request:

```powershell
openssl req -new -key mykeyname.key -out mycsrname.csr
```

Sign it:

```powershell
openssl x509 -in mycsrname.csr -out mycrtname.crt -req -signkey mykeyname.key -days 10000
```

Export the `.pfx`:

```powershell
openssl pkcs12 -export -out CERTIFICATE.pfx -inkey mykeyname.key -in mycrtname.crt
```

Import it into Trusted Root Certification Authorities before installing the packaged app:

```powershell
Import-PfxCertificate -FilePath CERTIFICATE.pfx -CertStoreLocation Cert:\LocalMachine\Root
```

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
- [ ] Linux hosts have the GTK, clang, cmake, and ninja packages installed.
- [ ] macOS hosts have Xcode selected, its licence accepted, and CocoaPods on `PATH`.
- [ ] Windows hosts have Visual Studio with the C++ workload, not just VS Code.
- [ ] Windows distributions include the three Visual C++ redistributable DLLs and the `data` directory.
- [ ] CI pins the same SDK version and gates on `flutter analyze` and `flutter test`.
