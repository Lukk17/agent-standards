# Configuration Files

Contents:

- [Read](#read)
- [Write](#write)
- [Which file holds what](#which-file-holds-what)
- [Reload after a change](#reload-after-a-change)
- [Editing the appletsrc by hand](#editing-the-appletsrc-by-hand)

Everything lives under `~/.config`. Read with `kreadconfig6`, write with `kwriteconfig6`. The rules live in [SKILL.md](../SKILL.md).

Both tools take `--file`, `--group` (repeat it for a nested group) and `--key`. Verified from `--help` on one host: neither has a `--version` flag, `kwriteconfig6` also has `--type bool`, `--delete` and `--notify`, and `kreadconfig6` has `--default`, `--dump` and `--include-globals`.

---

### Read

Verified, read-only:

```bash
kreadconfig6 --file kdeglobals --group General --key ColorScheme
```

```bash
kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage
```

```bash
kreadconfig6 --file kdeglobals --group Icons --key Theme
```

```bash
kreadconfig6 --file kcminputrc --group Mouse --key cursorTheme
```

```bash
kreadconfig6 --file plasmarc --group Theme --key name
```

```bash
kreadconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme
```

Calling `kreadconfig6 kdeglobals General ColorScheme` without the flags prints the usage text and reads nothing.

A nested group such as `[Containments][<panel id>][Applets][<widget id>]` is `--group Containments --group <panel id> --group Applets --group <widget id> --key plugin`.

---

### Write

UNVERIFIED, because these change settings:

```bash
kwriteconfig6 --file kwinrc --group Windows --key FocusStealingPreventionLevel 2
```

```bash
kwriteconfig6 --file kdeglobals --group General --key ColorScheme BreezeDark --notify
```

Booleans need `--type bool true`. `--notify` tells running applications the file changed. KWin and plasmashell need an explicit reload, below.

---

### Which file holds what

| File | Holds |
|---|---|
| `plasma-org.kde.plasma.desktop-appletsrc` | every panel and desktop containment, and every widget with its configuration |
| `plasmashellrc` | per-panel view geometry and shell settings |
| `kdeglobals` | color scheme, icon theme, look-and-feel package, fonts, general UI |
| `plasmarc` | Plasma desktop theme |
| `kcminputrc` | cursor theme and size, mouse and touchpad |
| `kwinrc` | window manager: desktops, tiling, effects, focus, Xwayland scale |
| `kwinoutputconfig.json` | monitor layout and scale |
| `kglobalshortcutsrc` | global shortcuts, see [shortcuts.md](shortcuts.md) |
| `kwinrulesrc` | window rules, absent until the first rule is created |
| `plasma-workspace/env/` | per-login environment scripts |

---

### Reload after a change

For `kwinrc` and `kwinrulesrc`, the method exists on the verified host:

```bash
qdbus6 org.kde.KWin /KWin org.kde.KWin.reconfigure
```

For the appletsrc, `plasmashellrc` and `plasmarc`:

```bash
systemctl --user restart plasma-plasmashell
```

Colors, icons and cursors are better applied with the `plasma-apply-*` tools, see [theming.md](theming.md), because they broadcast the change to running applications.

---

### Editing the appletsrc by hand

The last resort.

1. Snapshot, see [safety.md](safety.md).
2. `systemctl --user stop plasma-plasmashell`.
3. Edit. Widget order is `AppletOrder` under `[Containments][<panel id>][General]`, a semicolon list of widget ids. System tray hidden items are `extraItems` under the tray's own `[General]` group.
4. `systemctl --user start plasma-plasmashell`, then read the layout back.

UNVERIFIED as a procedure.
