# Environment Setup on Linux

Contents:

- [Install the toolchain](#install-the-toolchain)
- [Package for the Snap Store](#package-for-the-snap-store)
- [Checklist](#checklist)

Installing a Flutter toolchain on Linux and packaging a Linux desktop build. Pinning the SDK, the `flutter doctor` loop and the CI gate are the same on every platform and are in [environment-setup.md](environment-setup.md).

---

### Install the toolchain

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

---

### Package for the Snap Store

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

### Checklist

- [ ] Linux hosts have the GTK, clang, cmake, and ninja packages installed.
