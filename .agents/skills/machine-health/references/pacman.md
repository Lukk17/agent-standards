# pacman: Arch and CachyOS Checks

The checks that need pacman, for a machine that runs Arch or CachyOS: pending and partial upgrades, configuration files the package manager left beside the live ones, orphans and cache size, plus the microcode, GPU driver, memory test and security update rows that name a package. The rules live in [SKILL.md](../SKILL.md), and every other Linux check is in [linux.md](linux.md). The commands were executed read-only with pacman-contrib, unless a row says otherwise. Nothing here installs, upgrades, removes or cleans, including the tools' own cleanup commands.

---

### Packages

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Pending updates | `checkupdates` | A long list, or one the owner has not upgraded for weeks, `warn`. It syncs a temporary copy of the databases and leaves the system ones alone | verified, 7 pending |
| Do not use for pending updates | `pacman -Qu` | Reads the local sync databases, which are as old as the last `pacman -Sy`, so it answers 0 on a stale machine | verified, printed 0 while `checkupdates` printed 7 |
| Kernel installed but not booted | `test -d /usr/lib/modules/$(uname -r) && echo present` together with `uname -r` and `pacman -Q linux-cachyos` or `linux` | The running kernel's module directory is gone, which means the kernel was upgraded and the machine not rebooted, `warn`, and new modules will fail to load | verified, present |
| Database consistency | `pacman -Dk` | Anything but `No database errors have been found!` | verified |
| Configuration leftovers | `pacdiff -o` | Any `.pacnew` or `.pacsave` file, `warn`. Each one is a configuration the package changed that nobody merged | verified, six, including `pacman.conf.pacnew` and four mirrorlists |
| Configuration leftovers without pacman-contrib | `find /etc \( -name '*.pacnew' -o -name '*.pacsave' \) 2>/dev/null` | Same | verified |
| Orphans | `pacman -Qdtq` | Packages installed as dependencies that nothing needs now. A short list is `ok`, a growing one `warn`. Build dependencies often appear here by design | verified, 4 |
| Foreign packages | `pacman -Qm` | Count compared with the baseline. A package that moved from the AUR into the repositories still shows here until reinstalled | verified, 13 |
| AUR updates | `yay -Qua` or `paru -Qua` | Pending AUR updates, reported separately because they build locally | UNVERIFIED |
| Package cache | `du -sh /var/cache/pacman/pkg 2>/dev/null` | Many gigabytes, `warn`. Unprivileged `du` skips the root-owned `download-*` folders, so the number is a floor | verified, 5.9G |
| What cleaning would free | `paccache -dk1` and `paccache -duk0` | The dry runs print the candidates and the space without removing anything. The default `paccache -d` keeps three versions and can report no candidates | verified, 69 candidates and 78.23 MiB, then 1 uninstalled package |

A partial upgrade on Arch is installing one package with `pacman -Sy <package>` instead of upgrading the whole system. Its signs are the kernel line above, a library error such as `error while loading shared libraries` in the journal, and `checkupdates` listing core libraries the owner thought were current. Report it, and leave the full upgrade to the owner under `arch-linux` or `cachyos`.

---

### Rows other checks point at

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Microcode package | `pacman -Q amd-ucode intel-ucode` | No microcode package installed, or the package was updated after the current boot, which means a reboot is owed | verified |
| GPU driver package | `pacman -Q \| grep -E '^(nvidia\|linux.*nvidia)'` | A kernel without its matching prebuilt driver package, or a DKMS package with no module built for the running kernel | verified |
| Pending security updates | `arch-audit -u` | Packages with a known vulnerability and a fixed version available. Only where `arch-audit` is installed. Otherwise report every pending update from `checkupdates`, since Arch marks none as security | UNVERIFIED, absent on the test machine |

For the memory test in [linux.md](linux.md): on Arch and CachyOS the `extra` repository carries `memtest86+-efi`, read with `pacman -Si memtest86+-efi`. Installing it and adding a boot entry is a change under `arch-linux` or `cachyos`, not part of this check.
