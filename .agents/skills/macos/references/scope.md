# Scope

Companion reference for the [macos](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

Administering a Mac from an agent: Homebrew formulae and casks, launchd, defaults and preference domains, Gatekeeper and TCC permissions, the Keychain, Time Machine and local snapshots, softwareupdate and the unified log.

- Installing, upgrading or removing software with Homebrew
- Anything that should start at login or at boot
- `defaults read` or `defaults write`, or a `.plist` under `~/Library/Preferences`
- An app blocked by Gatekeeper, a quarantine flag, or a missing privacy permission
- Reading or storing a credential in the Keychain
- Time Machine, local snapshots, or macOS updates
- Reading the unified log to explain a failure
- Also covers Homebrew first (formula for CLI, cask for GUI), Brewfiles, launchd with launchctl, LaunchAgents and LaunchDaemons, the defaults command and preference domains, Gatekeeper and the quarantine attribute, TCC privacy permissions and Full Disk Access, the Keychain and the security tool, Time Machine and APFS local snapshots, softwareupdate, the unified log with log show and log stream, and where files live under ~/Library against ~/.config
- The user says "run this at login", "app is damaged and cannot be opened", "show me the logs for this app", "brew install or brew install --cask", "launchctl load is deprecated", "change a hidden setting with defaults write", "remove the quarantine flag", "Terminal needs Full Disk Access", "read a password from the keychain", "take a local snapshot first", "install macOS updates from the terminal" or "where does this app keep its settings"

---

### When not to activate

- Writing or reviewing a shell script, use `bash`
- Building, signing or notarizing an app for distribution, which is Apple developer tooling rather than administration
- Fleet management through MDM profiles, which an individual Mac's owner usually cannot override
- Provisioning many Macs the same way, use `ansible`

---

### Related skills

- `bash` owns the shell scripts that wrap these commands
- The `security-auditor` agent owns judging whether an unsigned app or a third party tap is acceptable
- `git-workflow` owns repository settings such as case sensitivity and line endings, in its `references/git-config.md`
- `ansible` owns provisioning Macs reproducibly
