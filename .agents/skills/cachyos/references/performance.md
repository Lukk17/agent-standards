# Performance Stack

Read this before changing the CPU scheduler, `scx_loader`, `ananicy-cpp`, the power profile, sysctl values, zram or the I/O scheduler, or when someone proposes "tweaks". The rules live in [SKILL.md](../SKILL.md).

Measure first, change one layer, keep the change in a drop-in file, write it down. CachyOS ships tuned defaults, so a change needs a symptom or a measured goal.

---

### Discover each layer

| Layer | How to look |
|---|---|
| In-kernel scheduler | `pacman -Si <kernel package>` description, `zgrep -E 'CONFIG_HZ=\|CONFIG_SCHED_CLASS_EXT\|CONFIG_PREEMPT' /proc/config.gz` |
| sched-ext | `cat /sys/kernel/sched_ext/state`, `systemctl status scx_loader`, `pacman -Q scx-scheds scx-tools` |
| ananicy-cpp | `systemctl status ananicy-cpp`, rules from `cachyos-ananicy-rules` |
| Power profiles | `powerprofilesctl list`, `powerprofilesctl get`, `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` |
| game-performance | `cat /usr/bin/game-performance`, which wraps a command in `powerprofilesctl launch -p performance` |
| zram | `zramctl`, `swapon --show`, generator configuration in `/usr/lib/systemd/zram-generator.conf` |
| I/O scheduler | `cat /sys/block/<dev>/queue/scheduler`, rules in `/usr/lib/udev/rules.d/60-ioschedulers.rules` |
| Memory sysctl | `sysctl vm.swappiness vm.vfs_cache_pressure vm.dirty_bytes vm.dirty_background_bytes vm.page-cluster`, from `/usr/lib/sysctl.d/70-cachyos-settings.conf` |
| gamemode | `pacman -Q gamemode` |

High swappiness is intentional with zram, because swapping to compressed RAM is cheap. Record the current state in `MACHINE.md` before changing anything.

---

### How the pieces interact

1. `ananicy-cpp` changes nice values and I/O classes of known processes by rule. CachyOS says it is usually compatible with sched-ext schedulers, so do not disable it preemptively. If a scx scheduler stalls or the desktop hitches after enabling one, disabling Ananicy is a troubleshooting step with the owner's approval: `sudo systemctl disable --now ananicy-cpp`, undone with `enable --now`.
2. `gamemode` also changes priorities and overlaps with Ananicy. Do not add it casually.
3. `game-performance` only helps when `powerprofilesctl list` offers a `performance` profile. Where only `balanced` and `power-saver` exist, it runs the command unchanged, so do not recommend it as a speed-up there.
4. Third party notes say the CachyOS `power-profiles-daemon` switches `scx_loader` modes together with the power profile. UNVERIFIED.

---

### Enabling a sched-ext scheduler

Only when the owner wants to experiment.

1. State the goal and the way back first. The way back is `sudo systemctl disable --now scx_loader` and a reboot.
2. Test without persistence: `sudo scx_lavd`, or another binary from `pacman -Ql scx-scheds | grep /usr/bin/`. Ctrl+C returns to the kernel scheduler. `cat /sys/kernel/sched_ext/state` reads `enabled` while it runs.
3. To persist, copy the shipped file and edit the copy: `sudo mkdir -p /etc/scx_loader`, `sudo cp /usr/share/scx_loader/config.toml /etc/scx_loader/config.toml`, set `default_sched` and `default_mode`, then `sudo systemctl enable --now scx_loader.service`. Never edit `/usr/share/scx_loader/config.toml`.
4. Check with `systemctl status scx_loader`, `journalctl -u scx_loader -b` and `scxctl get` from `scx-tools`.
5. Not on kernels without sched-ext, see [kernel.md](kernel.md).
6. Measure before and after with something that reflects the workload, such as frame times in the game that stutters. A synthetic win the owner cannot feel is not a reason to keep it.

UNVERIFIED as a sequence on any machine.

---

### Overriding sysctl, udev, modprobe and zram

1. sysctl: a new file `/etc/sysctl.d/99-local.conf`, applied with `sudo sysctl --system`, verified with `sysctl <key>`.
2. udev: a new file in `/etc/udev/rules.d/` with a number above the one it overrides, then `sudo udevadm control --reload` and `sudo udevadm trigger`. Snapshot first if the change touches the root disk.
3. zram: `/etc/systemd/zram-generator.conf` or a file in `/etc/systemd/zram-generator.conf.d/`, never the file in `/usr/lib/systemd/`.
4. modprobe: `/etc/modprobe.d/`, followed by an initramfs rebuild when the module loads early.

---

### Not recommended

1. Switching to `rt-bore` or `hardened` for speed.
2. `mitigations=off` or other kernel parameters copied from forum posts. The command line affects boot, see [boot-limine.md](boot-limine.md).
3. Cargo cult sysctl lists. `cachyos-settings` already carries a tuned set.
4. Changing the I/O scheduler of the root disk without a measurement.
