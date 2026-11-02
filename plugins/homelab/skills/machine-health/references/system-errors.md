# System Errors

Failed units, crashes, error level log lines since boot, kernel warnings and taint, and the Windows and macOS equivalents. The rules live in [SKILL.md](../SKILL.md). Linux commands below were executed read-only on CachyOS with systemd 262, macOS and Windows commands are UNVERIFIED.

---

### Linux

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Failed system units | `systemctl --failed --no-legend --plain` | Any line, `fail` | verified, none |
| Failed user units | `systemctl --user --failed --no-legend --plain` | Any line, `fail` | verified, none |
| Crashes | `coredumpctl list --since=-7d --no-pager` | Any entry is worth a line. The same executable crashing repeatedly is `warn`, a system daemon is `fail` | verified, one `SIGABRT` of `/usr/bin/chwd` that day |
| Errors since boot, counted | `journalctl -b -p err --no-pager -q \| wc -l` | A count well above the baseline | verified, 62 |
| Errors since boot, grouped | `journalctl -b -p err --no-pager -q -o cat \| sort \| uniq -c \| sort -rn \| head -20` | New messages compared with the baseline. Group before reading, one noisy line can hide a rare one | verified |
| Previous boot | `journalctl -b -1 -p err --no-pager -q -o cat \| sort \| uniq -c \| sort -rn \| head -20` | Errors right before an unexpected end of the previous boot | verified |
| Boots that ended badly | `journalctl --list-boots --no-pager \| tail -5` | Fewer boots than the owner remembers, or a boot whose last lines show no clean shutdown | verified |
| Kernel warnings | `journalctl -k -b -p warning --no-pager -q -o cat \| grep -v 'UFW BLOCK' \| sort \| uniq -c \| sort -rn \| head -20` | `WARNING:`, `BUG:`, `Oops`, call traces, firmware load failures. Firewall block lines are excluded because they are expected noise | verified, `grep -v` was needed because UFW block lines filled the output |
| Kernel taint | `cat /proc/sys/kernel/tainted` | Any value outside the baseline. Decode the bits before judging | verified, `12288` |

Decode taint with the kernel's own table: "If that returns `0`, the kernel is not tainted; any other number indicates the reasons why it is", with bit 12 "externally-built (out-of-tree) module was loaded" (4096) and bit 13 "unsigned module was loaded" (8192), and bit 9 "kernel issued warning" (512) (<https://docs.kernel.org/admin-guide/tainted-kernels.html>). On the test machine `12288` is 4096 plus 8192, which an out of tree GPU driver produces, so it is `ok` when the baseline says the same. Bit 9 appearing is `warn` and the kernel warning lines above say why.

The journal can miss the first minutes of a boot, and `dmesg` is root only while `kernel.dmesg_restrict` is 1, both measured on the test machine. When an early boot problem is suspected, put `needs: sudo dmesg --level=err,warn` into Needs root.

Read the messages, not only the counts. A line such as `a password is required ; ... COMMAND=/usr/bin/true` in the error log is an agent or script probing `sudo`, which this skill forbids, and is worth naming to the owner.

---

### Windows

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Critical and error events, System log | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; Level = 1, 2; StartTime = (Get-Date).AddDays(-7) } \| Group-Object ProviderName, Id \| Sort-Object Count -Descending \| Select-Object -First 20 Count, Name` | New providers or ids compared with the baseline | UNVERIFIED |
| Same for Application | the same command with `LogName = 'Application'` | Repeated application crashes | UNVERIFIED |
| Unexpected shutdowns | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-Kernel-Power'; Id = 41 } -MaxEvents 10` | Any recent event, the previous shutdown was not clean | UNVERIFIED |
| Hardware errors | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-WHEA-Logger' } -MaxEvents 20` | Any event | UNVERIFIED |
| Services that should run | `Get-CimInstance Win32_Service -Filter "StartMode='Auto' AND State<>'Running'" \| Select-Object Name, DisplayName, State` | An automatic service that is stopped and is not one of the delayed or trigger start services that stop by design | UNVERIFIED |

Level 1 is critical and level 2 is error. Filter inside the hashtable rather than with `Where-Object`, so the event log service does the filtering. The `windows` skill carries the event log detail.

---

### macOS

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Faults in the last hour | `log show --last 1h --predicate 'messageType == fault' --style compact` | A fault repeating from one process. The unified log is large, so always bound the time | UNVERIFIED |
| Crash and panic reports | `ls -lt ~/Library/Logs/DiagnosticReports /Library/Logs/DiagnosticReports \| head -20` | Any `.panic` file, `fail`, repeated `.ips` reports from one app, `warn` | UNVERIFIED |
| Launch agents failing | `launchctl list \| awk '$2 != 0 && $2 != "-"'` | A non-zero last exit status for an agent that should run | UNVERIFIED |

The `macos` skill carries the unified log and `launchd` detail.
