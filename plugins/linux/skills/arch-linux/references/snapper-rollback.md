# Snapshots and Rollback

Read this before a risky change, to take the snapshot, and when something broke and you need to go back. The rules live in [SKILL.md](../SKILL.md).

---

### Discover what is covered

Nothing here is the same on two machines. Find out, then compare with `MACHINE.md`:

1. Root filesystem and subvolumes: `findmnt -no FSTYPE,SOURCE /` and `findmnt -t btrfs -o TARGET,SOURCE,OPTIONS`. Each separate subvolume, often `/home`, `/var/log`, `/var/cache` and `/var/tmp`, is outside a root rollback. A rollback that keeps `/var/log` and the package cache is useful, because the evidence survives.
2. Snapper configs: `sudo snapper list-configs`, run by the owner where the normal user gets "No permissions". A config usually exists for `/` only.
3. Automatic pairs around pacman: `pacman -Q snap-pac`. When installed, every transaction gets a pre and post snapshot.
4. Timeline and limits: the values in `/etc/snapper/configs/<config>` (`TIMELINE_CREATE`, `NUMBER_LIMIT`, `SPACE_LIMIT`, `FREE_LIMIT`). The cleanup timer deletes snapshots by those limits, so rollback points can disappear on a nearly full disk.
5. The boot partition: `findmnt /boot` and `findmnt /efi`. A separate vfat `/boot` holds kernels and the bootloader configuration and is in no btrfs snapshot.
6. Snapshot boot entries: check for `limine-snapper-sync` or `grub-btrfs` with `pacman -Q`. The `cachyos` skill covers the Limine route.

On a machine without snapper, `MACHINE.md` names the snapshot tool in use, for example Timeshift. Use that tool's own commands and do not mix two tools on one filesystem.

---

### Take a snapshot

The owner runs it, with a description that says why:

```bash
sudo snapper -c root create -d "before editing fstab"
```

Do it before kernel or bootloader work, initramfs changes, `/etc` edits that can stop boot (fstab, crypttab, mkinitcpio, bootloader configuration), driver changes, bulk package removal and systemd unit changes. A pacman transaction already gets a pair from `snap-pac`, so do not double up. Confirm it exists with `sudo snapper -c root list | tail -5`.

---

### Undo levels, smallest first

1. One file under `/etc` or `/usr`: copy it out of a read-only snapshot, mounted under `/.snapshots/<number>/snapshot/`. See what changed first with `sudo snapper -c root status <older>..<newer>` and `sudo snapper -c root diff <older>..<newer> /etc/fstab`, then the owner runs `sudo cp -a /.snapshots/<number>/snapshot/etc/fstab /etc/fstab`.
2. A set of files changed between two snapshots: `sudo snapper -c root undochange <older>..<newer> /etc/some/path`. Use `<number>..0` to compare against the current state. Always give a path, never undo the whole filesystem this way.
3. One package: downgrade from the cache, see [pacman-discipline.md](pacman-discipline.md).
4. A whole bad upgrade, system still boots: boot the matching snapshot from the boot menu if snapshot entries exist, check that it works, then make it permanent with the tool that created the entries.
5. System does not boot: snapshot entries if the menu still works, otherwise a live ISO and a chroot.
6. Something under `~`: usually not covered. Restore from a backup copy, see below.

---

### Before you roll back

1. Say what you intend to restore and what will be lost. A root rollback discards every change to `/etc`, `/usr` and `/var/lib` made after that snapshot, including installed packages and their database state.
2. Check that nothing outside the root subvolume must match. Kernel images live in `/boot`. A rolled back root that expects a different kernel than the one in `/boot` loads no modules: no GPU driver, no Wi-Fi, a display stuck at low resolution. Prefer a tool that restores the matching kernel with the snapshot over any generic btrfs restore.
3. Never `btrfs subvolume delete` the live root or `.snapshots`.
4. After a rollback, compare `uname -r` with the kernel package version, run `systemctl --failed` and `pacman -Qk 2>&1 | grep -v ' 0 missing'`, then record the event in the `MACHINE.md` change log.

---

### Back up before editing anything in the home directory

Snapshots usually do not cover `~`. Before editing a user configuration file, copy it: `cp -a <file> <file>.bak.$(date +%s)`. Resetting an application to defaults means moving its file away so the application writes a fresh one on the next start. Ask first, because a reset throws away the owner's settings. Remove old `.bak.*` files only with the owner's approval.
