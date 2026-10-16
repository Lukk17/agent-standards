# Global Shortcuts

The file is `~/.config/kglobalshortcutsrc`, with one group per component such as `kwin`, `plasmashell`, `ksmserver`, `mediacontrol` and `org_kde_powerdevil`, plus a group for each application that registered shortcuts. List the groups with `grep '^\[' ~/.config/kglobalshortcutsrc`. The rules live in [SKILL.md](../SKILL.md).

---

### Line format

Verified by reading the file on one host:

```ini
Edit Tiles=Meta+T,Meta+T,Toggle Tiles Editor
Expose=Ctrl+F9\tMeta+F9,Ctrl+F9\tMeta+F9,Toggle Present Windows (Current desktop)
Cycle Overview=none,none,Cycle through Overview and Grid View
```

The fields are the active keys, the default keys, and the friendly name. Several keys for one action are separated by a literal tab written as `\t`, and `none` means unbound.

---

### Read

Verified, read-only:

```bash
kreadconfig6 --file kglobalshortcutsrc --group kwin --key "Edit Tiles"
```

```bash
grep -n 'Overview' ~/.config/kglobalshortcutsrc
```

The live registry is on D-Bus, service `org.kde.kglobalaccel`, path `/kglobalaccel`, with methods `allComponents`, `shortcutKeys(actionId)`, `setShortcutKeys(...)` and `getGlobalShortcutsByKey(key)`. On the verified host `qdbus6` could not print some return values without `--literal`, so reading the file is simpler for lookups.

---

### Change a shortcut

Preferred: System Settings, Keyboard, Shortcuts, because it asks kglobalaccel to re-register the binding.

Scripted route, UNVERIFIED:

1. Snapshot, see [safety.md](safety.md).
2. Check the key is free: `grep -n 'Meta+W' ~/.config/kglobalshortcutsrc`.
3. Write the line: `kwriteconfig6 --file kglobalshortcutsrc --group kwin --key "Overview" "Meta+W,Meta+W,Toggle Overview"`.
4. kglobalaccel reads the file at startup, so a running session may ignore the edit. Log out and in, or restart its user unit after confirming the name with `systemctl --user list-units 'plasma-*'`.

A shortcut that launches a program is a `.desktop` file under `~/.local/share/applications` with an `X-KDE-Shortcuts=` key, which kglobalaccel picks up. UNVERIFIED.
