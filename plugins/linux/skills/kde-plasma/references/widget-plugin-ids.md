# Finding Widget Plugin IDs

The id passed to `addWidget("...")` is the plugin name, the same string `widget.type` returns. The rules live in [SKILL.md](../SKILL.md).

---

### From the live session

Every id currently placed, read-only:

```bash
qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript 'var s={}; panels().concat(desktops()).forEach(function(c){c.widgetIds.forEach(function(i){s[c.widgetById(i).type]=1})}); print(Object.keys(s).join("\n"))'
```

---

### From installed packages

User scope, under `~/.local/share/plasma/plasmoids`:

```bash
kpackagetool6 --list --type Plasma/Applet
```

System scope, under `/usr/share/plasma/plasmoids`:

```bash
kpackagetool6 --list --type Plasma/Applet --global
```

Two traps:

1. The two lists are separate. Presets a widget installs per user, such as system monitor presets, show only in the user list.
2. Compiled applets are not kpackages. Most of Plasma's own widgets, and many third party ones, are `.so` plugins, so `kpackagetool6` never lists them and `kpackagetool6 --show <id>` answers `Can't find plugin metadata`. List the plugin directory instead, where the file name minus `.so` is the plugin id:

```bash
ls /usr/lib/qt6/plugins/plasma/applets/
```

---

### From a package to its ids

```bash
pacman -Ql <package> | grep -E 'plugins/plasma/applets|share/plasma/plasmoids'
```

A package can ship more than one id, for example a launcher and a panel variant of the same widget, and can register its own global shortcut component. Check `kglobalshortcutsrc` after installing one, see [shortcuts.md](shortcuts.md).

---

### Installing a plasmoid

UNVERIFIED. User scope only:

```bash
kpackagetool6 --type Plasma/Applet --install ./plasmoid-dir
```

```bash
kpackagetool6 --type Plasma/Applet --upgrade ./plasmoid-dir
```

```bash
kpackagetool6 --type Plasma/Applet --remove <id>
```

Prefer a distribution package when one exists, and never use `--global`. A widget a konsave profile references must be installed before that profile is applied, or its slot comes up empty.
