# dnf: Fedora Checks

The checks that need dnf or rpm, for a machine that runs Fedora. The rules live in [SKILL.md](../SKILL.md), and every other Linux check is in [linux.md](linux.md). No command here was executed, so every row is UNVERIFIED. Nothing here installs, upgrades, removes or cleans, including the tools' own cleanup commands.

---

### Packages

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Pending updates | `dnf check-update` | Exit code 100 means updates exist, 0 none | UNVERIFIED |
| Dependency problems | `dnf check` | Any output, `fail` | UNVERIFIED |
| Configuration leftovers | `find /etc \( -name '*.rpmnew' -o -name '*.rpmsave' \) 2>/dev/null` | Any file, `warn` | UNVERIFIED |
| Orphans | `dnf repoquery --unneeded` | Packages nothing needs | UNVERIFIED |
| Reboot owed | `dnf needs-restarting -r` | Says a reboot is needed | UNVERIFIED |

---

### Rows other checks point at

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Microcode package | `rpm -q microcode_ctl linux-firmware` | No microcode package installed, or the package was updated after the current boot, which means a reboot is owed | UNVERIFIED |
| Pending security updates | `dnf updateinfo list --security` | Any line, `warn` | UNVERIFIED |
