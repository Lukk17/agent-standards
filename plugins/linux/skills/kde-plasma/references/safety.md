# Safety: Snapshot, Restart, Rollback

Read this before any write to the Plasma configuration. The rules live in [SKILL.md](../SKILL.md).

---

### Snapshot, always first

Two layers. Use both before a panel or widget change, the file copy alone for a one-key theme change. Pick a stamp, then copy the files into a backup directory:

```bash
STAMP=$(date +%Y%m%d-%H%M%S); mkdir -p ~/.local/state/plasma-backups/"$STAMP"; cp -a ~/.config/plasma-org.kde.plasma.desktop-appletsrc ~/.config/plasmashellrc ~/.config/kdeglobals ~/.config/kwinrc ~/.config/kglobalshortcutsrc ~/.config/plasmarc ~/.config/kcminputrc ~/.local/state/plasma-backups/"$STAMP"/
```

Save the layout as a replayable script, which is a read-only call:

```bash
qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.dumpCurrentLayoutJS > ~/.local/state/plasma-backups/"$STAMP"/layout.js
```

Add a konsave profile where konsave is installed, see [konsave.md](konsave.md):

```bash
konsave -s backup-"$(date +%Y%m%d)" -f
```

Verified on one host: the `dumpCurrentLayoutJS` call and the file paths. Not run there: the copy and `konsave -s`, both of which write. Some of the listed files may not exist on a fresh account, in which case `cp` reports them and copies the rest.

---

### Restart plasmashell

```bash
systemctl --user restart plasma-plasmashell
```

```bash
systemctl --user status plasma-plasmashell --no-pager
```

Check the unit first with `systemctl --user cat plasma-plasmashell`. On the verified host it was `Type=dbus` with `ExecStart=/usr/bin/plasmashell --no-respawn` and `Restart=on-failure`. Panels vanish for a few seconds during a restart, which is normal.

If plasmashell is wedged and the unit will not stop: `systemctl --user kill -s KILL plasma-plasmashell`, then `systemctl --user start plasma-plasmashell`. UNVERIFIED.

---

### Roll back

1. Stop plasmashell so it cannot overwrite the restore: `systemctl --user stop plasma-plasmashell`.
2. Copy the snapshot back: `cp -a ~/.local/state/plasma-backups/<STAMP>/. ~/.config/`. The `layout.js` file lands in `~/.config` as well, remove it afterwards or copy the config files by name.
3. Start it: `systemctl --user start plasma-plasmashell`.
4. KWin and theme files: `qdbus6 org.kde.KWin /KWin org.kde.KWin.reconfigure`. A color scheme restores with `plasma-apply-colorscheme <name>`.
5. From a konsave profile: `konsave -a <name>`, then log out and in.
6. If the desktop does not come up at all, switch to a TTY (Ctrl+Alt+F3), log in, and do steps 2 and 3 there, or move the file aside and let Plasma regenerate defaults: `mv ~/.config/plasma-org.kde.plasma.desktop-appletsrc ~/.config/plasma-org.kde.plasma.desktop-appletsrc.broken`.

All rollback steps are UNVERIFIED, because nothing was changed to roll back.

---

### Do not

1. Edit anything under `/usr/share` or `/usr/lib`. Package updates overwrite it. Put overrides under `~/.local/share/plasma/`.
2. Edit `plasma-org.kde.plasma.desktop-appletsrc` while plasmashell runs.
3. Run `konsave -a` without a snapshot. It overwrites the files it manages.
4. Run `konsave -w`, which wipes every profile.
