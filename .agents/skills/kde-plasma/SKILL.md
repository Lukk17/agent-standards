---
name: kde-plasma
description: 'Changing KDE Plasma 6 safely from the command line: panels, widgets and plasmoids through the Plasma scripting API and evaluateScript, widget plugin ids, kreadconfig6 and kwriteconfig6, which file under ~/.config holds what, KWin effects, window rules, tiling and virtual desktops, global shortcuts in kglobalshortcutsrc, color scheme, Plasma theme, cursor, icons, look-and-feel and wallpaper, konsave profiles, and restarting plasmashell. Also building, testing and publishing a plasmoid, and making a Plasma Style or Global Theme. Use when you say "add a widget to the panel", "move the clock", "what is the plugin id", "change the color scheme", "bind a shortcut", "disable the blur effect", "save my desktop with konsave", "plasmashell is stuck", "restore my panel layout", "write a plasmoid", "publish my widget on the KDE Store", "make a Plasma theme", or "build a Global Theme". Not for packages, audio, systemd or snapshots, use `arch-linux`, and not for CachyOS defaults or the login manager, use `cachyos`.'
---

# KDE Plasma 6 Administration

How to read and change a Plasma 6 desktop through its live interfaces, so a change applies at once, is easy to read back, and has a snapshot behind it. Plasma rewrites several of its own files while it runs, which is why the live API comes first and a hand edit comes last.

Baseline: Plasma 6.7 and KWin 6.7 on Wayland, Qt 6.12, verified on one CachyOS host on 2026-10-13. Commands that were not executed are marked UNVERIFIED in the topic files.

| Task | Open |
|---|---|
| Snapshot before a change, restart plasmashell, roll back | [safety.md](references/safety.md) |
| Read the layout, add, remove, reorder or configure panels and widgets | [panels-and-widgets.md](references/panels-and-widgets.md) |
| Find a widget plugin id, install a plasmoid | [widget-plugin-ids.md](references/widget-plugin-ids.md) |
| `kreadconfig6`, `kwriteconfig6`, which file holds what, reloading | [config-files.md](references/config-files.md) |
| Color scheme, Plasma theme, cursor, icons, look-and-feel, wallpaper | [theming.md](references/theming.md) |
| Global shortcuts and `kglobalshortcutsrc` | [shortcuts.md](references/shortcuts.md) |
| KWin effects, window rules, tiling, virtual desktops | [kwin.md](references/kwin.md) |
| Save, export, import and apply konsave profiles | [konsave.md](references/konsave.md) |
| Build, test, package and publish a Plasma 6 widget (plasmoid) | [widget-development.md](references/widget-development.md) |
| Make a Plasma Style, color scheme, style or decoration fork, icon theme or Global Theme safely | [theme-development.md](references/theme-development.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`: the monitors and their scales, the owner's saved konsave profile and where its archive lives, custom widgets, and the change log. Read it before acting. This skill describes no particular layout. Read the live one with the read-only commands in [panels-and-widgets.md](references/panels-and-widgets.md), and never assume a panel or widget id.

---

### When to activate

- Any change to a panel, a widget, the system tray or a desktop containment
- `kreadconfig6`, `kwriteconfig6`, or a file under `~/.config` that Plasma or KWin owns
- KWin effects, window rules, tiling layouts or virtual desktops
- Global shortcuts
- Themes, colors, cursors, icons, look-and-feel packages or wallpapers
- konsave, or restarting, recovering or rolling back plasmashell

---

### When not to activate

- Installing or upgrading Plasma packages, or KDE breaking after an upgrade, use `arch-linux`
- `cachyos-kde-settings`, `/etc/skel` or the login manager, use `cachyos`
- Audio devices and volume routing, use `arch-linux`

---

### Hard rules

1. Snapshot before any write, see [safety.md](references/safety.md). No exception for a tiny edit.
2. Prefer the live interfaces (`evaluateScript`, `plasma-apply-*`, `kwriteconfig6 --notify`) over editing files. plasmashell rewrites `plasma-org.kde.plasma.desktop-appletsrc` on exit and on its own schedule, so a hand edit made while it runs is lost or merged badly.
3. Never touch `/usr/share` or `/usr/lib`. Everything user level lives under `~/.config` and `~/.local/share`.
4. Use `qdbus6`. Check with `command -v qdbus6 qdbus`, because plain `qdbus` is often absent on Plasma 6.
5. Restart plasmashell through its user unit, `systemctl --user restart plasma-plasmashell`, never `kquitapp6 plasmashell && plasmashell`. The unit restarts on failure and a manual launch fights it.
6. After a change, read it back with `kreadconfig6` or a read-only script, and report what you saw.

---

### Related skills

- `arch-linux` owns packages, partial upgrades, journal triage and audio
- `cachyos` owns the CachyOS defaults package and the login manager
- `bash` owns any script that wraps these commands

---

### Checklist

- [ ] `MACHINE.md` read, and the live layout read before any panel change
- [ ] Config files copied and the layout dumped before the first write
- [ ] The live API used, or plasmashell stopped before a hand edit
- [ ] Nothing written under `/usr/share` or `/usr/lib`
- [ ] The change read back and reported
- [ ] The change and its undo recorded in the `MACHINE.md` change log
