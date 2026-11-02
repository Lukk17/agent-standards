# Theming

Applying a theme with a tool broadcasts the change to running applications, so prefer the tools over `kwriteconfig6`. The rules live in [SKILL.md](../SKILL.md).

---

### List what is installed

Verified, read-only:

```bash
lookandfeeltool -l
```

```bash
plasma-apply-colorscheme --list-schemes
```

```bash
plasma-apply-cursortheme --list-themes
```

```bash
plasma-apply-desktoptheme --list-themes
```

```bash
ls /usr/share/icons ~/.local/share/icons
```

Read the current values with the `kreadconfig6` commands in [config-files.md](config-files.md) and record them in the snapshot before changing anything.

---

### Apply

UNVERIFIED, these change the session:

```bash
plasma-apply-colorscheme BreezeDark
```

```bash
plasma-apply-cursortheme breeze_cursors
```

```bash
plasma-apply-desktoptheme breeze-dark
```

```bash
lookandfeeltool -a org.kde.breezedark.desktop
```

```bash
plasma-apply-wallpaperimage /path/to/image.png
```

Use the names exactly as the list commands print them. For cursors that is the id in brackets, such as `breeze_cursors`, not the display name. A look-and-feel package overwrites the color scheme, the Plasma theme and the cursor together, so apply it first and the individual pieces after.

The icon theme has no `plasma-apply-*` tool. Write the key and let applications follow, logging out and in if some do not. UNVERIFIED:

```bash
kwriteconfig6 --file kdeglobals --group Icons --key Theme <name> --notify
```

---

### Where custom themes go

`~/.local/share/color-schemes`, `~/.local/share/plasma/desktoptheme`, `~/.local/share/plasma/look-and-feel` and `~/.local/share/icons`. Never under `/usr/share`.
