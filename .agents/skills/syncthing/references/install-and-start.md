# Install and Start

Read this before installing Syncthing, making it start at login, or opening the firewall for it. The rules live in [SKILL.md](../SKILL.md). Commands marked VERIFIED ran on Syncthing 2.1.7 in a throwaway container on 2026-10-23. Every other command here is UNVERIFIED.

Sources, fetched on 2026-10-23: https://docs.syncthing.net/users/autostart.html, https://docs.syncthing.net/users/syncthing.html, https://docs.syncthing.net/users/config.html, https://docs.syncthing.net/users/firewall.html, https://apt.syncthing.net/, https://formulae.brew.sh/formula/syncthing, https://formulae.brew.sh/cask/syncthing-app, the winget manifest `Syncthing.Syncthing` 2.1.7 in `microsoft/winget-pkgs`, and `etc/linux-systemd/user/syncthing.service` at tag v2.1.7 of `syncthing/syncthing`.

---

### Where Syncthing keeps its state

The configuration page says, under "Configuration File Locations", that the directory defaults to "`$XDG_STATE_HOME/syncthing` or `$HOME/.local/state/syncthing` (Unix-like), `$HOME/Library/Application Support/Syncthing` (Mac), or `%LOCALAPPDATA%\Syncthing` (Windows)". The same page adds that before 1.27.0 the Unix default was `~/.config/syncthing` and that "Existing installations may still use these directories instead of the newer defaults".

| Platform | Configuration and database |
|---|---|
| Linux | `~/.local/state/syncthing`, or `~/.config/syncthing` on an installation older than 1.27.0 |
| macOS | `~/Library/Application Support/Syncthing` |
| Windows | `%LOCALAPPDATA%\Syncthing` |

Never guess which one is in use. Ask Syncthing, which prints the configuration file, the keys, the database and the log location. VERIFIED:

```bash
syncthing paths
```

The database lives in that directory too, in `index-v2` on 2.x, so the disk under it is the disk that `minHomeDiskFree` watches, see [troubleshooting.md](troubleshooting.md).

---

### Linux

Install from the distribution, which needs root, so the command goes to the owner. On 2026-10-23 Arch `extra` carried 2.1.7 and Fedora 44 carried 2.1.6.

```bash
sudo pacman -S syncthing
```

```bash
sudo dnf install syncthing
```

Debian and Ubuntu archives may lag behind, so apt.syncthing.net publishes a `stable-v2` channel. Its page gives these steps, all for the owner:

```bash
sudo mkdir -p /etc/apt/keyrings
```

```bash
sudo curl -L -o /etc/apt/keyrings/syncthing-archive-keyring.gpg https://syncthing.net/release-key.gpg
```

```bash
echo "deb [signed-by=/etc/apt/keyrings/syncthing-archive-keyring.gpg] https://apt.syncthing.net/ syncthing stable-v2" | sudo tee /etc/apt/sources.list.d/syncthing.list
```

```bash
sudo apt-get update
```

```bash
sudo apt-get install syncthing
```

Start it as a systemd user service, which needs no root. The autostart page says the user service "is intended to be used on a (multiuser) desktop computer", and the packages above ship `syncthing.service` for the user instance. In 2.1.7 that unit runs `/usr/bin/syncthing serve --no-browser --no-restart`.

```bash
systemctl --user enable --now syncthing.service
```

```bash
systemctl --user status syncthing.service
```

```bash
journalctl -e --user-unit=syncthing.service
```

A user service starts at login. To start it at boot on a machine nobody logs in to, the owner enables lingering for the account, which needs root:

```bash
sudo loginctl enable-linger <user>
```

A systemd user service runs in the user's home directory. The systemd.exec page says `WorkingDirectory=` defaults to "the respective user's home directory if run as user", which is why a folder created with a relative path lands in the home folder, see [folders-and-devices.md](folders-and-devices.md).

---

### Windows

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

### macOS

Install the formula and start it with `brew services`, which writes a LaunchAgent for the user. The formula's service block, read from formulae.brew.sh on 2026-10-23, runs `syncthing --no-browser --no-restart`, keeps it alive, and logs to `$(brew --prefix)/var/log/syncthing.log`. Homebrew never runs under `sudo`.

```bash
brew install syncthing
```

```bash
brew services start syncthing
```

```bash
brew services info syncthing
```

The cask `syncthing-app` is the menu bar application, which brings its own copy of Syncthing and starts it itself. Install one of the two, never both, or two instances fight over the same configuration and ports.

---

### Firewall

The firewall page lists, for a local firewall, "Port 22000/TCP: TCP based sync protocol traffic", "Port 22000/UDP: QUIC based sync protocol traffic" and "Port 21027/UDP: for discovery broadcasts on IPv4 and multicasts on IPv6". The GUI port 8384 stays closed unless the owner wants remote access to the GUI. Every rule below needs root or administrator rights, so it goes to the owner.

Linux with ufw and a packaged Syncthing, which ships the `syncthing` profile:

```bash
sudo ufw allow syncthing
```

Linux with firewalld, which has carried a `syncthing` service since 0.5.0:

```bash
sudo firewall-cmd --zone=public --add-service=syncthing --permanent
```

```bash
sudo firewall-cmd --reload
```

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

macOS: when the application firewall is on, macOS asks once whether `syncthing` may accept incoming connections. The owner answers that prompt, or allows it in System Settings, Network, Firewall, Options. UNVERIFIED.

---

### First check after the start

VERIFIED, all three:

```bash
syncthing --version
```

```bash
syncthing device-id
```

```bash
syncthing cli show system
```

`syncthing device-id` prints this device's ID, which is what the other side needs to pair. `show system` returns JSON with `myID` and the state of every listener. Syncthing 2.x no longer creates a Default Folder on first start, so a fresh install has no folders at all. Set the default folder path next, as [folders-and-devices.md](folders-and-devices.md) describes.
