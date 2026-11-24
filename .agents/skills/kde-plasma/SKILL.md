---
name: kde-plasma
description: 'KDE Plasma 6 from the command line: panels, widgets, KWin, shortcuts, themes, konsave, plasmoids. Use when the user says "add a widget to the panel" or "plasmashell is stuck". Not for packages, use `arch-linux`.'
metadata:
  version: "1.1.0"
---

# KDE Plasma 6 Administration

How to read and change a Plasma 6 desktop through its live interfaces, so a change applies at once, is easy to read back, and has a snapshot behind it. Plasma rewrites several of its own files while it runs, which is why the live API comes first and a hand edit comes last.

Written for Plasma 6 and KWin 6 on Wayland, with Qt 6.

The commands that ran were run on one CachyOS host, and commands that were not executed are marked UNVERIFIED in the topic files.

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
| Call a Plasma change done | [checklist.md](references/checklist.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`. Read it before acting. This skill holds no facts about any single machine.

For this skill they are the monitors and their scales, the owner's saved konsave profile and where its archive lives, custom widgets, and the change log. This skill describes no particular layout. Read the live one with the read-only commands in [panels-and-widgets.md](references/panels-and-widgets.md), and never assume a panel or widget id.

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
