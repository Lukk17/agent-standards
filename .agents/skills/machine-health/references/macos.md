# macOS Checks

Contents:

- [Before the first command](#before-the-first-command)
- [CPU](#cpu)
- [Memory](#memory)
- [Storage](#storage)
- [System errors](#system-errors)
- [Paths and environment](#paths-and-environment)
- [Packages](#packages)
- [Devices and network](#devices-and-network)
- [Security baseline](#security-baseline)

Every check for a machine that runs macOS, in run order. The rules live in [SKILL.md](../SKILL.md), and how a value becomes a verdict on any operating system is in [judging.md](judging.md). No command here was executed on a Mac, so every row is UNVERIFIED.

---

### Before the first command

1. Never run `sudo` or anything that asks for a password. A check that needs root goes into Needs root as `needs: sudo <command>`.
2. Never run `fsck` or another repair tool.
3. A device in the never-touch table gets listing level only, `diskutil list`.
4. List variable names and paths only, never the value of a variable that might hold a secret.

---

### CPU

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Model and microcode | `sysctl -n machdep.cpu.brand_string` | Model differs from `MACHINE.md`. Microcode arrives with macOS updates and is not inspectable | UNVERIFIED |
| Governor and power profile | `pmset -g` | Low Power Mode on when not expected | UNVERIFIED |
| Temperatures | `sudo powermetrics --samplers smc -n 1` | Needs root, so it goes to Needs root | UNVERIFIED |
| Throttling | `pmset -g therm` | A `CPU_Speed_Limit` below 100, or a recorded thermal warning level | UNVERIFIED |

---

### Memory

| Check | Command | What it gives | Status |
|---|---|---|---|
| Installed modules | `system_profiler SPMemoryDataType` | Per slot on Intel Macs. On Apple silicon the memory is in the package and there are no slots to compare | UNVERIFIED |

The configured speed is `Speed` per slot from `system_profiler` on an Intel Mac. The verdicts for configured speed, mixed kits and channels are in [judging.md](judging.md).

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Memory errors | none user visible | Use Apple Diagnostics below | not applicable |

The memory test for a Mac is Apple Diagnostics. Apple's page "Use Apple Diagnostics to test your Mac" says on Apple silicon "Press and hold the power button on your Mac", release at Options, then "Press and hold Command (⌘)-D", and on Intel "press and hold the D key on your keyboard as your Mac starts up" (<https://support.apple.com/en-us/102550>).

An Intel Mac that can boot it can run Memtest86+ instead. The project describes it as "a free, open-source, stand-alone memory tester for IA-32, x86-64, and LoongArch64 systems" that runs "directly by a PC BIOS (legacy or UEFI)" or "via an intermediate bootloader", from "a USB Flash Drive (FAT32 formatted)" (<https://www.memtest.org/>). Let it run at least one full pass, and treat a single error as `fail`. The agent never schedules either test, as [judging.md](judging.md) sets out.

---

### Storage

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| SMART and NVMe health | `diskutil info disk0` | `SMART Status` other than `Verified` | UNVERIFIED |
| Filesystem errors | `diskutil verifyVolume /` | Anything but a clean verdict. Verifying the boot volume may need root, if so list it | UNVERIFIED |
| Free space | `df -h /`, `diskutil apfs list` | Container free space below 10 percent | UNVERIFIED |
| Encryption state | `fdesetup status` | `FileVault is Off` where the owner expects it on | UNVERIFIED |

---

### System errors

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Faults in the last hour | `log show --last 1h --predicate 'messageType == fault' --style compact` | A fault repeating from one process. The unified log is large, so always bound the time | UNVERIFIED |
| Crash and panic reports | `ls -lt ~/Library/Logs/DiagnosticReports /Library/Logs/DiagnosticReports \| head -20` | Any `.panic` file, `fail`, repeated `.ips` reports from one app, `warn` | UNVERIFIED |
| Launch agents failing | `launchctl list \| awk '$2 != 0 && $2 != "-"'` | A non-zero last exit status for an agent that should run | UNVERIFIED |

The `macos` skill carries the unified log and `launchd` detail.

---

### Paths and environment

Why the owner's shell is measured, and what to report, is in [judging.md](judging.md). Measure through the owner's login shell, interactive and login separately:

| Shell | Interactive | Login |
|---|---|---|
| zsh | `zsh -ic 'print -l $path'` | `zsh -lc 'print -l $path'` |
| bash | `bash -ic 'echo "$PATH"' \| tr ':' '\n'` | `bash -lc 'echo "$PATH"' \| tr ':' '\n'` |

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Duplicates and missing entries (zsh) | `zsh -ic 'print -l $path' \| sort \| uniq -cd` | Any line, `warn`. Usually a file sourced twice | UNVERIFIED on macOS |
| Duplicates and missing entries (bash) | `bash -ic 'echo "$PATH"' \| tr ':' '\n' \| sort \| uniq -cd` | Any line | UNVERIFIED on macOS |
| Duplicates and missing entries (zsh) | `zsh -ic 'for d in $path; do [[ -d $d ]] \|\| print "not a directory: $d"; done'` | Any line. A directory that is gone, or an entry that names a file, which PATH ignores | UNVERIFIED on macOS |
| Shadowed binaries (zsh) | `zsh -ic 'for b in python python3 pip java node npm git ssh gpg docker; do whence -a $b; done'` | A tool resolving somewhere the owner did not choose, `ok` when `MACHINE.md` records it as the owner's choice and `warn` when it does not. Homebrew's `/opt/homebrew/bin` behind `/usr/bin` for a tool the owner installed through Homebrew, or the reverse | UNVERIFIED |

| Check | Command | What it shows | Status |
|---|---|---|---|
| Which file sets what (zsh) | `zsh -x -ic exit 2>&1 \| grep -E 'PATH='` | Every PATH assignment, prefixed with the file and line, for example `+/home/<user>/<config-dir>/env.sh:41> export PATH=...` | UNVERIFIED on macOS |
| Which file sets what (bash) | `PS4='+${BASH_SOURCE}:${LINENO}: ' bash -x -ic exit 2>&1 \| grep -E 'PATH='` | Same, with the file and line from `PS4` | UNVERIFIED on macOS |
| Which file sets what | `cat /etc/paths; ls /etc/paths.d` | What `path_helper` prepends in a login shell | UNVERIFIED |

A trace with `-x` runs the startup files, which is what an interactive shell does anyway, and changes nothing.

---

### Packages

Nothing here installs, upgrades, removes or cleans, including the tools' own cleanup commands.

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Homebrew health | `brew doctor` | Any warning other than ones the baseline accepted | UNVERIFIED |
| Outdated formulae and casks | `HOMEBREW_NO_AUTO_UPDATE=1 brew outdated --greedy` | The variable stops `brew` updating its own metadata first, so the check stays read-only and reports against the last update | UNVERIFIED |
| Missing dependencies | `brew missing` | Any output | UNVERIFIED |
| What cleaning would free | `brew cleanup --dry-run` and `brew autoremove --dry-run` | Large totals, `warn` | UNVERIFIED |
| System updates | `softwareupdate --list` | Any pending update, a security response or a point release is `warn` | UNVERIFIED |
| App Store updates | `mas outdated` | Any line | UNVERIFIED |

---

### Devices and network

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| GPU driver | `system_profiler SPDisplaysDataType` | GPU missing from the list, Metal support missing | UNVERIFIED |
| Displays | `system_profiler SPDisplaysDataType`, which prints the resolution and refresh per display | A mode below the highest refresh the monitor offers at its resolution, judged as [judging.md](judging.md) sets out | UNVERIFIED |
| Audio devices | `system_profiler SPAudioDataType` | The default output device differs from the baseline | UNVERIFIED |
| Network and firewall | `networksetup -listallhardwareports`, `scutil --dns` | The primary interface down or without an address, an interface from the baseline missing, or a DNS server nobody configured | UNVERIFIED |
| Network and firewall | `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate` | `disabled`, `warn` on a laptop, the owner decides | UNVERIFIED |
| Time sync | `sudo systemsetup -getusingnetworktime` | Needs root, goes to Needs root | UNVERIFIED |

---

### Security baseline

Firewall, Secure Boot, disk encryption and pending security updates in one view, so the owner sees the machine's posture on one screen. Most rows point at a check described in full above.

| Area | Command | Wrong looks like | Status |
|---|---|---|---|
| Firewall | the firewall row under Devices and network above | Off, `fail` | UNVERIFIED |
| Secure Boot | `csrutil status` for System Integrity Protection. Apple silicon boot policy needs `sudo bputil -d`, which goes to Needs root | `disabled` SIP, `warn` | UNVERIFIED |
| Gatekeeper | `spctl --status` | `assessments disabled`, `warn` | UNVERIFIED |
| Pending security updates | `softwareupdate --list` | A security response or a point release | UNVERIFIED |
| Disk encryption | the encryption row under Storage above | A volume the owner expects encrypted is not | UNVERIFIED |

What goes to the owner for a security finding is in [judging.md](judging.md).
