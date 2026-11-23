# Linux Checks

Contents:

- [Before the first command](#before-the-first-command)
- [CPU](#cpu)
- [Memory](#memory)
- [Storage](#storage)
- [System errors](#system-errors)
- [Paths and environment](#paths-and-environment)
- [Packages](#packages)
- [Devices and network](#devices-and-network)
- [Security baseline](#security-baseline)

Every check for a machine that runs Linux, in run order. The rules live in [SKILL.md](../SKILL.md), and how a value becomes a verdict on any operating system is in [judging.md](judging.md). The commands were executed read-only on one CachyOS test machine with an AMD CPU, an NVIDIA GPU, systemd 262, Plasma 6, zsh and bash, and each row says whether it ran. In a table, `all` under Applies to means every Linux machine.

---

### Before the first command

1. Never run `sudo`, `doas`, `pkexec` or anything that asks for a password. A check that needs root goes into Needs root as `needs: sudo <command>`.
2. Never run `fsck`, `ntfsfix` or `btrfs check --repair`.
3. A device in the never-touch table gets listing level only, `lsblk`. No `blkid -p`, even read-only. Device names such as `sdb` can move between boots, so match the model from `lsblk -o NAME,MODEL,SIZE` against the table before every per-device command.
4. List variable names and paths only, never the value of a variable that might hold a secret.

---

### CPU

Model, microcode, frequency governor and power profile, temperatures and throttling.

#### Model and microcode

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `lscpu` | Model differs from `MACHINE.md`, fewer online CPUs than threads | verified |
| all | `grep -m1 microcode /proc/cpuinfo` | Revision differs from the baseline with no package update behind it | verified, printed `0x<revision>` |
| all | the microcode package row in the file for the machine's package manager, [pacman.md](pacman.md), [apt.md](apt.md) or [dnf.md](dnf.md) | No microcode package installed, or the package was updated after the current boot, which means a reboot is owed | see that file |

On Linux the early boot lines that name the microcode revision are often missing from the journal, and `dmesg` is root only while `kernel.dmesg_restrict` is 1. Both were measured on the test machine: `journalctl -k -b` started four minutes after boot and `dmesg` answered `Operation not permitted`. Read `/proc/cpuinfo` instead, and list `sudo dmesg` in Needs root only when the boot lines matter.

#### Governor and power profile

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | Governor `performance` left on a laptop on battery, `powersave` on `acpi-cpufreq` (which pins the lowest frequency), or a driver that changed since the baseline | verified, printed `acpi-cpufreq` and `schedutil` |
| all | `cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference` | Only exists under `amd-pstate` or `intel_pstate` in active mode. Absent under `acpi-cpufreq`, which is not a fault | verified absent |
| all | `powerprofilesctl get` | Profile differs from the owner preference in `MACHINE.md` | verified, printed `balanced` |
| all | `cat /sys/devices/system/cpu/cpufreq/boost` | `0` when the owner expects boost on | verified, printed `1` |

#### Temperatures

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `sensors` | CPU reading near or above the vendor's maximum at idle, or a sensor chip from the baseline missing | verified |

Read the right sensor. On AMD the `k10temp` driver reports `Tctl` and sometimes `Tdie`. The kernel documentation says "On some AMD CPUs, there is a difference between the die temperature (Tdie) and the reported temperature (Tctl)" and "Tdie is the real measured temperature, and Tctl is used for fan control" (<https://docs.kernel.org/hwmon/k10temp.html>). On the AMD test machine `Tctl` read 56.0 and `Tdie` 46.0 at the same moment, so judge against `Tdie` where it exists.

Judge the reading against the vendor's maximum as [judging.md](judging.md) sets out.

#### Throttling

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| Intel | `grep -H . /sys/devices/system/cpu/cpu*/thermal_throttle/*_throttle_count` | Any non-zero count, or a count that grew since the baseline | UNVERIFIED, the directory does not exist on the AMD test machine |
| all | `journalctl -k -b --no-pager -q -g 'thrott\|temperature above\|machine check'` | Any line. `-- No entries --` is the clean answer | verified, clean |
| all | `nvidia-smi --query-gpu=name,temperature.gpu,clocks_event_reasons.active,pstate --format=csv` | A reason bitmask other than `0x0` or `0x1` (idle) while under load. Older drivers spell the field `clocks_throttle_reasons.active` | verified, the test machine's driver printed `0x0000000000000001` |

---

### Memory

Installed modules, memory errors, and how the owner runs a memory test. The verdicts for configured speed, mixed kits and channels are in [judging.md](judging.md).

#### Installed modules

| Applies to | Command | What it gives | Status |
|---|---|---|---|
| all | `free -h`, `swapon --show`, `zramctl` | Total and swap, no per-module detail | verified |
| all | `sudo dmidecode -t memory` | Per slot: `Locator`, `Bank Locator`, `Size`, `Type`, `Speed` (the module's rated speed), `Configured Memory Speed`, `Manufacturer`, `Part Number`, `Rank`, `Configured Voltage`. Root only, so it goes to Needs root | verified root only: unprivileged it printed `/sys/firmware/dmi/tables/smbios_entry_point: Permission denied` |
| all | `decode-dimms` | SPD contents including the XMP profile. Needs the `ee1004` or `at24` module loaded and root to read, so it goes to Needs root as well | present at `/usr/bin/decode-dimms`, not executed |

On Linux the one root command the owner runs is `sudo dmidecode -t memory`. Do not ask for more.

The configured speed is `Configured Memory Speed` from `dmidecode`, and `Locator` and `Bank Locator` name the channel, for example `P0 CHANNEL A`.

#### Memory errors

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `ls /sys/devices/system/edac/mc/` | With ECC memory and an EDAC driver, one `mcX` directory per controller. No `mcX` directory means no EDAC reporting, which is normal for non-ECC desktop memory, so record `unknown (no EDAC)` rather than `ok` | verified, no `mcX` on the test machine |
| all | `grep -H . /sys/devices/system/edac/mc/mc*/ce_count /sys/devices/system/edac/mc/mc*/ue_count` | Any non-zero `ue_count`, or a `ce_count` that grew since the baseline | UNVERIFIED, nothing to read on a non-ECC machine |
| all | `ras-mc-ctl --summary` | Any recorded error. Needs `rasdaemon` running, absent is `unknown`, never install it | UNVERIFIED, `rasdaemon` inactive on the test machine |
| all | `journalctl -k -b --no-pager -q -g 'mce\|machine check\|edac\|hardware error'` | Any line | verified, printed `-- No entries --` |

The kernel RAS guide defines the two counters: a Correctable Error is when "the error detection mechanism detected and corrected the error", an Uncorrected Error is when "the amount of errors happened above the error correction threshold, and the system was unable to auto-correct" (<https://docs.kernel.org/admin-guide/RAS/main.html>).

#### Running a memory test

The memory test for Linux is Memtest86+. The project describes it as "a free, open-source, stand-alone memory tester for IA-32, x86-64, and LoongArch64 systems" that runs "directly by a PC BIOS (legacy or UEFI)" or "via an intermediate bootloader", from "a USB Flash Drive (FAT32 formatted)" (<https://www.memtest.org/>). Let it run at least one full pass, and treat a single error as `fail`. The package that carries it on Arch and CachyOS is named in [pacman.md](pacman.md). The agent never schedules the test, as [judging.md](judging.md) sets out.

---

### Storage

SMART and NVMe health, filesystem errors, free space, mount options and encryption state.

#### SMART and NVMe health

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `sudo smartctl -H -A /dev/<disk>` for each disk not on the never-touch list | Root only, so each line goes to Needs root | verified root only: unprivileged it printed `Smartctl open device: /dev/nvme0 failed: Permission denied`, smartmontools 7.5 |
| all | `sensors` | NVMe `Composite` near its own `crit` value printed on the same line | verified, the drive prints its own `high` and `crit` |

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

#### Filesystem errors

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `journalctl -b --no-pager -q -p warning -g 'I/O error\|blk_update_request\|nvme.*(timeout\|reset)\|ata[0-9].*(error\|failed)\|BTRFS (error\|warning)\|EXT4-fs error\|ntfs3\|fs-verity'` | Any I/O error, any BTRFS or EXT4 error. `ntfs3` link count corrections are the driver repairing on the fly, `warn`, and say the volume needs a Windows `chkdsk` by the owner | verified. On the test machine it surfaced ten `ntfs3(nvme0n1p3): ... Correct links count` lines and two `fs-verity (dm-0, inode ...): FILE CORRUPTED!` lines |
| btrfs | `btrfs device stats /` | Any counter above 0. Works unprivileged on a mount point the user can read, `/root` answered `Permission denied` | verified, all zero |
| btrfs | `btrfs scrub status /` | `Error summary` other than `no errors found`, or a last scrub older than the owner's schedule | verified unprivileged |
| ext4 | `sudo tune2fs -l /dev/<partition>` | `Filesystem state` other than `clean`, a recent `Last error time`. Root only | UNVERIFIED |

A `FILE CORRUPTED` line from fs-verity names an inode. Mapping it to a path needs `sudo btrfs inspect-internal inode-resolve <inode> /`, which goes to Needs root. Treat it as `fail` until the owner knows which file it is.

#### Free space

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `df -h -x tmpfs -x devtmpfs -x efivarfs -x squashfs` | Any filesystem above 90 percent, the boot partition above 80 percent before a kernel update | verified |
| btrfs | `btrfs filesystem usage -T /` | `Device unallocated` below a few GiB on a busy filesystem, `warn`. Unprivileged it prints the overall block and warns that per device detail needs root | verified |

#### Mount options

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `findmnt -rno TARGET,SOURCE,FSTYPE,OPTIONS` | A filesystem mounted twice at two targets, `warn`. A filesystem mounted `ro` that should be `rw`, which often means the kernel remounted it after an error, `fail` | verified, the test machine showed one NTFS partition at both its `fstab` mount point `/mnt/<label>` and a second desktop automount point for the same label |
| all | `grep -vE '^\s*(#\|$)' /etc/fstab` | A non-boot data disk line without `nofail` | verified |
| all | `systemctl --failed --type=mount --no-legend` | Any failed mount unit | verified, none |

Why `nofail` matters on a disk the system can boot without: the local systemd 262 manual page `systemd.mount(5)` says "With nofail, this mount will be only wanted, not required, by local-fs.target or remote-fs.target ... This means that the boot will continue without waiting for the mount unit and regardless whether the mount point can be mounted successfully." Without it, a missing or failing data disk holds up the boot. That consequence is inferred from the quoted text, high confidence. Root, `/boot`, `/home` and anything the session needs stay required.

On a dual boot machine, an NTFS volume mounted read-write by Linux is only safe while Windows Fast Startup is off, which `MACHINE.md` records as an owner rule. Report a read-write NTFS mount next to that rule, and leave the Fast Startup check to `windows`.

#### Encryption state

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `lsblk -o NAME,FSTYPE,MOUNTPOINTS` | A partition the owner expects encrypted shows a plain filesystem rather than `crypto_LUKS` with a `crypt` child | verified |
| all | `sudo cryptsetup luksDump /dev/<partition>` | Key slot and token detail, root only | UNVERIFIED |

---

### System errors

Failed units, crashes, error level log lines since boot, kernel warnings and taint.

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Failed system units | `systemctl --failed --no-legend --plain` | Any line, `fail` | verified, none |
| Failed user units | `systemctl --user --failed --no-legend --plain` | Any line, `fail` | verified, none |
| Crashes | `coredumpctl list --since=-7d --no-pager` | Any entry is worth a line. The same executable crashing repeatedly is `warn`, a system daemon is `fail` | verified, one `SIGABRT` of `/usr/bin/chwd` that day |
| Errors since boot, counted | `journalctl -b -p err --no-pager -q \| wc -l` | A count well above the baseline | verified, 62 |
| Errors since boot, grouped | `journalctl -b -p err --no-pager -q -o cat \| sort \| uniq -c \| sort -rn \| head -20` | New messages compared with the baseline. Group before reading, one noisy line can hide a rare one | verified |
| Previous boot | `journalctl -b -1 -p err --no-pager -q -o cat \| sort \| uniq -c \| sort -rn \| head -20` | Errors right before an unexpected end of the previous boot | verified |
| Boots that ended badly | `journalctl --list-boots --no-pager \| tail -5` | Fewer boots than the owner remembers, or a boot whose last lines show no clean shutdown | verified |
| Kernel warnings | `journalctl -k -b -p warning --no-pager -q -o cat \| grep -v 'UFW BLOCK' \| sort \| uniq -c \| sort -rn \| head -20` | `WARNING:`, `BUG:`, `Oops`, call traces, firmware load failures. Firewall block lines are excluded because they are expected noise | verified, `grep -v` was needed because UFW block lines filled the output |
| Kernel taint | `cat /proc/sys/kernel/tainted` | Any value outside the baseline. Decode the bits before judging | verified, `12288` |

Decode taint with the kernel's own table: "If that returns `0`, the kernel is not tainted; any other number indicates the reasons why it is", with bit 12 "externally-built (out-of-tree) module was loaded" (4096) and bit 13 "unsigned module was loaded" (8192), and bit 9 "kernel issued warning" (512) (<https://docs.kernel.org/admin-guide/tainted-kernels.html>). On the test machine `12288` is 4096 plus 8192, which an out of tree GPU driver produces, so it is `ok` when the baseline says the same. Bit 9 appearing is `warn` and the kernel warning lines above say why.

The journal can miss the first minutes of a boot, and `dmesg` is root only while `kernel.dmesg_restrict` is 1, both measured on the test machine. When an early boot problem is suspected, put `needs: sudo dmesg --level=err,warn` into Needs root.

Read the messages, not only the counts. A line such as `a password is required ; ... COMMAND=/usr/bin/true` in the error log is an agent or script probing `sudo`, which this skill forbids, and is worth naming to the owner.

---

### Paths and environment

PATH duplicates, entries that do not exist, shadowed binaries and which startup file sets what. Why the owner's shell is measured, and what to report, is in [judging.md](judging.md). On the test machine the agent's own PATH had no duplicates, while `zsh -ic` had ten.

#### Measure the shell the owner uses

| Shell | Interactive | Login |
|---|---|---|
| zsh | `zsh -ic 'print -l $path'` | `zsh -lc 'print -l $path'` |
| bash | `bash -ic 'echo "$PATH"' \| tr ':' '\n'` | `bash -lc 'echo "$PATH"' \| tr ':' '\n'` |

The zsh and bash forms were executed. On the test machine the interactive zsh PATH had 34 entries and the login one 24, which is expected when the PATH work lives in `.zshrc`.

#### Duplicates and missing entries

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| zsh | `zsh -ic 'print -l $path' \| sort \| uniq -cd` | Any line, `warn`. Usually a file sourced twice | verified, ten duplicates |
| bash | `bash -ic 'echo "$PATH"' \| tr ':' '\n' \| sort \| uniq -cd` | Any line | verified, eight duplicates |
| zsh | `zsh -ic 'for d in $path; do [[ -d $d ]] \|\| print "not a directory: $d"; done'` | Any line. A directory that is gone, or an entry that names a file, which PATH ignores | verified, four, two of them files such as `/usr/bin/brave-browser-stable` |

#### Shadowed binaries

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| zsh | `zsh -ic 'for b in python python3 pip java node npm git ssh gpg docker; do whence -a $b; done'` | A tool resolving somewhere the owner did not choose. On the test machine `python3` resolved to `~/.pyenv/shims/python3` ahead of `/usr/bin/python3`, and `java` to SDKMAN ahead of `/usr/bin/java`. That is `ok` when `MACHINE.md` records it as the owner's choice and `warn` when it does not | verified |
| bash | `bash -ic 'type -a python3'` | Same | verified |

#### Which file sets what

| Applies to | Command | What it shows | Status |
|---|---|---|---|
| zsh | `zsh -x -ic exit 2>&1 \| grep -E 'PATH='` | Every PATH assignment, prefixed with the file and line, for example `+/home/<user>/<config-dir>/env.sh:41> export PATH=...` | verified |
| bash | `PS4='+${BASH_SOURCE}:${LINENO}: ' bash -x -ic exit 2>&1 \| grep -E 'PATH='` | Same, with the file and line from `PS4` | verified |
| systemd user session | `systemctl --user show-environment \| grep -c '^PATH='` | Whether the graphical session carries a PATH of its own, set through `environment.d`. Print the count or the names, not the value, in the report | verified |
| all | `ls /etc/profile.d/ ~/.config/environment.d/ 2>/dev/null` | Files every login shell or the session reads | verified |

A trace with `-x` runs the startup files, which is what an interactive shell does anyway, and changes nothing.

With a systemd user session and zsh as the login shell, continue with [linux-zsh-environment.md](linux-zsh-environment.md).

---

### Packages

Pending and partial upgrades, configuration files the package manager left beside the live ones, orphans and cache size are in the file for the machine's package manager: [pacman.md](pacman.md) for Arch and CachyOS, [apt.md](apt.md) for Debian and Ubuntu, [dnf.md](dnf.md) for Fedora. Nothing here installs, upgrades, removes or cleans, including the tools' own cleanup commands. Two checks hold on every distribution:

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Flatpak updates | `flatpak remote-ls --updates` | Pending application or runtime updates | verified |
| Snap updates | `snap refresh --list` | Anything but `All snaps up to date.` | verified |

---

### Devices and network

GPU driver, displays and the refresh rate actually applied, audio devices, network and firewall state, time sync and the dual boot clock.

#### GPU driver

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `lspci -nnk \| grep -A3 -E 'VGA\|3D\|Display'` | `Kernel driver in use` missing, or a fallback driver such as `nouveau` or `simpledrm` where the baseline had the vendor driver, `fail` | verified, `nvidia` |
| NVIDIA | `cat /proc/driver/nvidia/version` and `nvidia-smi --query-gpu=name,driver_version,pstate --format=csv` | The kernel module version differs from the user space version, which happens after an upgrade without a reboot and makes `nvidia-smi` fail, `fail` | verified, both versions matched on the test machine |
| AMD or Intel | `glxinfo -B` or `vulkaninfo --summary` where installed | Renderer `llvmpipe`, which is software rendering, `fail` | UNVERIFIED |

On Arch and CachyOS, also run the GPU driver package row in [pacman.md](pacman.md).

#### Displays

On KDE Plasma, compare the current mode with the highest refresh at the same resolution:

```bash
kscreen-doctor -j | python3 -c "import json,sys; d=json.load(sys.stdin); [print(o['name'], cur['size']['width'], cur['size']['height'], round(cur['refreshRate'], 2), 'max', round(max(m['refreshRate'] for m in o['modes'] if m['size'] == cur['size']), 2)) for o in d['outputs'] if o['enabled'] for cur in [next(m for m in o['modes'] if m['id'] == o['currentModeId'])]]"
```

Executed on the test machine, it printed one line per enabled output in the form `<output> <width> <height> <refresh> max <max-refresh>`. A line such as `HDMI-A-1 2560 1440 60 max 75.0`, a sample and not a measured value, is a `warn`: the monitor offers 75 Hz at its native resolution and runs at 60.

Confirm the monitor's own limit from its EDID, which works unprivileged:

```bash
edid-decode /sys/class/drm/card1-HDMI-A-1/edid
```

Read `Display Product Name` and the `Display Range Limits` line. On the test machine it printed the model name as `'<model>'` and a range line of the form `Monitor ranges (GTF): <min>-<max> Hz V`. List the connectors with `ls /sys/class/drm/`, the card number differs between machines.

| Desktop | Command | Status |
|---|---|---|
| X11 | `xrandr --query`, where `*` marks the current mode and `+` the preferred one | UNVERIFIED |
| GNOME on Wayland | `gdbus call --session --dest org.gnome.Mutter.DisplayConfig --object-path /org/gnome/Mutter/DisplayConfig --method org.gnome.Mutter.DisplayConfig.GetCurrentState` | UNVERIFIED |
| wlroots compositors | `wlr-randr` | UNVERIFIED |

The verdict for a display below its maximum refresh is in [judging.md](judging.md).

#### Audio devices

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| PipeWire | `wpctl status` | No sinks, a `Dummy Output` sink, which means no card was found, or a default sink (marked `*`) other than the one `MACHINE.md` names, for example a monitor's HDMI output without speakers | verified |
| all | `cat /proc/asound/cards` | A card from the baseline missing | verified |
| all | `systemctl --user is-active pipewire pipewire-pulse wireplumber` | Any of them not `active` | verified |

#### Network and firewall

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `ip -br addr` | The primary interface `DOWN` or without an address, an interface from the baseline missing | verified |
| all | `nmcli -t -f NAME,TYPE,DEVICE,ACTIVE connection show --active` | No active connection on the interface the baseline uses | verified |
| all | `resolvectl status` and `ls -l /etc/resolv.conf` | `resolv.conf` no longer the link the baseline recorded, a DNS server nobody configured. `resolv.conf mode: foreign` means something other than systemd-resolved writes the file | verified |
| all | `systemctl is-active ufw firewalld nftables` | None `active`, `fail`, or two firewalls active at once, `warn` | verified, `ufw` active |
| all | `sudo ufw status verbose` or `sudo nft list ruleset` | Rules need root, so they go to Needs root | verified root only: `ufw status` printed `ERROR: You need to be root to run this script` |

#### Time sync

| Applies to | Command | Wrong looks like | Status |
|---|---|---|---|
| all | `timedatectl show -p NTPSynchronized -p LocalRTC -p Timezone` | `NTPSynchronized=no`, `fail`. `LocalRTC=yes` on a machine that does not dual boot with Windows, `warn` | verified, `yes` and `no` |
| all | `timedatectl timesync-status` | No server, or a stratum of 16 | verified, with `systemd-timesyncd` |
| all | `systemctl is-active systemd-timesyncd chronyd ntpd` | None active | verified |

On a machine that dual boots with Windows, read `LocalRTC` against the dual boot clock rule in [judging.md](judging.md).

---

### Security baseline

Firewall, Secure Boot, disk encryption and pending security updates in one view, so the owner sees the machine's posture on one screen. Most rows point at a check described in full above.

| Area | Command | Wrong looks like | Status |
|---|---|---|---|
| Firewall | the firewall rows under Network and firewall above | Off, `fail` | verified |
| Secure Boot | `bootctl status` | Read the `Secure Boot:` line. `disabled` is the owner's decision and becomes `accepted` once recorded, `disabled (setup)` means the firmware is in setup mode with no platform key enrolled | verified, `disabled (setup)` |
| Secure Boot | `od -An -t u1 /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c` | The last byte is 1 when enabled and 0 when disabled. Use it when `bootctl` is absent | verified, last byte `0` |
| Secure Boot | `mokutil --sb-state` | Same answer, only where `mokutil` is installed, usual on Debian, Ubuntu and Fedora | UNVERIFIED, absent on the test machine |
| Platform | `fwupdmgr security` | The Host Security ID and each failed test. A drop in HSI level since the baseline is `warn`. Runs unprivileged | verified, fwupd 2 printed `HSI:0!` |
| Firmware updates | `fwupdmgr get-updates` | Pending firmware updates. It reads the metadata already downloaded, never run `fwupdmgr refresh` or `update` | UNVERIFIED |
| Disk encryption | the rows under Encryption state above | A volume the owner expects encrypted is not | verified |
| Pending security updates | the row in the file for the machine's package manager, [pacman.md](pacman.md), [apt.md](apt.md) or [dnf.md](dnf.md) | see that file | see that file |

#### Reading the HSI result

`fwupdmgr security` prints passed and failed tests grouped by level. A failed test is not automatically a fault: on the test machine `Supported CPU: Unknown`, `CET Platform: Not supported` and `Hardware disk encryption: Not supported` are properties of a 2018 desktop that no setting changes. Record the failed tests in the baseline once, mark the ones that are hardware limits as `accepted` after the owner agrees, and report only tests that changed state on later runs. Never change a firmware setting to raise the level, that is the owner's decision at the firmware setup screen.

What goes to the owner for a security finding is in [judging.md](judging.md).
