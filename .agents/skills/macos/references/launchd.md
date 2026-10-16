# launchd, launchctl, LaunchAgents and LaunchDaemons

Read this before making anything start at login or at boot, or before stopping or restarting a background job. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Sources: the `launchctl(1)` and `launchd.plist(5)` man pages as shipped with Xcode 27.2 beta 2, read through the community mirror `https://keith.github.io/xcode-man-pages/` on 2026-10-13. Check the local copy with `man launchctl` before relying on a flag.

---

### Where jobs live

From `launchd.plist(5)`:

| Directory | Meaning |
|---|---|
| `~/Library/LaunchAgents` | "Per-user agents provided by the user." |
| `/Library/LaunchAgents` | "Per-user agents provided by the administrator." |
| `/Library/LaunchDaemons` | "System-wide daemons provided by the administrator." |
| `/System/Library/LaunchAgents` | "Per-user agents provided by OS X." |
| `/System/Library/LaunchDaemons` | "System-wide daemons provided by OS X." |

An agent runs in the user's session and can show UI. A daemon runs as root, or as a named user, with no session. Never edit anything under `/System`, which System Integrity Protection protects anyway. Per-user work belongs in `~/Library/LaunchAgents`. `/Library` needs the owner's administrator rights.

---

### Domains and targets

`launchctl` addresses jobs by domain: `system/` for daemons and `gui/<uid>/` for the logged-in user's agents, so a service target looks like `gui/501/com.example.job`. Get the uid with `id -u`.

```bash
launchctl print gui/$(id -u)/<label>
```

```bash
launchctl list | grep -i <part of label>
```

`print` shows the job's state, its program, the last exit status and why it is or is not running.

---

### Load, unload, enable, kick

The man page lists `load` and `unload` under LEGACY SUBCOMMANDS, with "Recommended alternative subcommands: bootstrap | bootout | enable | disable". Use the modern form.

Load a per-user agent:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<label>.plist
```

Unload it:

```bash
launchctl bootout gui/$(id -u)/<label>
```

Run it now, killing a running instance first:

```bash
launchctl kickstart -k gui/$(id -u)/<label>
```

`enable` and `disable` "persists across boots", and a disabled service "cannot be loaded in the specified domain until it is once again enabled". A job that refuses to load is often disabled: check with `launchctl print-disabled gui/$(id -u)`.

Daemons in the `system` domain need `sudo launchctl bootstrap system /Library/LaunchDaemons/<label>.plist`, run by the owner.

---

### A minimal agent

`~/Library/LaunchAgents/com.example.job.plist`, with the file name matching the `Label`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.example.job</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/some-tool</string>
    <string>--flag</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/USERNAME/Library/Logs/com.example.job.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/USERNAME/Library/Logs/com.example.job.log</string>
</dict>
</plist>
```

1. Use absolute paths everywhere. A launchd job does not get the login shell's `PATH`, so a bare `some-tool` fails. A tilde is not expanded either.
2. Check the file before loading it: `plutil -lint <file>`.
3. Logs go where `StandardOutPath` and `StandardErrorPath` point, otherwise read the unified log, see [logs.md](logs.md).
4. Record the label, the file and how to `bootout` it in the `MACHINE.md` change log.

Login items added in System Settings, General, Login Items, and background items registered by apps are managed there by the owner. Do not delete another app's plist to stop it.
