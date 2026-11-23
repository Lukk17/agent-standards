# Scope

Companion reference for the [cachyos](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

CachyOS administration on top of Arch: linux-cachyos kernels, the x86-64-v3 and v4 repositories, chwd and NVIDIA modules, sched-ext schedulers, cachyos-settings, and Limine with snapshot boot entries.

- A question about a `linux-cachyos*` kernel, its modules or its headers
- An edit to `/etc/pacman.conf` or a CachyOS mirrorlist
- `chwd`, a GPU driver change, or a display that broke after an upgrade
- `scx_loader`, `ananicy-cpp`, `power-profiles-daemon`, zram or a sysctl from `cachyos-settings`
- Limine, `/etc/default/limine`, snapshot boot entries, or a machine that does not boot
- `cachyos-kde-settings`, `/etc/skel`, or the login manager
- Also covers linux-cachyos kernel flavors and switching, kerver, cachyos-kernel-manager, the x86-64-v3 and v4 optimized repositories and pacman.conf order, cachyos-mirrorlist and cachyos-rate-mirrors, chwd hardware profiles, the prebuilt NVIDIA module packages, scx_loader and sched-ext, ananicy-cpp, power-profiles-daemon, game-performance, zram and cachyos-settings, the Limine bootloader with limine-snapper-sync and limine-mkinitcpio, snapshot boot entries, cachy-chroot recovery, cachyos-kde-settings and the login manager
- The user says "switch to the bore kernel", "should I use the v4 repos", "black screen after the nvidia update", "the system will not boot", "chwd", "enable scx_lavd", "change the kernel command line" or "restore a snapshot from the boot menu"

---

### When not to activate

- Generic pacman, AUR, `.pacnew`, cleanup, snapper, journal, crash or audio work, use `arch-linux`
- Plasma panels, widgets, KWin, shortcuts, themes or konsave, use `kde-plasma`
- Provisioning a CachyOS host reproducibly, use `ansible`

---

### Related skills

- `arch-linux` owns pacman, the AUR, snapshots, the journal, crash diagnosis, audio and safe configuration
- `kde-plasma` owns the Plasma desktop that `cachyos-kde-settings` seeds
- `ansible` owns provisioning the same state reproducibly
