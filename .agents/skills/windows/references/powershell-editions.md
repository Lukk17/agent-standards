# PowerShell 7 and Windows PowerShell 5.1

Read this before handing over a PowerShell command, and when a script works in one shell and fails in the other. The rules live in [SKILL.md](../SKILL.md). How to write the script itself belongs to the `powershell` skill.

---

### Which one to run

The order is rule 1 in [SKILL.md](../SKILL.md): PowerShell 7 when it is installed, its installation recommended when it is not, and Windows PowerShell 5.1 only after the owner declines.

1. Check for PowerShell 7 with `Get-Command pwsh -ErrorAction SilentlyContinue`, which answers in either shell, or `where.exe pwsh` from `cmd`. Output means it is installed, so run the command in `pwsh`.
2. When nothing comes back, recommend the install to the owner before handing over any 5.1 command. Microsoft Learn, "Install PowerShell 7 on Windows", lists "WinGet - Recommended way to install PowerShell on Windows clients" and gives `winget install --id Microsoft.PowerShell --source winget`. Add `-e` as for every winget install, see [package-managers.md](package-managers.md).
3. The same page says "Beginning with the winget package for PowerShell 7.6.0, winget installs the MSIX package by default" and "Store-based installations are installed for a single user". Whether that install raises a UAC prompt on a given machine is UNVERIFIED, so the owner runs it.
4. Fall back to `powershell.exe` only when the owner declines, say in the handover that the command targets 5.1, and check it against the table below.
5. A Windows module that loads only in 5.1 does not change the choice. Load it from `pwsh` through the compatibility session described under "What breaks between them".

---

### Two programs, side by side

From Microsoft Learn, "Differences between Windows PowerShell 5.1 and PowerShell 7.x": "The binary name for PowerShell has been changed from `powershell(.exe)` to `pwsh(.exe)`. This change provides a deterministic way for users to run PowerShell on machines and support side-by-side installations of Windows PowerShell and PowerShell."

1. `powershell.exe` is Windows PowerShell 5.1, shipped with Windows under `C:\Windows\System32\WindowsPowerShell\v1.0\`. That path was confirmed on a mounted Windows 11 disk, read-only.
2. `pwsh.exe` is PowerShell 7, installed separately, for example through winget (`Microsoft.PowerShell`) or the Store. A Store install appears as an app execution alias under `%LOCALAPPDATA%\Microsoft\WindowsApps`, as on the inspected disk, rather than under `C:\Program Files\PowerShell\7`.
3. Check what a session is with `$PSVersionTable.PSVersion` and `$PSVersionTable.PSEdition`, which reads `Desktop` for 5.1 and `Core` for 7.
4. `pwsh` takes a script path as its first positional argument. To run a command string, say so: `pwsh -NoProfile -Command "<command>"`.

---

### What breaks between them

| Area | Windows PowerShell 5.1 | PowerShell 7 | Source |
|---|---|---|---|
| Default file encoding | "Out-File and the redirection operators `>` and `>>` create UTF-16LE", and `Set-Content` uses the ANSI code page | "PowerShell defaults to `utf8NoBOM` for all output" | about_Character_Encoding |
| Reading a script without a BOM | read as the ANSI code page, so non-ASCII characters break | read as UTF-8 | about_Character_Encoding |
| Event log cmdlets | `Get-EventLog` exists | "the `*-EventLog` cmdlets have been removed", use `Get-WinEvent` | differences page |
| `sc` | an alias of `Set-Content` | no such alias | the Set-Content page for each version |
| `Get-WmiObject` | present | removed, use `Get-CimInstance` | differences page, WMI v1 cmdlets |

Consequences:

1. Always call the service control tool as `sc.exe`. In 5.1 a bare `sc query` writes a file instead.
2. A script with non-ASCII characters that must run in 5.1 is saved as UTF-8 with a BOM. The encoding page: "Without the BOM, Windows PowerShell misinterprets your script as being encoded in the legacy "ANSI" codepage."
3. When writing a text file other tools read, state the encoding: `Set-Content -Encoding utf8` in 7, and expect a BOM from `-Encoding UTF8` in 5.1.
4. Some Windows modules still load only in 5.1. In 7, `Import-Module <name> -UseWindowsPowerShell` loads one through a 5.1 compatibility session. UNVERIFIED for any specific module.

---

### Execution policy

A script blocked with "running scripts is disabled on this system" is the execution policy. Read it with `Get-ExecutionPolicy -List`. The narrowest change is the current user scope, which needs no elevation: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`. Execution policy is not a security boundary, but changing it is still the owner's decision. A downloaded script also carries a Zone.Identifier mark, removed with `Unblock-File <path>` after the owner has read it.
