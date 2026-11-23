# Install and Start on Windows

Read this before installing Syncthing on Windows, making it start at logon, or opening the firewall for it. What is the same on every operating system, the command that prints the state directory, the firewall ports and the first check after the start, is in [install-and-start.md](install-and-start.md). The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Sources: https://docs.syncthing.net/users/autostart.html, https://docs.syncthing.net/users/firewall.html, and the winget manifest `Syncthing.Syncthing` in `microsoft/winget-pkgs`.

---

### State directory

The configuration and the database are in `%LOCALAPPDATA%\Syncthing`.

---

### Install and start

Install with winget. The `Syncthing.Syncthing` manifest is a portable zip that registers the command `syncthing`, so no installer runs and no elevation is needed.

```powershell
winget install --id Syncthing.Syncthing -e --source winget
```

The autostart page says "There is currently no official installer available for Windows" and lists Task Scheduler and the Startup folder as the built-in ways to start it. A task that runs at the owner's logon, as the owner, needs no elevation. Name the full path, because a task does not see the interactive `PATH`. The winget link path stays the same across upgrades.

```powershell
$syncthingExe = (Get-Command syncthing).Source
```

```powershell
$action = New-ScheduledTaskAction -Execute $syncthingExe -Argument 'serve --no-console --no-browser'
```

```powershell
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
```

The upstream steps also clear "Stop task if it runs longer than", which is an execution time limit of zero here, and the battery conditions:

```powershell
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
```

```powershell
Register-ScheduledTask -TaskName 'Syncthing' -Action $action -Trigger $trigger -Settings $settings -Description 'Syncthing at logon, added by <who> on <date>'
```

```powershell
Start-ScheduledTask -TaskName 'Syncthing'
```

The same page warns that "ending the task in Task Scheduler terminates only the monitor process of Syncthing". Stop Syncthing itself through the API instead:

```powershell
syncthing cli operations shutdown
```

Running Syncthing as a Windows service through NSSM is the upstream route only for a headless server, and the page says starting on login "is the preferred approach for almost any end-user scenario". Do not set that up unless the owner asks for it.

---

### Firewall

The ports are listed in [install-and-start.md](install-and-start.md#firewall-ports). Every rule below needs root or administrator rights, so it goes to the owner.

Windows, in an elevated `pwsh`. The upstream note says the first interactive start triggers a Windows Firewall prompt. Port rules avoid both the prompt and a program path that changes with every winget upgrade. These three commands are UNVERIFIED:

```powershell
New-NetFirewallRule -DisplayName 'Syncthing sync TCP' -Direction Inbound -Protocol TCP -LocalPort 22000 -Action Allow -Profile Private
```

```powershell
New-NetFirewallRule -DisplayName 'Syncthing sync UDP' -Direction Inbound -Protocol UDP -LocalPort 22000 -Action Allow -Profile Private
```

```powershell
New-NetFirewallRule -DisplayName 'Syncthing discovery' -Direction Inbound -Protocol UDP -LocalPort 21027 -Action Allow -Profile Private
```
