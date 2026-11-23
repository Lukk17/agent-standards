# Windows Checks

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

Every check for a machine that runs Windows, in run order. The rules live in [SKILL.md](../SKILL.md), and how a value becomes a verdict on any operating system is in [judging.md](judging.md). No command here was executed, so every row is UNVERIFIED.

---

### Before the first command

1. Never run `runas`, an elevated PowerShell or anything that asks for a password. A check that needs elevation goes into Needs root as `needs: elevated <command>`.
2. Never run `fsutil dirty set`, `chkdsk /f` or `chkdsk /r`. A read-only `chkdsk C: /scan` needs elevation and goes to the owner.
3. A device in the never-touch table gets listing level only, `Get-Disk`.
4. List variable names and paths only, never the value of a variable that might hold a secret.

---

### CPU

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Model and microcode | `Get-CimInstance Win32_Processor \| Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed` | Model or core count differs from `MACHINE.md` | UNVERIFIED |
| Model and microcode | `Get-ItemProperty 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0' \| Select-Object 'Update Revision'` | Value differs from the baseline with no BIOS or Windows update behind it | UNVERIFIED |
| Governor and power profile | `powercfg /getactivescheme` | Scheme differs from the baseline, or Power saver on a desktop | UNVERIFIED |
| Temperatures | `Get-CimInstance -Namespace root\wmi -ClassName MSAcpi_ThermalZoneTemperature` | Needs elevation on most machines and reports an ACPI zone in tenths of kelvin, often not the CPU die. Treat the value as indicative only | UNVERIFIED |
| Throttling | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-Kernel-Processor-Power'; StartTime = (Get-Date).AddDays(-7) } -MaxEvents 20` | Events saying the processor speed is limited by firmware. The event id is from memory and not checked against a Microsoft page | UNVERIFIED |

---

### Memory

| Check | Command | What it gives | Status |
|---|---|---|---|
| Installed modules | `Get-CimInstance Win32_PhysicalMemory \| Select-Object DeviceLocator,BankLabel,Capacity,Speed,ConfiguredClockSpeed,Manufacturer,PartNumber,Attributes,SMBIOSMemoryType` | Per slot. The bootstrap prompt lists it as unprivileged. If it answers access denied, move it to Needs root as `needs: elevated` | UNVERIFIED |

Read the Windows fields carefully. Microsoft documents `ConfiguredClockSpeed` as "The configured clock speed of the memory device, in megahertz (MHz), or 0, if the speed is unknown", and `Attributes` as "SMBIOS - Type 17 - Attributes. Represents the RANK" (<https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemory>). The same page documents `Speed` as "Speed of the physical memory, in nanoseconds", which does not match the MT/s figures it usually shows. Treat `Speed` as the module rating only after checking it against the part number.

The configured speed is `ConfiguredClockSpeed`, and `DeviceLocator` and `BankLabel` name the channel, for example `P0 CHANNEL A`. The verdicts for configured speed, mixed kits and channels are in [judging.md](judging.md).

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Memory errors | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-WHEA-Logger'; StartTime = (Get-Date).AddDays(-30) } -MaxEvents 20` | Any event, WHEA is where Windows records hardware errors | UNVERIFIED |

The memory test for Windows is Windows Memory Diagnostic. Microsoft's older reliability guide says to run `mdsched.exe` and choose to restart now or at the next restart, after which the test runs automatically (<https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-vista/cc749573(v=ws.10)>, a Vista era page, so confirm the dialog on the current build). Where the result lands in the System log is UNVERIFIED. The agent never schedules the test, as [judging.md](judging.md) sets out.

---

### Storage

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| SMART and NVMe health | `Get-PhysicalDisk \| Select-Object FriendlyName,MediaType,HealthStatus,OperationalStatus` | `HealthStatus` other than `Healthy`, `OperationalStatus` other than `OK` | UNVERIFIED |
| SMART and NVMe health | `Get-PhysicalDisk \| Get-StorageReliabilityCounter \| Select-Object DeviceId,Temperature,Wear,ReadErrorsUncorrected,WriteErrorsUncorrected,PowerOnHours` | Needs elevation, so it goes to Needs root as `needs: elevated` | UNVERIFIED |
| Filesystem errors | `fsutil dirty query C:` | `Volume C: is dirty`. Likely needs elevation | UNVERIFIED |
| Filesystem errors | `Get-Volume \| Select-Object DriveLetter,FileSystemLabel,FileSystem,HealthStatus,SizeRemaining,Size` | `HealthStatus` other than `Healthy` | UNVERIFIED |
| Free space | `Get-Volume` as above | `SizeRemaining` below 10 percent of `Size` on the system drive | UNVERIFIED |
| Encryption state | `manage-bde -status`, `Get-BitLockerVolume` | Both need elevation, so they go to Needs root | UNVERIFIED |

Microsoft describes the dirty bit: "When a volume's dirty bit is set, autochk automatically checks the volume for errors the next time the computer is restarted", and lists "Corruption was detected on the volume" among its causes (<https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/fsutil-dirty>).

---

### System errors

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Critical and error events, System log | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; Level = 1, 2; StartTime = (Get-Date).AddDays(-7) } \| Group-Object ProviderName, Id \| Sort-Object Count -Descending \| Select-Object -First 20 Count, Name` | New providers or ids compared with the baseline | UNVERIFIED |
| Same for Application | the same command with `LogName = 'Application'` | Repeated application crashes | UNVERIFIED |
| Unexpected shutdowns | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-Kernel-Power'; Id = 41 } -MaxEvents 10` | Any recent event, the previous shutdown was not clean | UNVERIFIED |
| Hardware errors | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-WHEA-Logger' } -MaxEvents 20` | Any event | UNVERIFIED |
| Services that should run | `Get-CimInstance Win32_Service -Filter "StartMode='Auto' AND State<>'Running'" \| Select-Object Name, DisplayName, State` | An automatic service that is stopped and is not one of the delayed or trigger start services that stop by design | UNVERIFIED |

