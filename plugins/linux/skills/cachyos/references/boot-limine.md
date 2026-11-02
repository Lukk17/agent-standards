# Boot: Limine, Snapshot Entries, Recovery

Read this before changing the kernel command line, the bootloader or the initramfs, before restoring a snapshot, or when the machine does not boot. The rules live in [SKILL.md](../SKILL.md).

---

### Discover how this machine boots

Read-only unless marked. Compare every answer with the Boot and Storage sections of `MACHINE.md`, and never touch a disk it lists as never-touch.

1. Which bootloader: `bootctl status` reports the current boot loader, and `efibootmgr` lists the firmware entries and `BootOrder`. Another operating system, such as Windows, usually has its own firmware entry. `limine-scan` exists to add other systems to the Limine menu.
2. The boot partition: `findmnt /boot` and `lsblk -f`. A vfat `/boot` is often mounted `umask=0077`, so listing it needs root: the owner runs `sudo ls /boot`.
3. The root device: `findmnt /`, and `lsblk -o NAME,FSTYPE,MOUNTPOINTS` for a LUKS mapping. With systemd hooks the initramfs unlocks LUKS through `sd-encrypt`.
4. The kernel command line in use: `cat /proc/cmdline`. Its source of truth on CachyOS with Limine is `/etc/default/limine`, key `KERNEL_CMDLINE[default]`, alongside `ESP_PATH` and `BOOT_ORDER`. The generated `/boot/limine.conf` is overwritten by `limine-mkinitcpio`, so edits there do not stick.
5. Packages and hooks: `pacman -Q limine limine-mkinitcpio-hook limine-snapper-sync` and `ls /usr/share/libalpm/hooks/ | grep -i -E 'limine|snap'`. `limine-mkinitcpio-hook` builds the initramfs and kernel entries on kernel upgrades. `limine-snapper-sync` turns snapper snapshots into boot entries.
6. Snapshot entry settings: `/etc/limine-snapper-sync.conf`, for example `LIMIT_USAGE_PERCENT`, `EXCLUDE_SNAPSHOT_ENTRIES` and `RESTORE_METHOD`. Its documentation is local at `/usr/share/doc/limine-snapper-sync/README.md`. Read it before acting.

---

### Changing boot options

1. Snapshot, and keep a copy: the owner runs `sudo cp -a /etc/default/limine /etc/default/limine.bak.$(date +%s)`.
2. The owner edits `/etc/default/limine`. Copy the LUKS and `root=` parameters exactly from the current `/proc/cmdline`, because a typo in them means no unlock.
3. Regenerate: `sudo limine-mkinitcpio`, and read its output for errors.
4. Reboot. If the default entry fails, choose the fallback kernel, the fallback initramfs, or a snapshot entry, then restore the backup.
5. The same regeneration applies after changing `/etc/mkinitcpio.conf` or files in `/etc/mkinitcpio.conf.d/`. Snippets a hardware tool generated are not edited by hand, see [hardware-nvidia.md](hardware-nvidia.md).

UNVERIFIED end to end. The tool names were verified on one host.

---

### Snapshot boot entries and restoring

Per the local `limine-snapper-sync` README: each snapper snapshot gets a boot entry together with its matching kernel files, stored on the boot partition. Deleting a snapshot removes the entry and its kernel files, and snapshots created before the tool was installed get no entries. This is how a rollback keeps the kernel in step with the restored root, which a plain btrfs restore does not.

Restoring when a change broke the system but it still boots:

1. Reboot, open the Limine menu, and choose a snapshot from the Snapshots submenu. It boots read-only. Pick one from before the bad change. Pre snapshots of pacman transactions carry the command in their description.
2. Check that the snapshot works. A notification offers to restore. The command line equivalent is `limine-snapper-restore`, run by the owner inside the booted snapshot before rebooting into the normal system. An agent never drives it.
3. The restore method comes from `RESTORE_METHOD` in the configuration. Read what it means in the README before restoring.
4. Reboot into the normal entry and verify as the `arch-linux` skill describes after a rollback: kernel against package, failed units, package integrity, and a change log entry in `MACHINE.md`.
5. `limine-snapper-restore --kernels <snapshot id>`, run as root, restores only the kernel files from one snapshot, for the case where the kernel and root disagree. UNVERIFIED.
6. `limine-snapper-list` and `limine-snapper-info` show entries and their status.
7. A snapshot boot is read-only, so some services fail to start there. That is expected, and a reason to restore promptly if that is the choice.

`/home` is usually a separate subvolume outside every snapshot, so a restore does not touch it.

---

### Recovery from a live ISO

When no entry boots. Needs a CachyOS live USB from `https://cachyos.org/download/` and the owner at the keyboard.

1. Boot the live ISO and run `cachy-chroot` (package `cachy-chroot` in the `[cachyos]` repository), which mounts the installed system, including the LUKS unlock and the btrfs subvolumes, and enters a chroot. Do not `pacman -Sy` it on the live system. If it is missing there, follow `https://wiki.cachyos.org/features/cachy_chroot/`.
2. Select the root partition, accept the CachyOS btrfs subvolume preset, and mount the boot partition at `/boot` when asked. Without `/boot`, kernels and the bootloader cannot be repaired.
3. Inside the chroot: `pacman -Syu` if a half finished upgrade is the cause, then `mkinitcpio -P`, then `limine-mkinitcpio`. If the Limine EFI file itself is missing, `limine-install` from `limine-mkinitcpio-hook` reinstalls it. Read its help before running it, and check with `efibootmgr` afterwards that the other operating systems' entries survived.
4. Exit the chroot, reboot, remove the USB.
5. Prefer rolling back to a snapshot over repairing in a chroot when an upgrade caused it.

UNVERIFIED. The package and tool names were verified on one host, and the steps follow the CachyOS documentation.

---

### Do not

1. Edit `/boot/limine.conf` by hand for a permanent change.
2. Run GRUB or systemd-boot commands on a Limine machine. `bootctl status` tells you which loader is current.
3. Use Btrfs Assistant or a raw btrfs command to restore the root subvolume. It does not know about the kernel files on `/boot`.
4. Delete `.snapshots`, or `btrfs subvolume delete` the live root.
5. Format or resize the boot partition, or touch another operating system's EFI partition.
6. Touch any disk `MACHINE.md` lists as never-touch, such as BitLocker volumes, while repairing anything.
