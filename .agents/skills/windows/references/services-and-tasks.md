# Services and Scheduled Tasks

Read this before inspecting or changing a service or a scheduled task. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

---

### Services: read

```powershell
Get-Service -Name '<name>' | Format-List Name, DisplayName, Status, StartType
```

```powershell
Get-CimInstance Win32_Service -Filter "Name='<name>'" | Format-List Name, State, StartMode, StartName, PathName
```

The CIM view adds the account the service runs as and the binary path, which `Get-Service` does not show in 5.1. Call the native tool as `sc.exe`, never `sc`, see [powershell-editions.md](powershell-editions.md):

```powershell
sc.exe qc <name>
```

---

### Services: change

All of these need elevation, so they go to the owner.

1. Record the current start type first, from the read above.
2. Restart: `Restart-Service -Name '<name>'`.
3. Start type: `Set-Service -Name '<name>' -StartupType Manual`. The values are `Automatic`, `Manual` and `Disabled`, and PowerShell 7 adds `AutomaticDelayedStart`.
4. Read it back, and write the old and new start type in the `MACHINE.md` change log.

Never disable a service whose purpose you have not identified. Services named for Defender, Windows Update, BitLocker, the event log or networking are out of bounds without a stated reason and the owner's approval.

---

### Scheduled tasks: read

```powershell
Get-ScheduledTask | Where-Object State -ne 'Disabled' | Select-Object TaskPath, TaskName, State
```

```powershell
Get-ScheduledTaskInfo -TaskPath '\' -TaskName '<name>'
```

```powershell
Export-ScheduledTask -TaskPath '\' -TaskName '<name>'
```

The export prints the task XML, which is also the backup to keep before a change. `schtasks.exe /query /fo LIST /v` gives the same information from `cmd`. Task definitions live under `C:\Windows\System32\Tasks`, confirmed on a mounted Windows 11 disk, read-only. Read them through the cmdlets rather than editing the files.

---

### Scheduled tasks: create

A per-user task that runs at logon needs no elevation when it runs as the current user with standard rights. A task that runs elevated, at startup, or as SYSTEM goes to the owner.

```powershell
$action = New-ScheduledTaskAction -Execute 'pwsh.exe' -Argument '-NoProfile -File "C:\path\to\script.ps1"'
```

```powershell
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
```

```powershell
Register-ScheduledTask -TaskName '<name>' -Action $action -Trigger $trigger -Description '<why, and who added it>'
```

1. Name the full path to the interpreter and the script. A task does not run in the owner's interactive environment and may not see the same `PATH`.
2. Test it once with `Start-ScheduledTask -TaskName '<name>'` and read `LastTaskResult` from `Get-ScheduledTaskInfo`. `0` means success.
3. Remove with `Unregister-ScheduledTask -TaskName '<name>'`, and record both in the change log.
