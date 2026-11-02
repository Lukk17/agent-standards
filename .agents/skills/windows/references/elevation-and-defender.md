# Elevation, UAC and Microsoft Defender

Read this before any command that needs administrator rights, and before any Defender change. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

---

### How elevation works

With UAC on, an administrator's processes run with a filtered standard token. A process gets the full token only by being started elevated, which shows a consent prompt. The agent's own process is not elevated and must stay that way.

Check whether a session is elevated:

```powershell
([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

`True` means elevated. A script that needs elevation declares `#Requires -RunAsAdministrator` and fails fast instead of half running.

---

### The owner runs elevated commands

1. Print the command, the shell it runs in, and what it changes. Group several into one numbered list, so the owner runs them in order and a failure stops the rest.
2. The owner runs them in an elevated terminal, or with sudo for Windows where it is enabled.
3. Afterwards, verify with a read-only command from the agent's unelevated session.

Never start an elevated process from the agent with `Start-Process -Verb RunAs`, `runas`, or `sudo`. A prompt the owner did not expect is exactly what UAC trains people to click through.

---

### sudo for Windows

From Microsoft Learn, "Sudo for Windows": "The Sudo for Windows command is available in Windows 11, version 24H2 or higher." It is enabled in Settings, System, Advanced, "Enable sudo". `sudo.exe` was present in `C:\Windows\System32` on the inspected Windows 11 disk, which says nothing about whether it is enabled.

Three modes:

| Mode | Value for `sudo config --enable` | Behaviour |
|---|---|---|
| In a new window | `forceNewWindow`, the default | the elevated command runs in a new window, "similar to the behavior of the `runas /user:admin` command" |
| Input closed | `disableInput` | runs in the current window with its input handle closed |
| Inline | `normal` | runs in the current window and can receive input from it |

The page warns about the last two: "It is possible for malicious processes to attempt to drive the elevated process using the connection established by the unelevated sudo.exe and the elevated sudo.exe process", and recommends `forceNewWindow` "unless you are familiar and comfortable with the risks". Never change the mode for the agent's convenience. sudo still elevates only through a UAC prompt, so the owner sees and approves each one.

---

### Microsoft Defender: read

From an elevated or standard `pwsh` with the Defender module, which exists under `C:\Windows\System32\WindowsPowerShell\v1.0\Modules\Defender` on the inspected disk:

```powershell
Get-MpComputerStatus | Select-Object AMRunningMode, RealTimeProtectionEnabled, IsTamperProtected, AntivirusSignatureLastUpdated
```

```powershell
Get-MpThreatDetection | Select-Object -First 20
```

Reading the exclusion lists from `Get-MpPreference` can need elevation.

---

### Microsoft Defender: exclusions

An exclusion stops scanning of a path. From the `Add-MpPreference` reference: `-ExclusionPath` "Specifies an array of file paths to exclude from scheduled and real-time scanning", and `-ExclusionProcess` excludes "any files opened by the processes that you specify", not the processes themselves.

1. Only with the owner's request, for one named path, typically a build output or package cache that measurably slows builds.
2. Never exclude a whole drive, the user profile, the Downloads folder, a temp directory, or an interpreter such as `python.exe` or `node.exe`.
3. The owner runs it elevated: `Add-MpPreference -ExclusionPath '<path>'`. Undo with `Remove-MpPreference -ExclusionPath '<path>'`.
4. Record the path and the reason in the `MACHINE.md` change log.

Tamper Protection blocks this. From "Protect security settings with tamper protection": when enabled, "Exclusions can't be modified or added" and "Real-time protection remains turned on". If a change fails silently, check `IsTamperProtected` and stop. Turning Tamper Protection off is the owner's decision, in the Windows Security app, and is never a step an agent proposes to get its own work done.
