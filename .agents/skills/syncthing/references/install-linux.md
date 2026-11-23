# Install and Start on Linux

Read this before installing Syncthing on Linux, making it start at login or at boot, or opening the firewall for it. What is the same on every operating system, the command that prints the state directory, the firewall ports and the first check after the start, is in [install-and-start.md](install-and-start.md). The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Sources: https://docs.syncthing.net/users/autostart.html, https://docs.syncthing.net/users/firewall.html, https://apt.syncthing.net/, and `etc/linux-systemd/user/syncthing.service` of `syncthing/syncthing`.

---

### State directory

The configuration and the database are in `~/.local/state/syncthing`, or in `~/.config/syncthing` on an installation older than 1.27.0.

---

### Install and start

Install from the distribution, which needs root, so the command goes to the owner.

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

Start it as a systemd user service, which needs no root. The autostart page says the user service "is intended to be used on a (multiuser) desktop computer", and the packages above ship `syncthing.service` for the user instance. In Syncthing 2 that unit runs `/usr/bin/syncthing serve --no-browser --no-restart`.

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

### Firewall

The ports are listed in [install-and-start.md](install-and-start.md#firewall-ports). Every rule below needs root or administrator rights, so it goes to the owner.

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
