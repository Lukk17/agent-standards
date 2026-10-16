# Where Files Live

Read this when looking for an application's settings, caches or logs, before deleting anything to "reset" an app, and when a cross-platform tool cannot find its configuration. The rules live in [SKILL.md](../SKILL.md).

Source: Apple's "macOS Library Directory Details" in the File System Programming Guide, fetched on 2026-10-13. That guide is archived, and the layout it describes is still the one apps use.

---

### The user Library

`~/Library` is hidden in Finder by default but is an ordinary directory in the shell.

| Directory | Holds, in Apple's words where quoted |
|---|---|
| `~/Library/Application Support/<bundle id or app name>` | "all app-specific data and support files", which "can include files that contain user data" |
| `~/Library/Preferences` | "the user's preferences", which you change through `defaults`, never by creating files there, see [defaults.md](defaults.md) |
| `~/Library/Caches/<bundle id>` | "cached data that can be regenerated as needed" |
| `~/Library/Logs` | "log files for the console and specific system services" |
| `~/Library/LaunchAgents` | "the agent apps to launch and run for the current user", see [launchd.md](launchd.md) |
| `~/Library/Containers/<bundle id>` | the sandbox of a sandboxed app, which holds its own Library tree |
| `~/Library/Group Containers` | data shared between apps from one developer |

1. Caches are safe to remove with the app quit. Application Support holds user data and is never deleted without the owner's approval and a backup.
2. "Resetting" an app means moving its preferences domain and support folder aside, with the app quit, so they can be put back.
3. Some folders under `~/Library`, such as Mail and Messages, need Full Disk Access to read, see [gatekeeper-and-tcc.md](gatekeeper-and-tcc.md).

---

### Command line tools

Cross-platform tools usually follow their own convention rather than Apple's: many read `~/.config/<tool>` (the XDG layout), others a dotfile in `~`, and some use `~/Library/Application Support/<tool>` on macOS only. Check the tool's documentation, and check both locations before concluding a configuration file is missing. A tool that honours `XDG_CONFIG_HOME` uses it when set.

---

### System locations

| Path | Notes |
|---|---|
| `/System` | the sealed system volume, protected by System Integrity Protection, never written |
| `/usr` | protected by SIP, except `/usr/local` |
| `/Library` | machine wide support files, preferences, LaunchAgents and LaunchDaemons, writable by administrators |
| `/Applications` | apps for every user, casks install here |
| `/opt/homebrew` | Homebrew's prefix on Apple silicon, see [homebrew.md](homebrew.md) |

---

### Case and line endings

APFS volumes are case-insensitive by default, so `Readme.md` and `README.md` are one file. Check a volume with `diskutil info / | grep -i 'case'`. Line endings are LF, the same as Linux.
