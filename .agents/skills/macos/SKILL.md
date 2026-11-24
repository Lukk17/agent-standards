---
name: macos
description: 'Administering a Mac: Homebrew, launchd, defaults, Gatekeeper, Keychain, Time Machine and logs. Use when the user says "run this at login" or "app is damaged and cannot be opened". Not for shell scripts, use `bash`.'
metadata:
  version: "1.1.0"
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
| Call a change on a Mac done | [checklist.md](references/checklist.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`. Read it before acting. This skill holds no facts about any single machine.

For this skill they are the macOS version, the CPU architecture and Homebrew prefix, whether Time Machine is configured, FileVault state, disks that must never be touched, and the change log. Discover with `sw_vers`, `uname -m` and the commands in the topic files, and compare with `MACHINE.md`.

---

### When not to activate

- Writing or reviewing a shell script, use `bash`
- Provisioning many Macs the same way, use `ansible`
- Repository settings such as case sensitivity and line endings, use `git-workflow`

---

### Hard rules

1. The agent does not run `sudo`. A command that needs administrator rights goes to the owner with what it changes. Homebrew itself must never run under `sudo`.
2. Install everything Homebrew carries with Homebrew: a formula for a command line tool, a cask for a GUI application. Only when Homebrew has neither, use the App Store or the vendor's own installer. An application already installed another way stays with that route, and no application is installed through two. The order is set out in [homebrew.md](references/homebrew.md).
3. Never disable System Integrity Protection or Gatekeeper globally. Clear quarantine on one item the owner trusts, and only that item.
4. Never edit TCC databases or grant privacy permissions on the owner's behalf. The owner grants them in System Settings, Privacy and Security.
5. Never print a secret. Do not read a Keychain password into the session, a log or a file.
6. Take a local snapshot, or confirm a recent backup, before an OS update or a change under `/Library`.
7. Read a preference before writing it, and record the old value so it can be restored.
8. Record every system change in the change log of `MACHINE.md`, with how to undo it.
