# Gatekeeper, Quarantine and Privacy Permissions

Read this when an app "cannot be opened", "is damaged", or comes from an unidentified developer, and when a tool is denied access to files, the camera, the screen or other protected data. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

---

### Gatekeeper and the quarantine attribute

A file downloaded by a browser or another quarantine-aware app carries the extended attribute `com.apple.quarantine`. Gatekeeper checks quarantined software for a valid signature and notarization the first time it runs.

Inspect, read-only. From `xattr(1)`, the bare form lists attribute names, and `-p` prints one value:

```bash
xattr -l /Applications/<App>.app
```

```bash
spctl --assess --verbose /Applications/<App>.app
```

```bash
codesign --verify --deep --strict --verbose=2 /Applications/<App>.app
```

`spctl --assess` says whether the system policy would allow it and why. `codesign --verify` says whether the signature is intact. A broken signature on a file from a trusted source usually means a damaged download, so download it again rather than forcing it open.

---

### Opening a blocked app

From Apple's developer news "Updates to runtime protection in macOS Sequoia": "In macOS Sequoia, users will no longer be able to Control-click to override Gatekeeper when opening software that isn't signed correctly or notarized. They'll need to visit System Settings > Privacy & Security to review security information for software before allowing it to run."

Apple Support, "Safely open apps on your Mac": "Click Privacy & Security, scroll down, and click the Open Anyway button to confirm your intent to open or install the app."

That is the owner's decision, made in System Settings, for one app.

Removing the quarantine attribute from one item the owner has decided to trust also stops the check. The `-d` form of `xattr(1)` deletes one named attribute:

```bash
xattr -d com.apple.quarantine /Applications/<App>.app
```

Never use `-r` over a whole folder of downloads, and never run `spctl --global-disable`. In the current man page that subcommand is described as "Reveal the option to allow applications downloaded from anywhere in the Privacy & Security settings pane", which turns off the check for everything, and requires root.

---

### TCC privacy permissions

Access to protected data (Files and Folders, Full Disk Access, Camera, Microphone, Screen Recording, Accessibility, Automation and others) is granted per app by the owner in System Settings, Privacy and Security. Apple Support, "Control access to files and folders on Mac", describes the Files and Folders list where "For each app in the list, you turn its access to specific locations on or off".

1. A terminal or an agent's host app that needs a protected folder must be granted access there by the owner. A command fails with "Operation not permitted" until then, even with `sudo`.
2. Several `tmutil` verbs, for example, "require root and Full Disk Access privileges", see [time-machine-and-snapshots.md](time-machine-and-snapshots.md).
3. The permission belongs to the responsible app, which for a command line tool is usually the terminal application that launched it.
4. Never edit the TCC database files. They are protected by System Integrity Protection, and editing them is not a supported interface.

Resetting decisions makes apps prompt again. From `tccutil(1)`: "Reset all decisions for the specified service, causing apps to prompt again the next time they access the service. If a bundle identifier is specified, the service will be reset for that bundle only."

```bash
tccutil reset ScreenCapture <bundle id>
```

Always pass a bundle identifier, so only one app is affected, and tell the owner the prompt will come back.
