---
name: cachyos
description: 'CachyOS administration: kernels, v3 and v4 repositories, NVIDIA, sched-ext, Limine. Use when the user says "black screen after the nvidia update" or "switch to the bore kernel". Not for plain pacman, use `arch-linux`.'
metadata:
  version: "1.1.0"
---

# CachyOS Administration

CachyOS is a rolling Arch derivative with its own kernels, repositories rebuilt for newer CPU instruction sets, a tuned settings package and its own tools. The Arch Wiki is still the background, but where it and CachyOS differ, what the CachyOS packages ship on the machine wins. Read the `arch-linux` skill as well, because every generic package, snapshot and journal rule applies here unchanged.

Written for CachyOS with Limine and snapper.

The commands that ran were run on one CachyOS host, and commands that were not executed are marked UNVERIFIED in the topic files.

| You are about to | Open |
|---|---|
| Edit `/etc/pacman.conf`, add or change a CachyOS repository, rank mirrors, consider v4 or znver4 | [repos-v3.md](references/repos-v3.md) |
| Install, switch, remove or upgrade a kernel, use `kerver` | [kernel.md](references/kernel.md) |
| Touch the NVIDIA driver, run `chwd`, change the GPU, fix a black screen after an upgrade | [hardware-nvidia.md](references/hardware-nvidia.md) |
| Change the scheduler, `scx_loader`, `ananicy-cpp`, the power profile, sysctl, zram, the I/O scheduler | [performance.md](references/performance.md) |
| Touch the bootloader, the kernel command line, snapshot boot entries, recover from a live ISO | [boot-limine.md](references/boot-limine.md) |
| Change something a `cachyos-*-settings` package owns, the login manager, `/etc/skel` | [desktop-defaults.md](references/desktop-defaults.md) |
| Finish a kernel, driver, repository or boot change | [checklist.md](references/checklist.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`. Read it before acting. This skill holds no facts about any single machine.

For this skill they are the CPU and its ISA level, the GPU and driver packaging, installed kernels, the bootloader and its command line, disks that must never be touched, and the change log. Discover them with the commands in the topic files and compare with `MACHINE.md`.

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
