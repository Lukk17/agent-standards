# apt: Debian and Ubuntu Checks

The checks that need apt or dpkg, for a machine that runs Debian or Ubuntu. The rules live in [SKILL.md](../SKILL.md), and every other Linux check is in [linux.md](linux.md). No command here was executed, so every row is UNVERIFIED. Nothing here installs, upgrades, removes or cleans, including the tools' own cleanup commands.

---

### Packages

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Pending updates | `apt list --upgradable` | Reads the local lists, which are as old as the last `apt update` the owner ran. Say how old they are: `ls -l --time-style=long-iso /var/lib/apt/lists/*_InRelease` | UNVERIFIED |
| Half installed packages | `dpkg --audit` | Any output, `fail` | UNVERIFIED |
| Kept back or broken | `apt-get -s dist-upgrade` | Packages kept back or a dependency problem. `-s` simulates and changes nothing | UNVERIFIED |
| Configuration leftovers | `find /etc \( -name '*.dpkg-dist' -o -name '*.dpkg-old' -o -name '*.dpkg-new' -o -name '*.ucf-dist' \) 2>/dev/null` | Any file, `warn` | UNVERIFIED |
| Orphans | `apt-get -s autoremove` | Packages that would go | UNVERIFIED |
| Reboot owed | `test -f /var/run/reboot-required && cat /var/run/reboot-required.pkgs` | The file exists, `warn` | UNVERIFIED |

---

### Rows other checks point at

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Microcode package | `dpkg -l amd64-microcode intel-microcode` | No microcode package installed, or the package was updated after the current boot, which means a reboot is owed | UNVERIFIED |
| Pending security updates | `apt list --upgradable 2>/dev/null \| grep -i security` | Any line, `warn` | UNVERIFIED |
