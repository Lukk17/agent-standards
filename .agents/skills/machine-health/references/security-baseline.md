# Security Baseline

Firewall, Secure Boot, disk encryption and pending security updates in one view, so the owner sees the machine's posture on one screen. The rules live in [SKILL.md](../SKILL.md). Most rows point at a check described in full elsewhere. Linux commands below were executed read-only on CachyOS on 2026-10-13, macOS and Windows commands are UNVERIFIED.

---

### Checks

| Area | OS | Command | Wrong looks like | Status |
|---|---|---|---|---|
| Firewall | all | see [devices-and-network.md](devices-and-network.md) | Off, `fail` | Linux verified |
| Secure Boot | Linux | `bootctl status` | Read the `Secure Boot:` line. `disabled` is the owner's decision and becomes `accepted` once recorded, `disabled (setup)` means the firmware is in setup mode with no platform key enrolled | verified, `disabled (setup)` |
| Secure Boot | Linux | `od -An -t u1 /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c` | The last byte is 1 when enabled and 0 when disabled. Use it when `bootctl` is absent | verified, last byte `0` |
| Secure Boot | Linux | `mokutil --sb-state` | Same answer, only where `mokutil` is installed, usual on Debian, Ubuntu and Fedora | UNVERIFIED, absent on the test machine |
| Platform | Linux | `fwupdmgr security` | The Host Security ID and each failed test. A drop in HSI level since the baseline is `warn`. Runs unprivileged | verified, fwupd 2.1.8 printed `HSI:0!` |
| Firmware updates | Linux | `fwupdmgr get-updates` | Pending firmware updates. It reads the metadata already downloaded, never run `fwupdmgr refresh` or `update` | UNVERIFIED |
| Secure Boot | Windows | `Confirm-SecureBootUEFI` | Elevated only, goes to Needs root | UNVERIFIED |
| Secure Boot | macOS | `csrutil status` for System Integrity Protection. Apple silicon boot policy needs `sudo bputil -d`, which goes to Needs root | `disabled` SIP, `warn` | UNVERIFIED |
| Disk encryption | all | see [storage.md](storage.md) | A volume the owner expects encrypted is not | Linux verified |
| Gatekeeper | macOS | `spctl --status` | `assessments disabled`, `warn` | UNVERIFIED |
| Antivirus | Windows | `Get-MpComputerStatus \| Select-Object AMServiceEnabled, RealTimeProtectionEnabled, AntivirusSignatureLastUpdated` | Real time protection off, or signatures older than a week | UNVERIFIED |
| Pending security updates | Arch | `arch-audit -u` | Packages with a known vulnerability and a fixed version available. Only where `arch-audit` is installed. Otherwise report every pending update from `checkupdates`, since Arch marks none as security | UNVERIFIED, absent on the test machine |
| Pending security updates | Debian | `apt list --upgradable 2>/dev/null \| grep -i security` | Any line, `warn` | UNVERIFIED |
| Pending security updates | Fedora | `dnf updateinfo list --security` | Any line, `warn` | UNVERIFIED |
| Pending security updates | macOS | `softwareupdate --list` | A security response or a point release | UNVERIFIED |
| Pending security updates | Windows | the Windows Update query in [packages.md](packages.md) | A security or cumulative update | UNVERIFIED |

---

### Reading the HSI result

`fwupdmgr security` prints passed and failed tests grouped by level. A failed test is not automatically a fault: on the test machine `Supported CPU: Unknown`, `CET Platform: Not supported` and `Hardware disk encryption: Not supported` are properties of a 2018 desktop that no setting changes. Record the failed tests in the baseline once, mark the ones that are hardware limits as `accepted` after the owner agrees, and report only tests that changed state on later runs. Never change a firmware setting to raise the level, that is the owner's decision at the firmware setup screen.

---

### What to hand the owner

Security findings go first in the reply, before performance and tidiness. For each one say what an attacker or a failure gains while it stays, what the fix changes, and whether it needs a reboot or a firmware visit. Turning Secure Boot on, enrolling keys or enabling BitLocker or FileVault can lock the owner out of an operating system or a disk when done in the wrong order, so the suggestion names the OS skill that carries the procedure, `arch-linux`, `cachyos`, `windows` or `macos`, rather than a one-line command.
