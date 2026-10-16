# Desktop Defaults and the Login Manager

Read this before changing something a `cachyos-*-settings` package seeded, before copying files out of `/etc/skel`, or before touching the login manager. Plasma configuration itself (panels, shortcuts, KWin, widgets, themes) belongs to the `kde-plasma` skill. This file covers only the CachyOS layer. The rules live in [SKILL.md](../SKILL.md).

---

### Discover what is installed

```bash
pacman -Q | grep -E '^cachyos-.*(settings|theme|wallpapers)'
```

```bash
pacman -Ql cachyos-kde-settings
```

```bash
systemctl status display-manager --no-pager
```

1. `cachyos-kde-settings` owns the KDE defaults CachyOS ships. Its files sit under `/etc/skel/.config/`, plus snippets for SDDM. If SDDM is not the login manager in use, those snippets have no effect.
2. Theme and wallpaper packages are visuals, not configuration.
3. `display-manager.service` is an alias for whichever login manager is enabled, so its status names it. Check the session type with `echo "$XDG_SESSION_TYPE"`.

---

### Rules

1. `/etc/skel` is copied once, when a user account is created. It never updates an existing user, so changing it does nothing for the owner, and it is a packaged location. Never edit it.
2. Never copy or rsync `/etc/skel` over `~`. It overwrites the owner's customised settings. To see a stock default, read the file or diff it against the live one: `diff /etc/skel/.config/kwinrc ~/.config/kwinrc`. To pull one stock setting back, back up the live file first and change one key, preferably with `kwriteconfig6`.
3. Do not uninstall `cachyos-kde-settings` so that an upstream recipe "applies cleanly". Override in `~/.config` instead.
4. The login manager is a boot path. Changing, disabling or replacing it can leave the machine without a graphical login. Take a snapshot, keep a TTY available (Ctrl+Alt+F3), and ask first. Never disable it as a side effect of another task. Its configuration lives in `/etc` drop-ins, never in `/usr/share`. Look up the exact files with `pacman -Ql <login manager package>` and its `man` page before writing anything.
5. Wayland and the NVIDIA driver interact. When the session fails to start after a driver or kernel upgrade, see [hardware-nvidia.md](hardware-nvidia.md).
6. KDE problems after a big upgrade are most often a partial upgrade of KDE Frameworks or an AUR widget built against old libraries. Check the `arch-linux` skill's partial upgrade topic first.