Level 1 is critical and level 2 is error. Filter inside the hashtable rather than with `Where-Object`, so the event log service does the filtering. The `windows` skill carries the event log detail.

---

### Paths and environment

Why the owner's shell is measured, and what to report, is in [judging.md](judging.md). In PowerShell 7 the PATH is `$env:Path -split ';'`, interactive or login, because the process inherits machine plus user.

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| Duplicates and missing entries | `$env:Path -split ';' \| Where-Object { $_ } \| Group-Object \| Where-Object Count -gt 1 \| Select-Object Count, Name` | Any line | UNVERIFIED |
| Duplicates and missing entries | `$env:Path -split ';' \| Where-Object { $_ -and -not (Test-Path -LiteralPath $_ -PathType Container) }` | Any line | UNVERIFIED |
| Duplicates and missing entries | `[Environment]::GetEnvironmentVariable('Path', 'Machine') -split ';'` and the same with `'User'` | The same directory in both scopes, or a user entry that belongs in the machine scope | UNVERIFIED |
| Shadowed binaries | `Get-Command python, python3, pip, java, node, git, ssh -All -ErrorAction SilentlyContinue \| Select-Object Name, Source` | `python.exe` resolving to the App Execution Alias under `WindowsApps` ahead of a real install, a stub that opens the Store instead of running Python | UNVERIFIED |

| Check | Command | What it shows | Status |
|---|---|---|---|
| Which file sets what | the two `GetEnvironmentVariable` scopes in the table above | Machine and user PATH, set through System Properties or the registry | UNVERIFIED |

---

### Packages

Nothing here installs, upgrades, removes or cleans, including the tools' own cleanup commands.

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| winget | `winget upgrade --include-unknown` | Pending upgrades. The list includes apps winget did not install, compare with `MACHINE.md` before suggesting winget for one | UNVERIFIED |
| Chocolatey | `choco outdated` | Pending upgrades | UNVERIFIED |
| Scoop, only where installed | `scoop status` | Pending upgrades | UNVERIFIED |
| Reboot owed | `Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'` | `True`, `warn` | UNVERIFIED |
| Windows Update pending | `(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search('IsInstalled=0 and IsHidden=0').Updates \| Select-Object Title` | Any security or cumulative update, `warn`. Never install a module such as PSWindowsUpdate to answer this | UNVERIFIED |

The install order and which manager owns which app live in `windows`. A suggested upgrade goes through the manager that already owns the app.

---

### Devices and network

| Check | Command | Wrong looks like | Status |
|---|---|---|---|
| GPU driver | `Get-CimInstance Win32_VideoController \| Select-Object Name, DriverVersion, DriverDate, Status` | `Microsoft Basic Display Adapter`, which means no vendor driver, or `Status` other than `OK` | UNVERIFIED |
| Displays | `Get-CimInstance Win32_VideoController \| Select-Object CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, MaxRefreshRate` | A mode below the highest refresh the monitor offers at its resolution, judged as [judging.md](judging.md) sets out | UNVERIFIED |
| Displays | `Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorListedSupportedSourceModes` for the modes each monitor lists | The modes to compare the current one with | UNVERIFIED |
| Audio devices | `Get-CimInstance Win32_SoundDevice \| Select-Object Name, Status` | `Status` other than `OK`. The default device is not exposed through CIM, so ask the owner rather than installing a module to read it | UNVERIFIED |
| Network and firewall | `Get-NetAdapter \| Select-Object Name, Status, LinkSpeed`, `Get-NetIPConfiguration` | The primary interface down or without an address, an interface from the baseline missing, or a DNS server nobody configured | UNVERIFIED |
| Network and firewall | `Get-NetFirewallProfile \| Select-Object Name, Enabled` | Any profile `False`, `fail` | UNVERIFIED |
| Time sync | `w32tm /query /status` | `Source: Local CMOS Clock` means no sync. May need elevation | UNVERIFIED |
| Dual boot clock | `Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\TimeZoneInformation' -Name RealTimeIsUniversal -ErrorAction SilentlyContinue` | A value that disagrees with the Linux `LocalRTC` value, by the dual boot clock rule in [judging.md](judging.md) | UNVERIFIED |

---

### Security baseline

Firewall, Secure Boot, disk encryption and pending security updates in one view, so the owner sees the machine's posture on one screen. Most rows point at a check described in full above.

| Area | Command | Wrong looks like | Status |
|---|---|---|---|
| Firewall | the firewall row under Devices and network above | Off, `fail` | UNVERIFIED |
| Secure Boot | `Confirm-SecureBootUEFI` | Elevated only, goes to Needs root | UNVERIFIED |
| Antivirus | `Get-MpComputerStatus \| Select-Object AMServiceEnabled, RealTimeProtectionEnabled, AntivirusSignatureLastUpdated` | Real time protection off, or signatures older than a week | UNVERIFIED |
| Pending security updates | the Windows Update query under Packages above | A security or cumulative update | UNVERIFIED |
| Disk encryption | the encryption row under Storage above | A volume the owner expects encrypted is not | UNVERIFIED |

What goes to the owner for a security finding is in [judging.md](judging.md).
