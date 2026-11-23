# Install and Start

Read this before installing Syncthing, making it start at login, or opening the firewall for it. This file holds what is the same on every operating system, and the install, start and firewall steps are in [install-linux.md](install-linux.md), [install-windows.md](install-windows.md) and [install-macos.md](install-macos.md). The rules live in [SKILL.md](../SKILL.md). Commands marked VERIFIED ran on Syncthing 2 in a throwaway container. Every other command here is UNVERIFIED.

Sources: https://docs.syncthing.net/users/syncthing.html, https://docs.syncthing.net/users/config.html and https://docs.syncthing.net/users/firewall.html.

---

### Where Syncthing keeps its state

The configuration page says, under "Configuration File Locations", that the directory defaults to "`$XDG_STATE_HOME/syncthing` or `$HOME/.local/state/syncthing` (Unix-like), `$HOME/Library/Application Support/Syncthing` (Mac), or `%LOCALAPPDATA%\Syncthing` (Windows)". The same page adds that before 1.27.0 the Unix default was `~/.config/syncthing` and that "Existing installations may still use these directories instead of the newer defaults".

Never guess which one is in use. Ask Syncthing, which prints the configuration file, the keys, the database and the log location. VERIFIED:

```bash
syncthing paths
```

The database lives in that directory too, in `index-v2` on 2.x, so the disk under it is the disk that `minHomeDiskFree` watches, see [troubleshooting.md](troubleshooting.md).

---

### Firewall ports

The firewall page lists, for a local firewall, "Port 22000/TCP: TCP based sync protocol traffic", "Port 22000/UDP: QUIC based sync protocol traffic" and "Port 21027/UDP: for discovery broadcasts on IPv4 and multicasts on IPv6". The GUI port 8384 stays closed unless the owner wants remote access to the GUI. Every firewall rule needs root or administrator rights, so it goes to the owner. The commands are in the file for the operating system.

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
