# Kernels

Read this before installing, switching, removing or rolling back a kernel, and when the running kernel does not match the installed package. The rules live in [SKILL.md](../SKILL.md).

---

### Discover what is installed and running

```bash
uname -r
```

```bash
pacman -Q | grep -E '^linux-cachyos'
```

```bash
ls /usr/lib/modules
```

1. `uname -r` is the running release. `pacman -Q linux-cachyos` (or the installed flavor) is the installed package. After an upgrade, a mismatch between the two means a reboot is needed. `kerver` prints the running kernel's build string where installed.
2. Each kernel normally comes with `-headers` and, on NVIDIA machines, a matching `-nvidia-open` or `-nvidia` module package. List the full set per flavor.
3. sched-ext support: `zgrep CONFIG_SCHED_CLASS_EXT /proc/config.gz` and `cat /sys/kernel/sched_ext/state`, which reads `disabled` when no scx scheduler is loaded.
4. Every installed kernel should have a boot menu entry, built by the bootloader hooks, see [boot-limine.md](boot-limine.md).

Record the default kernel and the fallback in `MACHINE.md`.

---

### The flavors

Listed with `pacman -Ssq '^linux-cachyos'` on 2026-10-13. Each flavor also has `-headers`, NVIDIA module and `-zfs` packages, and most have `-lto` and `-r8125` siblings. Read `pacman -Si <pkg>` for the current description, because the default scheduler has changed over time and older web pages disagree.

| Package | What it is | Typical use |
|---|---|---|
| `linux-cachyos` | the default kernel | keep as the main kernel |
| `linux-cachyos-lts` | long term kernel | keep as the fallback |
| `linux-cachyos-bore`, `-eevdf`, `-bmq`, `-cacule`, `-gcc` | other schedulers or toolchains | only for a stated experiment |
| `linux-cachyos-server` | server tuning | servers |
| `linux-cachyos-rt-bore` | realtime | latency critical audio or control work, it lowers throughput and does not make games faster |
| `linux-cachyos-hardened` | hardened configuration | security focused machines |
| `linux-cachyos-deckify` | handheld devices | Steam Deck class hardware |
| `linux-cachyos-rc` | mainline release candidates | testing only |
| `*-r8125` | the same kernel with the Realtek r8125 driver built in | only a machine with that NIC |

From the CachyOS documentation, not tested here: `bmq` and `hardened` do not support sched-ext, so never load an scx scheduler on them.

---

### Switch or add a kernel

1. Snapshot first. The pacman pre and post pair is not enough, because the bootloader and `/boot` are involved.
2. Upgrade first: `sudo pacman -Syu`.
3. Install the new kernel with its headers and the matching module package, all of one flavor, for example `sudo pacman -S linux-cachyos-<flavor> linux-cachyos-<flavor>-headers linux-cachyos-<flavor>-nvidia-open`. Never remove the running kernel or the fallback in the same step. `cachyos-kernel-manager` does the same through a GUI, and the owner may prefer it.
4. Check that the initramfs and the boot entry were built: the pacman output shows the mkinitcpio and bootloader hooks, and `ls /usr/lib/modules` shows the new module directory. `/boot` may need root to list.
5. Reboot, choose the new kernel in the boot menu, then verify `uname -r`, `systemctl --failed`, and the GPU driver (for NVIDIA, `nvidia-smi`).
6. Only after it has run well for a while, remove the unwanted kernel together with its headers and module package. Never leave the machine with a single kernel.

---

### Modules must match the kernel

A prebuilt module package such as `linux-cachyos-nvidia-open` depends on exactly one kernel version. Check with `pacman -Qi linux-cachyos-nvidia-open | grep 'Depends On'`. pacman moves the pair together as long as both are upgraded. A kernel booted without its matching module shows up as a black screen, or a session that falls back to software rendering. If an upgrade ever holds back one half of the pair, for example a mirror carries the kernel but not yet the module, do not reboot. Finish the upgrade first, as the `arch-linux` skill describes for partial upgrades.

---

### Do not

1. Edit anything under `/usr/lib/modules/`.
2. Install `rt-bore` or `hardened` to "improve" performance.
3. Remove the fallback kernel to save space. It is the way back when a new kernel misbehaves.
4. Change the kernel command line in files under `/boot`, see [boot-limine.md](boot-limine.md).
