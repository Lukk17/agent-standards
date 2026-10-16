# Storage

SMART and NVMe health, filesystem errors, free space, mount options and encryption state. The rules live in [SKILL.md](../SKILL.md). Linux commands below were executed read-only on CachyOS on 2026-10-13 unless marked otherwise, macOS and Windows commands are UNVERIFIED.

---

### Never-touch devices first

Read the never-touch table in `MACHINE.md` before the first storage command. Those devices get listing level only: `lsblk` on Linux, `Get-Disk` on Windows, `diskutil list` on macOS. No SMART query, no filesystem tool, no mount, no `blkid -p`, even read-only, and no suggested fix. Device names such as `sdb` can move between boots, so match the model from `lsblk -o NAME,MODEL,SIZE` against the table before every per-device command.

---

### SMART and NVMe health

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `sudo smartctl -H -A /dev/<disk>` for each disk not on the never-touch list | Root only, so each line goes to Needs root | verified root only: unprivileged it printed `Smartctl open device: /dev/nvme0 failed: Permission denied`, smartmontools 7.5 |
| Linux | `sensors` | NVMe `Composite` near its own `crit` value printed on the same line | verified, the drive prints its own `high` and `crit` |
| macOS | `diskutil info disk0` | `SMART Status` other than `Verified` | UNVERIFIED |
| Windows | `Get-PhysicalDisk \| Select-Object FriendlyName,MediaType,HealthStatus,OperationalStatus` | `HealthStatus` other than `Healthy`, `OperationalStatus` other than `OK` | UNVERIFIED |
| Windows | `Get-PhysicalDisk \| Get-StorageReliabilityCounter \| Select-Object DeviceId,Temperature,Wear,ReadErrorsUncorrected,WriteErrorsUncorrected,PowerOnHours` | Needs elevation, so it goes to Needs root as `needs: elevated` | UNVERIFIED |

When the owner pastes `smartctl` output, read these. The interpretation is common practice rather than a quoted vendor rule, inferred with high confidence, and each drive vendor sets its own thresholds.

| Field | Wrong looks like |
|---|---|
| `SMART overall-health self-assessment test result` | Anything but `PASSED`, `fail` |
| SATA `Reallocated_Sector_Ct`, `Current_Pending_Sector`, `Offline_Uncorrectable` raw value | Non-zero is `warn`, growing since the baseline is `fail` |
| SATA `UDMA_CRC_Error_Count` raw value | Growing points at the cable or port rather than the disk, `warn` |
| NVMe `Critical Warning` | Anything but `0x00`, `fail` |
| NVMe `Percentage Used` | Above 90, `warn`, the endurance rating is nearly spent |
| NVMe `Available Spare` against `Available Spare Threshold` | At or below the threshold, `fail` |
| NVMe `Media and Data Integrity Errors` | Non-zero, `warn`, growing, `fail` |
| NVMe `Unsafe Shutdowns` | Growing fast since the baseline points at power loss or hard resets |

---

### Filesystem errors

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `journalctl -b --no-pager -q -p warning -g 'I/O error\|blk_update_request\|nvme.*(timeout\|reset)\|ata[0-9].*(error\|failed)\|BTRFS (error\|warning)\|EXT4-fs error\|ntfs3\|fs-verity'` | Any I/O error, any BTRFS or EXT4 error. `ntfs3` link count corrections are the driver repairing on the fly, `warn`, and say the volume needs a Windows `chkdsk` by the owner | verified. On the test machine it surfaced ten `ntfs3(nvme0n1p3): ... Correct links count` lines and two `fs-verity (dm-0, inode ...): FILE CORRUPTED!` lines |
| Linux, btrfs | `btrfs device stats /` | Any counter above 0. Works unprivileged on a mount point the user can read, `/root` answered `Permission denied` | verified, all zero |
| Linux, btrfs | `btrfs scrub status /` | `Error summary` other than `no errors found`, or a last scrub older than the owner's schedule | verified unprivileged |
| Linux, ext4 | `sudo tune2fs -l /dev/<partition>` | `Filesystem state` other than `clean`, a recent `Last error time`. Root only | UNVERIFIED |
| macOS | `diskutil verifyVolume /` | Anything but a clean verdict. Verifying the boot volume may need root, if so list it | UNVERIFIED |
| Windows | `fsutil dirty query C:` | `Volume C: is dirty`. Likely needs elevation | UNVERIFIED |
| Windows | `Get-Volume \| Select-Object DriveLetter,FileSystemLabel,FileSystem,HealthStatus,SizeRemaining,Size` | `HealthStatus` other than `Healthy` | UNVERIFIED |

