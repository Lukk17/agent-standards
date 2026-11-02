# macOS Updates with softwareupdate

Read this before installing macOS or Apple software updates from the command line. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Source: the `softwareupdate(8)` man page as shipped with Xcode, read through `https://keith.github.io/xcode-man-pages/softwareupdate.8.html`.

---

### Rights

From the man page: "softwareupdate requires admin authentication for all commands except `--list`. If you run softwareupdate as a normal admin user, you will be prompted for a password when required." Listing is something the agent can do. Installing is the owner's step.

---

### List

```bash
softwareupdate --list
```

Record the version before updating with `sw_vers`, and read the release notes of a major upgrade before recommending it. Check that the tools the owner relies on, such as Homebrew, the IDE and drivers, support the new release.

---

### Install

Before installing: confirm a backup or take a local snapshot, see [time-machine-and-snapshots.md](time-machine-and-snapshots.md), and make sure the owner has saved open work, because a restart quits applications.

Install one named update from the list:

```bash
softwareupdate --install "<label from --list>"
```

Install all recommended updates:

```bash
softwareupdate --install --recommended
```

1. `--all` installs every listed update, recommended or not. Prefer naming the updates.
2. `--restart` will "Automatically restart if required to complete installation. If the user invoking this tool is logged in then macOS will attempt to quit all applications, logout, and restart." Never add it without the owner's explicit go-ahead.
3. `--fetch-full-installer` downloads a full macOS installer app, and `--install-rosetta` installs Rosetta on Apple silicon. Both are deliberate choices, not routine maintenance.
4. Record the old and new `sw_vers` output in the `MACHINE.md` change log.

On a managed Mac, updates may be deferred or enforced by MDM. If `--list` disagrees with what the owner expects, check System Settings, General, Device Management before assuming a fault.
