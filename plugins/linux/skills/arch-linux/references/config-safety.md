# Editing Configuration Safely

Read this before editing any configuration file, before anything that needs root, and before writing a pacman hook or a systemd drop-in. The rules live in [SKILL.md](../SKILL.md).

Four ideas carry the whole file: never edit what a package owns, put the change where the package does not overwrite it, back up before resetting, and use the right privilege route.

---

### Never edit what a package owns

A file a package owns is overwritten by the next upgrade, or left beside a `.pacnew` (see [pacnew.md](pacnew.md)), and an edit leaves no record. Reading those files is safe and encouraged, because they document the default.

1. Find the owner: `pacman -Qo <path>`. No owner means a file a person or a tool created.
2. Never edit anything under `/usr`, and never edit `/etc/skel`. `/etc/skel` is copied into a home directory once, when the account is created, so it never updates an existing user either.
3. Files a package lists as backup files (`pacman -Qii <pkg>`, "Backup Files") are meant to be edited, and `.pacnew` handling applies to them.
4. Use the override mechanism of whatever you are configuring:

| What | Packaged default | Put the change in |
|---|---|---|
| Kernel parameters at runtime | `/usr/lib/sysctl.d/` | `/etc/sysctl.d/99-local.conf`, applied with `sudo sysctl --system` |
| A systemd unit | `/usr/lib/systemd/system/` | `/etc/systemd/system/<unit>.d/override.conf`, see [systemd-journal-triage.md](systemd-journal-triage.md) |
| systemd settings (journald, timeouts, limits) | `/usr/lib/systemd/*.conf.d/` | `/etc/systemd/<name>.conf.d/*.conf` |
| udev rules | `/usr/lib/udev/rules.d/` | `/etc/udev/rules.d/`, where the same file name overrides and a higher number runs later |
| Kernel module options | `/usr/lib/modprobe.d/` | `/etc/modprobe.d/` |
| mkinitcpio | `/etc/mkinitcpio.conf` and `/etc/mkinitcpio.conf.d/` | an additional `/etc/mkinitcpio.conf.d/99-local.conf`, leaving files another tool generated alone |
| WirePlumber and PipeWire | `/usr/share/wireplumber/`, `/usr/share/pipewire/` | `~/.config/wireplumber/wireplumber.conf.d/`, see [pipewire-wireplumber.md](pipewire-wireplumber.md) |
| Desktop entries and autostart | `/usr/share/applications/` | `~/.local/share/applications/`, `~/.config/autostart/` |
| KDE Plasma settings | `/usr/share/` | files under `~/.config` and `~/.local/share`, see the `kde-plasma` skill |
| pacman options | `/etc/pacman.conf` | edit with care, keeping a backup, see [pacnew.md](pacnew.md) |

5. Prefer a new file with a high number over editing an existing one, so the change is visible and easy to remove.
6. Record every file you create in the `MACHINE.md` change log, with its path and the reason.

---

### Back up before you change, reset only with permission

1. For anything under `~`, which snapshots usually do not cover: `cp -a <file> <file>.bak.$(date +%s)` before editing. For `/etc`, take a snapshot (see [snapper-rollback.md](snapper-rollback.md)) and keep a `.bak.<epoch>` beside the file as well.
2. Validate before relying on the change, with the program's own check where it has one: `systemd-analyze verify`, `visudo -c` (sudoers is only ever edited through `visudo`), `desktop-file-validate`, `kbuildsycoca6` after KDE service changes, and `mkinitcpio -P` only when the owner agrees.
3. Resetting an application to defaults throws away the owner's settings. Ask first, and move the file away rather than deleting it, so it can be put back.
4. If a change did not work, restore the backup and say so. Do not stack further guesses on top.

---

### Privilege: sudo, pkexec, and what an agent may do

1. The agent has no terminal in which to type a password, and `sudo -n` answers "a password is required". Do not look for a way around this.
2. For a command that needs root, print it for the owner with what it does and what it changes. In Claude Code the owner runs it with the `!` prefix, for example `! sudo systemctl daemon-reload`, which runs in the owner's session where the prompt works. Verify afterwards with a read-only command.
3. `pkexec` is for a caller that cannot use a terminal, such as a graphical background process. With the owner at the keyboard it is not needed. Do not use it to push a change through a graphical prompt unless the owner asks.
4. Do not wrap a command that elevates itself, such as `paru`, in another `sudo`. `makepkg` never runs as root.
5. Group the root steps of one task into a short numbered list, so the owner runs them in order with one decision, and a failure at step 2 stops the rest.
6. Never `sudo` a shell redirect. `sudo echo x > /etc/file` writes the file as the unprivileged user and fails. Use `printf '...\n' | sudo tee /etc/file` or `sudoedit`. Never `chmod -R` or `chown -R` on a system path.
7. Never create passwordless sudo rules or edit `/etc/sudoers` or `/etc/sudoers.d` for convenience.

---

### Hooks: run something automatically on an event

1. pacman hooks. Packaged ones live in `/usr/share/libalpm/hooks/`, your own go in `/etc/pacman.d/hooks/` as `NN-name.hook`, and they run in file name order across both directories. Every key is in `man alpm-hooks`. A reminder after a kernel upgrade, with the package name set to the kernel the machine runs:

```ini
[Trigger]
Operation = Upgrade
Type = Package
Target = linux

[Action]
Description = Reminder: reboot to use the new kernel
When = PostTransaction
Exec = /usr/bin/echo "kernel updated, reboot required"
```

2. systemd timers and path units for time or file driven work, see `man systemd.timer` and `man systemd.path`. User ones go in `~/.config/systemd/user/`.
3. Desktop autostart and session scripts for login time work, which belong to the `kde-plasma` skill on Plasma.

A pacman hook runs as root inside a transaction, and a failing `PreTransaction` hook aborts the upgrade. It needs a snapshot, the owner's approval, and a change log entry.

---

### Do not edit generated files

Some files look like configuration but are output. Read the header before editing: a ranked mirrorlist, a bootloader configuration rebuilt by a hook, an initramfs snippet written by a hardware tool, a `/etc/resolv.conf` written by NetworkManager or systemd-resolved, and `/var/lib/alsa/asound.state` written by `alsactl`. Change the input or the tool's own configuration, then regenerate.