Microsoft describes the dirty bit: "When a volume's dirty bit is set, autochk automatically checks the volume for errors the next time the computer is restarted", and lists "Corruption was detected on the volume" among its causes (<https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/fsutil-dirty>, fetched 2026-10-13). Never run `fsutil dirty set`, `chkdsk /f`, `chkdsk /r`, `fsck`, `ntfsfix` or `btrfs check --repair`. A read-only `chkdsk C: /scan` needs elevation and goes to the owner.

A `FILE CORRUPTED` line from fs-verity names an inode. Mapping it to a path needs `sudo btrfs inspect-internal inode-resolve <inode> /`, which goes to Needs root. Treat it as `fail` until the owner knows which file it is. If `MACHINE.md` records RAM above its rated speed, mention it next to any checksum or corruption finding.

---

### Free space

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `df -h -x tmpfs -x devtmpfs -x efivarfs -x squashfs` | Any filesystem above 90 percent, the boot partition above 80 percent before a kernel update | verified |
| Linux, btrfs | `btrfs filesystem usage -T /` | `Device unallocated` below a few GiB on a busy filesystem, `warn`. Unprivileged it prints the overall block and warns that per device detail needs root | verified |
| macOS | `df -h /`, `diskutil apfs list` | Container free space below 10 percent | UNVERIFIED |
| Windows | `Get-Volume` as above | `SizeRemaining` below 10 percent of `Size` on the system drive | UNVERIFIED |

---

### Mount options

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `findmnt -rno TARGET,SOURCE,FSTYPE,OPTIONS` | A filesystem mounted twice at two targets, `warn`. A filesystem mounted `ro` that should be `rw`, which often means the kernel remounted it after an error, `fail` | verified, the test machine showed one NTFS partition at both `/mnt/dev` and `/run/media/lukk/Dev` |
| Linux | `grep -vE '^\s*(#\|$)' /etc/fstab` | A non-boot data disk line without `nofail` | verified |
| Linux | `systemctl --failed --type=mount --no-legend` | Any failed mount unit | verified, none |

Why `nofail` matters on a disk the system can boot without: the local systemd 262 manual page `systemd.mount(5)` says "With nofail, this mount will be only wanted, not required, by local-fs.target or remote-fs.target ... This means that the boot will continue without waiting for the mount unit and regardless whether the mount point can be mounted successfully." Without it, a missing or failing data disk holds up the boot. That consequence is inferred from the quoted text, high confidence. Root, `/boot`, `/home` and anything the session needs stay required.

On a dual boot machine, an NTFS volume mounted read-write by Linux is only safe while Windows Fast Startup is off, which `MACHINE.md` records as an owner rule. Report a read-write NTFS mount next to that rule, and leave the Fast Startup check to `windows`.

---

### Encryption state

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `lsblk -o NAME,FSTYPE,MOUNTPOINTS` | A partition the owner expects encrypted shows a plain filesystem rather than `crypto_LUKS` with a `crypt` child | verified |
| Linux | `sudo cryptsetup luksDump /dev/<partition>` | Key slot and token detail, root only | UNVERIFIED |
| macOS | `fdesetup status` | `FileVault is Off` where the owner expects it on | UNVERIFIED |
| Windows | `manage-bde -status`, `Get-BitLockerVolume` | Both need elevation, so they go to Needs root | UNVERIFIED |

Never unlock, mount or probe an encrypted volume to answer this. The state from the listing is enough.
