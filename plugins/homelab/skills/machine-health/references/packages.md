# Packages

Pending and partial upgrades, configuration files the package manager left beside the live ones, orphans and cache size. The rules live in [SKILL.md](../SKILL.md). Arch and CachyOS commands below were executed read-only with pacman-contrib, Debian, Fedora, macOS and Windows commands are UNVERIFIED. Nothing here installs, upgrades, removes or cleans, including the tools' own cleanup commands.

---

### Arch and CachyOS

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
| Flatpak updates | `flatpak remote-ls --updates` | Pending application or runtime updates | verified |
| Snap updates | `snap refresh --list` | Anything but `All snaps up to date.` | verified |

A partial upgrade on Arch is installing one package with `pacman -Sy <package>` instead of upgrading the whole system. Its signs are the kernel line above, a library error such as `error while loading shared libraries` in the journal, and `checkupdates` listing core libraries the owner thought were current. Report it, and leave the full upgrade to the owner under `arch-linux` or `cachyos`.

---

### Debian and Ubuntu

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Pending updates | `apt list --upgradable` | Reads the local lists, which are as old as the last `apt update` the owner ran. Say how old they are: `ls -l --time-style=long-iso /var/lib/apt/lists/*_InRelease` | UNVERIFIED |
| Half installed packages | `dpkg --audit` | Any output, `fail` | UNVERIFIED |
| Kept back or broken | `apt-get -s dist-upgrade` | Packages kept back or a dependency problem. `-s` simulates and changes nothing | UNVERIFIED |
| Configuration leftovers | `find /etc \( -name '*.dpkg-dist' -o -name '*.dpkg-old' -o -name '*.dpkg-new' -o -name '*.ucf-dist' \) 2>/dev/null` | Any file, `warn` | UNVERIFIED |
| Orphans | `apt-get -s autoremove` | Packages that would go | UNVERIFIED |
| Reboot owed | `test -f /var/run/reboot-required && cat /var/run/reboot-required.pkgs` | The file exists, `warn` | UNVERIFIED |

---

### Fedora

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Pending updates | `dnf check-update` | Exit code 100 means updates exist, 0 none | UNVERIFIED |
| Dependency problems | `dnf check` | Any output, `fail` | UNVERIFIED |
| Configuration leftovers | `find /etc \( -name '*.rpmnew' -o -name '*.rpmsave' \) 2>/dev/null` | Any file, `warn` | UNVERIFIED |
| Orphans | `dnf repoquery --unneeded` | Packages nothing needs | UNVERIFIED |
| Reboot owed | `dnf needs-restarting -r` | Says a reboot is needed | UNVERIFIED |

---

### macOS

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Homebrew health | `brew doctor` | Any warning other than ones the baseline accepted | UNVERIFIED |
| Outdated formulae and casks | `HOMEBREW_NO_AUTO_UPDATE=1 brew outdated --greedy` | The variable stops `brew` updating its own metadata first, so the check stays read-only and reports against the last update | UNVERIFIED |
| Missing dependencies | `brew missing` | Any output | UNVERIFIED |
| What cleaning would free | `brew cleanup --dry-run` and `brew autoremove --dry-run` | Large totals, `warn` | UNVERIFIED |
| System updates | `softwareupdate --list` | Any pending update, a security response or a point release is `warn` | UNVERIFIED |
| App Store updates | `mas outdated` | Any line | UNVERIFIED |

---

### Windows

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| winget | `winget upgrade --include-unknown` | Pending upgrades. The list includes apps winget did not install, compare with `MACHINE.md` before suggesting winget for one | UNVERIFIED |
| Chocolatey | `choco outdated` | Pending upgrades | UNVERIFIED |
| Scoop, only where installed | `scoop status` | Pending upgrades | UNVERIFIED |
| Reboot owed | `Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'` | `True`, `warn` | UNVERIFIED |
| Windows Update pending | `(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search('IsInstalled=0 and IsHidden=0').Updates \| Select-Object Title` | Any security or cumulative update, `warn`. Never install a module such as PSWindowsUpdate to answer this | UNVERIFIED |

The install order and which manager owns which app live in `windows`. A suggested upgrade goes through the manager that already owns the app.
