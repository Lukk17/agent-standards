# Scope

Companion reference for the [kde-plasma](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

Changing KDE Plasma 6 safely from the command line: panels and widgets through the scripting API, kwriteconfig6, KWin effects and rules, shortcuts, themes and konsave, plus building and publishing plasmoids and themes.

- Any change to a panel, a widget, the system tray or a desktop containment
- `kreadconfig6`, `kwriteconfig6`, or a file under `~/.config` that Plasma or KWin owns
- KWin effects, window rules, tiling layouts or virtual desktops
- Global shortcuts
- Themes, colors, cursors, icons, look-and-feel packages or wallpapers
- konsave, or restarting, recovering or rolling back plasmashell
- Writing, testing, packaging or publishing a plasmoid, or building a theme set
- Also covers panels, widgets and plasmoids through the Plasma scripting API and evaluateScript, widget plugin ids, kreadconfig6 and kwriteconfig6, which file under ~/.config holds what, KWin effects, window rules, tiling and virtual desktops, global shortcuts in kglobalshortcutsrc, color scheme, Plasma theme, cursor, icons, look-and-feel and wallpaper, konsave profiles, and restarting plasmashell. Also building, testing and publishing a plasmoid, and making a Plasma Style or Global Theme
- The user says "add a widget to the panel", "bind a shortcut", "plasmashell is stuck", "write a plasmoid", "move the clock", "what is the plugin id", "change the color scheme", "disable the blur effect", "save my desktop with konsave", "restore my panel layout", "publish my widget on the KDE Store", "make a Plasma theme" or "build a Global Theme"

---

### When not to activate

- Installing or upgrading Plasma packages, or KDE breaking after an upgrade, use `arch-linux`
- `cachyos-kde-settings`, `/etc/skel` or the login manager, use `cachyos`
- Audio devices and volume routing, use `arch-linux`

---

### Related skills

- `arch-linux` owns packages, partial upgrades, journal triage and audio
- `cachyos` owns the CachyOS defaults package and the login manager
- `bash` owns any script that wraps these commands
