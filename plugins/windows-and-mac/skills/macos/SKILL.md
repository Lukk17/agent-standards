---
name: macos
description: 'Administering a Mac from an agent: Homebrew formulae and casks, launchd, defaults and preference domains, Gatekeeper and TCC permissions, the Keychain, Time Machine and local snapshots, softwareupdate and the unified log. Use when the user says "run this at login", "app is damaged and cannot be opened" or "show me the logs for this app". Not for writing shell scripts, use `bash`.'
---

# macOS Administration

How to change a Mac without fighting System Integrity Protection, the privacy prompts or the preferences cache, and with a snapshot behind any risky change. Behaviour moves between macOS releases, so check the version first and prefer the tool's own man page over memory.

Written for macOS 15 and later on Apple silicon, from Apple support and developer pages and the man pages shipped with Xcode. No command in this skill was executed, so every command is UNVERIFIED unless a topic file says otherwise.

| Task | Open |
|---|---|
| Install, upgrade or remove software, formula against cask, Brewfiles, `brew services` | [homebrew.md](references/homebrew.md) |
| Run something at login or boot, LaunchAgents, LaunchDaemons, `launchctl` | [launchd.md](references/launchd.md) |
| Read or change a preference with `defaults` | [defaults.md](references/defaults.md) |
| An app that "cannot be opened", the quarantine flag, privacy permissions | [gatekeeper-and-tcc.md](references/gatekeeper-and-tcc.md) |
| Store or read a secret through the Keychain | [keychain.md](references/keychain.md) |
| Time Machine, local snapshots, a restore point before a change | [time-machine-and-snapshots.md](references/time-machine-and-snapshots.md) |
| macOS updates from the command line | [software-update.md](references/software-update.md) |
| Read logs for a process, a subsystem or a time window | [logs.md](references/logs.md) |
| Where settings, caches and logs live | [paths.md](references/paths.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`: the macOS version, the CPU architecture and Homebrew prefix, whether Time Machine is configured, FileVault state, disks that must never be touched, and the change log. Read it before acting. This skill holds no facts about any single machine. Discover with `sw_vers`, `uname -m` and the commands in the topic files, and compare with `MACHINE.md`.

---

### When to activate

- Installing, upgrading or removing software with Homebrew
- Anything that should start at login or at boot
- `defaults read` or `defaults write`, or a `.plist` under `~/Library/Preferences`
- An app blocked by Gatekeeper, a quarantine flag, or a missing privacy permission
- Reading or storing a credential in the Keychain
- Time Machine, local snapshots, or macOS updates
- Reading the unified log to explain a failure
- Also covers Homebrew first (formula for CLI, cask for GUI), Brewfiles, launchd with launchctl, LaunchAgents and LaunchDaemons, the defaults command and preference domains, Gatekeeper and the quarantine attribute, TCC privacy permissions and Full Disk Access, the Keychain and the security tool, Time Machine and APFS local snapshots, softwareupdate, the unified log with log show and log stream, and where files live under ~/Library against ~/.config
- The user says "brew install or brew install --cask", "launchctl load is deprecated", "change a hidden setting with defaults write", "remove the quarantine flag", "Terminal needs Full Disk Access", "read a password from the keychain", "take a local snapshot first", "install macOS updates from the terminal" or "where does this app keep its settings"

---

### When not to activate

- Writing or reviewing a shell script, use `bash`
- Building, signing or notarizing an app for distribution, which is Apple developer tooling rather than administration
- Fleet management through MDM profiles, which an individual Mac's owner usually cannot override
- Provisioning many Macs the same way, use `ansible`

---

### Hard rules

1. The agent does not run `sudo`. A command that needs administrator rights goes to the owner with what it changes. Homebrew itself must never run under `sudo`.
2. Install everything Homebrew carries with Homebrew: a formula for a command line tool, a cask for a GUI application. Only when Homebrew has neither, use the App Store through `mas` or the vendor's own installer. An application already installed another way stays with that route, and no application is installed through two. The order is set out in [homebrew.md](references/homebrew.md).
3. Never disable System Integrity Protection or Gatekeeper globally. Clear quarantine on one item the owner trusts, and only that item.
4. Never edit TCC databases or grant privacy permissions on the owner's behalf. The owner grants them in System Settings, Privacy and Security.
5. Never print a secret. Do not read a Keychain password into the session, a log or a file.
6. Take a local snapshot, or confirm a recent backup, before an OS update or a change under `/Library`.
7. Read a preference before writing it, and record the old value so it can be restored.
8. Record every system change in the change log of `MACHINE.md`, with how to undo it.

---

### Related skills

- `bash` owns the shell scripts that wrap these commands
- The `security-auditor` agent owns judging whether an unsigned app or a third party tap is acceptable
- `git-workflow` owns repository settings such as case sensitivity and line endings, in its `references/git-config.md`
- `ansible` owns provisioning Macs reproducibly

---

### Checklist

- [ ] `MACHINE.md` read, and `sw_vers` and `uname -m` checked
- [ ] Homebrew used first, formula for a command line tool and cask for a GUI app, no `sudo brew`
- [ ] The App Store or a vendor installer used only for software Homebrew does not carry
- [ ] launchd jobs loaded with `bootstrap` into the right domain, not the legacy `load`
- [ ] Old preference values recorded before any `defaults write`
- [ ] Quarantine cleared on one named item only, Gatekeeper and SIP left on
- [ ] No privacy permission granted and no secret printed by the agent
- [ ] Snapshot or backup confirmed before updates or changes under `/Library`
- [ ] The change and its undo recorded in the `MACHINE.md` change log
