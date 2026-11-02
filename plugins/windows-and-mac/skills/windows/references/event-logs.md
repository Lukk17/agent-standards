# Event Logs

Read this when you need evidence for a failure: a service that would not start, a crash, an update that failed, an unexpected reboot. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

---

### Use Get-WinEvent

`Get-EventLog` does not exist in PowerShell 7. From the differences page: "the `*-EventLog` cmdlets have been removed from PowerShell. `Get-WinEvent` and `New-WinEvent` are available to get and create events on Windows." `Get-WinEvent` works in both editions, so use it everywhere.

List the logs that have entries:

```powershell
Get-WinEvent -ListLog * -ErrorAction SilentlyContinue | Where-Object RecordCount -gt 0 | Sort-Object RecordCount -Descending | Select-Object -First 30 LogName, RecordCount
```

---

### Bounded queries

Always bound a query by time, level or count. An unbounded read of the System log returns tens of thousands of events.

Errors and critical events in the System log over the last day:

```powershell
Get-WinEvent -FilterHashtable @{ LogName = 'System'; Level = 1, 2; StartTime = (Get-Date).AddDays(-1) }
```

One provider, the newest 50:

```powershell
Get-WinEvent -FilterHashtable @{ LogName = 'Application'; ProviderName = '<provider>' } -MaxEvents 50
```

One event id, as in the reference's own example `Get-WinEvent -FilterHashtable @{ LogName='Application'; StartTime=$Date; Id='1003' }`:

```powershell
Get-WinEvent -FilterHashtable @{ LogName = 'System'; Id = 41 } -MaxEvents 10
```

Levels are 1 critical, 2 error, 3 warning, 4 information. Filter in the hashtable rather than with `Where-Object`, because the hashtable filter runs in the event log service and does not ship every event to PowerShell first.

---

### Where to look

| Question | Log |
|---|---|
| Service start failures, drivers, unexpected shutdowns | `System` |
| Application crashes and installer results | `Application` |
| Sign-ins, privilege use, audit events | `Security`, which needs elevation to read |
| A component's own detail | `Microsoft-Windows-<Component>/Operational`, for example `Microsoft-Windows-PowerShell/Operational` |

The log files are `.evtx` files under `C:\Windows\System32\winevt\Logs`, confirmed on a mounted Windows 11 disk, read-only. Read them through `Get-WinEvent -Path <file>` rather than copying them around, because the Security log can hold sensitive information.

From `cmd` or a script without PowerShell, `wevtutil.exe qe System /c:20 /rd:true /f:text` reads the newest 20 System events.

---

### Reading honestly

The first error in a burst is usually the cause, later ones are consequences. Quote the event's time, provider, id and message when reporting, and correlate with a symptom or a time (an update, a reboot, a resume) before blaming a warning.
