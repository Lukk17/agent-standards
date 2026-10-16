---
name: cachyos
description: 'CachyOS specific administration on top of Arch: linux-cachyos kernel flavors and switching, kerver, cachyos-kernel-manager, the x86-64-v3 and v4 optimized repositories and pacman.conf order, cachyos-mirrorlist and cachyos-rate-mirrors, chwd hardware profiles, the prebuilt NVIDIA module packages, scx_loader and sched-ext, ananicy-cpp, power-profiles-daemon, game-performance, zram and cachyos-settings, the Limine bootloader with limine-snapper-sync and limine-mkinitcpio, snapshot boot entries, cachy-chroot recovery, cachyos-kde-settings and the login manager. Use when you say "switch to the bore kernel", "should I use the v4 repos", "chwd", "black screen after the nvidia update", "enable scx_lavd", "change the kernel command line", "restore a snapshot from the boot menu", or "the system will not boot". Not for generic pacman, AUR, snapper, journal or audio work, use `arch-linux`, and not for Plasma panels or themes, use `kde-plasma`.'
---

# CachyOS Administration

CachyOS is a rolling Arch derivative with its own kernels, repositories rebuilt for newer CPU instruction sets, a tuned settings package and its own tools. The Arch Wiki is still the background, but where it and CachyOS differ, what the CachyOS packages ship on the machine wins. Read the `arch-linux` skill as well, because every generic package, snapshot and journal rule applies here unchanged.

Baseline: CachyOS with Limine 12 and snapper, verified on one host on 2026-10-13. Commands that were not executed are marked UNVERIFIED in the topic files.

| You are about to | Open |
|---|---|
| Edit `/etc/pacman.conf`, add or change a CachyOS repository, rank mirrors, consider v4 or znver4 | [repos-v3.md](references/repos-v3.md) |
| Install, switch, remove or upgrade a kernel, use `kerver` | [kernel.md](references/kernel.md) |
| Touch the NVIDIA driver, run `chwd`, change the GPU, fix a black screen after an upgrade | [hardware-nvidia.md](references/hardware-nvidia.md) |
| Change the scheduler, `scx_loader`, `ananicy-cpp`, the power profile, sysctl, zram, the I/O scheduler | [performance.md](references/performance.md) |
| Touch the bootloader, the kernel command line, snapshot boot entries, recover from a live ISO | [boot-limine.md](references/boot-limine.md) |
| Change something a `cachyos-*-settings` package owns, the login manager, `/etc/skel` | [desktop-defaults.md](references/desktop-defaults.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`: the CPU and its ISA level, the GPU and driver packaging, installed kernels, the bootloader and its command line, disks that must never be touched, and the change log. Read it before acting. This skill holds no facts about any single machine. Discover them with the commands in the topic files and compare with `MACHINE.md`.

---

### When to activate

- A question about a `linux-cachyos*` kernel, its modules or its headers
- An edit to `/etc/pacman.conf` or a CachyOS mirrorlist
- `chwd`, a GPU driver change, or a display that broke after an upgrade
- `scx_loader`, `ananicy-cpp`, `power-profiles-daemon`, zram or a sysctl from `cachyos-settings`
- Limine, `/etc/default/limine`, snapshot boot entries, or a machine that does not boot
- `cachyos-kde-settings`, `/etc/skel`, or the login manager

---

### When not to activate

- Generic pacman, AUR, `.pacnew`, cleanup, snapper, journal, crash or audio work, use `arch-linux`
- Plasma panels, widgets, KWin, shortcuts, themes or konsave, use `kde-plasma`
- Provisioning a CachyOS host reproducibly, use `ansible`

---

### Hard rules

1. This is not vanilla Arch. Check what a CachyOS package owns with `pacman -Qo` before applying an Arch Wiki recipe.
2. Never edit shipped files under `/usr/lib` or `/usr/share`. Override in `/etc` or `~`, as the `arch-linux` skill describes.
3. Keep the CachyOS repositories above `[core]` in `pacman.conf`, and never replace the file with its `.pacnew`.
4. Never add `nvidia-dkms`, `nvidia-open-dkms` or another driver set by hand on top of a prebuilt `linux-cachyos*-nvidia*` module package.
5. Keep a second known good kernel installed and bootable at all times.
6. Do not add third party pacman repositories, including ones that offer agent skill packages.
7. The agent does not run `sudo`, and every root step goes to the owner with what it changes.

---

### Related skills

- `arch-linux` owns pacman, the AUR, snapshots, the journal, crash diagnosis, audio and safe configuration
- `kde-plasma` owns the Plasma desktop that `cachyos-kde-settings` seeds
- `ansible` owns provisioning the same state reproducibly

---

### Checklist

- [ ] `MACHINE.md` read, and the CPU ISA level, GPU, kernels and bootloader discovered or confirmed
- [ ] A snapshot taken before any kernel, driver, bootloader or initramfs change
- [ ] Kernel, headers and module package installed or removed as one flavor set
- [ ] A fallback kernel still installed and listed in the boot menu
- [ ] No hand-installed DKMS driver on top of a prebuilt module
- [ ] Boot options changed in `/etc/default/limine`, never in the generated `limine.conf`
- [ ] The change and its undo recorded in the `MACHINE.md` change log
