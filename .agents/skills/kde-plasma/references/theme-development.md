# Theme Development

How to make a Plasma 6 theme set safely: a Plasma Style, a color scheme, an application style and window decoration, an icon theme and a Global Theme that selects them. The rules live in [SKILL.md](../SKILL.md). Listing and applying installed themes, and where user themes go, is in [theming.md](theming.md) and is not repeated here.

Checked on 2026-10-23 against libplasma, plasma-workspace and KWin v6.7.5, KSvg and KPackage v6.31.0, konsave 2.3.0, the develop.kde.org theme pages and the freedesktop icon theme specification. Sources are listed at the end. Commands that were not executed are marked UNVERIFIED.

---

### Prove it before anyone installs it

The owner's rule: no trial and error on the user's desktop. One proven attempt, not a series of guesses.

1. Read the source for exactly which file Plasma loads in this case: the folder selector, the element prefix, the fallback theme. The sections below give the rules for Plasma 6.7.5.
2. Render the result in an isolated session that matches the real setup: the same Plasma version, Wayland, KWin blur on, no host folder mounted, a throwaway home.
3. State what is verified and what is not. If the result cannot be proven, say so instead of asking the user to test it.
4. Print every command the user must run, and the undo for each, in code blocks in the same reply.
5. Take the backup below before anything is applied.

A render recipe, UNVERIFIED as a whole: a container with plasma-workspace and KWin from a pinned Arch Linux Archive date, the theme copied into the throwaway `~/.local/share`, `kwin_wayland --virtual --width 1920 --height 1080` with plasmashell or `plasmawindowed <widget id>` inside it, and a screenshot taken in the container. `kwin_wayland --virtual` exists in KWin 6.7.5 (measured from `--help`), and a real theme set measured its layout with one and two KWin virtual outputs in such a container. Whether the blur renders on the virtual output was not checked. If the blur cannot be rendered, say that the glass look itself is unproven.

---

### The pieces

| Piece | Package type or form | Selected by |
|---|---|---|
| Plasma Style | KPackage `Plasma/Theme`, folder in `plasma/desktoptheme/` | `plasmarc` `[Theme] name` |
| Color scheme | `<Name>.colors` in `color-schemes/` | `kdeglobals` `[General] ColorScheme` |
| Application style | Qt style plugin under `/usr/lib/qt6/plugins/styles/` | `kdeglobals` `[KDE] widgetStyle` |
| Window decoration | KDecoration3 plugin under `/usr/lib/qt6/plugins/org.kde.kdecoration3/` | `kwinrc` `[org.kde.kdecoration2]` `library` and `theme` |
| Icons | folder with `index.theme` in `icons/` | `kdeglobals` `[Icons] Theme` |
| Cursors | folder with `index.theme` and `cursors/` in `icons/` | `kcminputrc` `[Mouse] cursorTheme` |
| Global Theme | KPackage `Plasma/LookAndFeel`, folder in `plasma/look-and-feel/` | `plasma-apply-lookandfeel` |

The group names are the ones `KLookAndFeelManager` writes (plasma-workspace v6.7.5 `libklookandfeel/klookandfeelmanager.cpp` lines 186 to 288). The decoration group is still called `org.kde.kdecoration2`. Compiled pieces (style and decoration) live under `/usr/lib`, so they ship only in a distribution package, never as a hand copy.

---

### Plasma Style package

```text
glass-example/
  metadata.json
  plasmarc
  colors
  dialogs/background.svg
  widgets/background.svg
  widgets/panel-background.svg
  widgets/tooltip.svg
  translucent/dialogs/background.svg
  translucent/widgets/background.svg
  translucent/widgets/panel-background.svg
  solid/dialogs/background.svg
  opaque/dialogs/background.svg
```

1. `metadata.json` needs `"KPackageStructure": "Plasma/Theme"` beside `KPlugin` with `Id`, `Name`, `Version` and `License`. KPackage lists a package only when that key matches the requested type (KPackage v6.31.0 `src/kpackage/packageloader.cpp` lines 211 to 216), so without it `kpackagetool6 --type Plasma/Theme --list` does not show the style.
2. `plasmarc` holds the theme settings. libplasma reads it first and falls back to `metadata.desktop` (`src/plasma/private/theme_p.cpp` lines 32 to 42).
3. `colors` is optional. When present, Plasma parts use it instead of the system color scheme (`theme_p.cpp` lines 405 to 414).
4. A fork keeps every original file and changes only what it must, with a CHANGES file naming each change and its date, as the GPL asks of modified files.

---

### Which folder Plasma uses

libplasma picks a selector folder (`theme_p.cpp` lines 169 to 190):

| Situation | Folder tried first |
|---|---|
| Compositing on and the blur effect available | `translucent/` |
| Compositing on, no blur effect | none, the top-level files |
| X11 without compositing | `opaque/` |

On Wayland "blur effect available" means KWin announced the blur capability of the background effect protocol (libplasma `src/plasma/private/blureffectwatcher.cpp` lines 44 to 47). KWin 6.7.5 announces it when its blur effect loads and withdraws it when the effect unloads (`src/plugins/blur/blur.cpp` lines 166 and 189). The develop.kde.org Theme Elements page still says the translucent folder is used "when the KWin Background Contrast effect is enabled". That is outdated for 6.7, the source checks blur. The X11 path was not checked.

KSvg looks for the whole file in the selector folder and uses the top-level file only when the selector folder has none (KSvg v6.31.0 `src/ksvg/private/imageset_p.cpp` lines 238 to 268). It replaces the file, it does not merge elements. So with blur on, an edit to `widgets/background.svg` changes nothing while `translucent/widgets/background.svg` exists. Change both copies, or check which one is loaded before you edit.

`solid/` is a prefix, not a selector: a dialog or window that asks for a solid background loads `solid/dialogs/background` (libplasma `src/plasmaquick/plasmawindow.cpp` lines 216 to 220, `src/plasmaquick/dialog.cpp` lines 237 to 239). The develop.kde.org page gives the example of a panel with adaptive opacity next to a maximized window.

---

### Which pieces each part draws

| Part | File and elements |
|---|---|
| Desktop widget with a standard background | `widgets/background`, `blurred-` elements when the file has them |
| Desktop widget with a translucent background | `widgets/translucentbackground` |
| Plasma menus, popups, drawers and dialogs from Plasma Components | `widgets/background`, the normal elements |
| Panel popups and other Plasma windows | `dialogs/background` |
| Panels | `widgets/panel-background` |
| Tooltips | `widgets/tooltip`, `solid/widgets/tooltip` |

Desktop widgets: plasma-workspace v6.7.5 `components/containmentlayoutmanager/qml/BasicAppletContainer.qml` uses the prefix `blurred` (line 92) when the widget has a standard background and the file has `blurred-` elements (lines 108 to 113), and `blurred-mask-` elements as the mask (line 245). plasmashell then blurs the wallpaper itself in QML (line 265), so this blur does not come from KWin. Plasma Components `Menu.qml`, `Popup.qml`, `Dialog.qml` and `Drawer.qml` use `widgets/background` with no prefix (libplasma `src/declarativeimports/plasmacomponents3/Menu.qml` lines 98 to 102). So a style can make desktop widgets more see-through by changing only the `blurred-` elements and keep menus readable with the normal ones.

---

### plasmarc and the contrast effect

```ini
[ContrastEffect]
enabled=false
contrast=1
intensity=1
saturation=1

[BlurBehindEffect]
enabled=true

[AdaptiveTransparency]
enabled=true

[Settings]
FallbackTheme=breeze
```

| Key | Default when missing | Source |
|---|---|---|
| `[ContrastEffect] enabled` | false | `theme_p.cpp` lines 346 to 359 |
| `contrast` | 0.45 on a dark background color, 0.3 on a light one | `src/plasma/theme.cpp` lines 174 to 187 |
| `intensity` | 0.6 dark, 1.4 light | `theme.cpp` lines 189 to 199 |
| `saturation` | 1.7 | `theme.cpp` lines 201 to 207 |
| `[BlurBehindEffect] enabled` | true | `theme_p.cpp` lines 372 to 381 |
| `[AdaptiveTransparency] enabled` | false | `theme_p.cpp` lines 361 to 370 |
| `[Settings] FallbackTheme` | none | `theme_p.cpp` lines 434 to 448 |

KWin removed its contrast effect in Plasma 6.5: KWin commit `6d947619` "Remove the contrast effect", message "main parts are inside blur right now", first tagged v6.4.90 and v6.5.0. In KWin 6.7.5 the blur effect applies one fixed color matrix, with the saturation from `kwinrc` `[Effect-blur] Saturation` (default 150, meaning 1.5) and contrast 1.0 (`src/plugins/blur/blur.cpp` line 259, `src/plugins/blur/blur.kcfg`). libplasma still sends the style's contrast values to the compositor (`plasmawindow.cpp` lines 167 to 171, `dialog.cpp` line 249), and no code in the KWin 6.7.5 sources reads them. Inferred, high confidence: on 6.5 and later `[ContrastEffect]` no longer changes panels and popups.

It still changes desktop widgets. `BasicAppletContainer.qml` lines 230 and 231 apply `backgroundContrast - 1.0` and `backgroundSaturation - 1.0` to plasmashell's own wallpaper blur, whatever `enabled` says. With the missing-key defaults that is a darker, stronger colored blur. `contrast=1` and `saturation=1` give a neutral blur of the real wallpaper.

---

### Color schemes

A `.colors` file is a KConfig file. A color with a fourth value carries alpha, for example `[Colors:Window] BackgroundNormal=49,49,58,128` for a window background about 50 percent see-through.

1. The application style decides whether that alpha does anything. A Darkly based style makes the window translucent and asks KWin for blur when the Window color alpha is below 255 (`Helper::shouldWindowHaveAlpha`, read in a fork of Darkly 0.5.41). Breeze was not checked, UNVERIFIED.
2. When colors are applied, the inactive `[Colors:Header]` is filled from `[Colors:Window]` unless the accent color tints the header (plasma-workspace v6.7.5 `kcms/colors/colorsapplicator.cpp` lines 249 to 268). An inactive title bar therefore gets the see-through window color.
3. Applications that draw their own background, such as most GTK and Electron applications, stay opaque.

---

### Application style and window decoration forks

1. Rename everything in the fork, not only the file names: plugin file names and ids, the style key, the config file (for example `glassrc`), D-Bus names, translation domains and the C++ namespace. The decoration settings page loads every `org.kde.kdecoration3` plugin into one process to list them (KWin v6.7.5 `src/kcms/decoration/decorationmodel.cpp` lines 115 to 118). Two copies with the same symbols in one process can collide, inferred. A full rename lets the original stay installed with its own settings.
2. A decoration plugin without themes is listed with its theme name equal to its `Name` (`decorationmodel.cpp` line 150), so a Global Theme selects it with `library=<plugin id>` and `theme=<Name>`.
3. Change defaults in the `.kcfg` files and also in any fallback written in the code, and update the upstream unit tests that check those defaults.
4. Keep the upstream license headers and authors, and list every change in a CHANGES file.

---

### Icon themes

The freedesktop icon theme specification, key `Inherits`: "If an icon name is not found in the current theme, it is searched for in the inherited theme (and recursively in all the inherited themes). If no theme is specified, implementations are required to add the "hicolor" theme to the inheritance tree."

1. A theme that changes only some icons ships only those and inherits the rest, for example `Inherits=breeze-dark,hicolor`. Breeze Dark itself has `Inherits=breeze,hicolor` (measured in the installed `index.theme`).
2. Inherited themes are searched only for names the theme lacks. When an icon is replaced, remove every other copy of that name in all size folders of the theme, or a fixed-size copy can still be picked. Inferred from the lookup order in the specification.
3. List every new folder in `Directories` and give it its own section in `index.theme`.

---

### Global Theme package

```text
org.example.glass/
  metadata.json
  contents/defaults
  contents/colors
  contents/layouts/org.kde.plasma.desktop-layout.js
  contents/previews/preview.png
```

`metadata.json` carries `"KPackageStructure": "Plasma/LookAndFeel"`. The file names inside `contents/` are the definitions in plasma-workspace v6.7.5 `shell/packageplugins/lookandfeel/lookandfeel.cpp` lines 26 to 49.

`contents/defaults` names the pieces, one group per target file and group:

```ini
[kdeglobals][KDE]
widgetStyle=Glass

[kdeglobals][General]
ColorScheme=Glass

[kdeglobals][Icons]
Theme=glass

[plasmarc][Theme]
name=glass-example

[kcminputrc][Mouse]
cursorTheme=breeze_cursors

[kwinrc][org.kde.kdecoration2]
library=org.example.glass
theme=Glass
```

What applying does, read in plasma-workspace v6.7.5:

1. Each value is written to `~/.config/kdedefaults/<file>`, and the user's own value of the same key in `~/.config/<file>` is removed (`klookandfeelmanager.cpp` lines 378 to 397). The theme id goes to `~/.config/kdedefaults/package` (line 594).
2. A file the package lacks comes from `org.kde.breeze.desktop` (`lookandfeel.cpp` lines 11 and 53 to 61). A package with no splash screen therefore switches the splash to the Breeze one.
3. A color scheme named in `defaults` is found by a changed form of its name (`colorSchemeFile`, `klookandfeelmanager.cpp` lines 399 to 419). Ship the scheme as `contents/colors` so the right one is used.

---

### The layout script

plasmashell runs `contents/layouts/org.kde.plasma.desktop-layout.js`, and `org.kde.plasma.desktop-prelayout.js` before it when present (`shell/shellcorona.cpp` lines 1094 and 1126). The script uses the scripting API in [panels-and-widgets.md](panels-and-widgets.md).

Applying a layout deletes all panels and desktop widgets. `ShellCorona::loadLookAndFeelDefaultLayout` deletes every group of `plasma-org.kde.plasma.desktop-appletsrc` and loads again (`shellcorona.cpp` lines 689 to 715). Panels, desktop widgets, their settings and the wallpaper settings are gone, and only what the script builds comes back. A layout runs only on request: `plasma-apply-lookandfeel` adds it only with `--resetLayout` (`kcms/lookandfeel/tool/lnftool.cpp` lines 53 and 100), or when the layout box is ticked in System Settings.

1. Check `knownWidgetTypes` before `addWidget`. A plugin that is not installed does not fail, it becomes a placeholder showing "Could not find requested component" (libplasma `src/plasma/pluginloader.cpp` lines 140 to 146).
2. Put no personal data in the script: no account lists, e-mail addresses, recent files or usage history. Widgets start empty, and the user's own settings come back from the backup.
3. Make no wallpaper choice unless that is the point of the theme. Plasma sets its default wallpaper after the reset.

---

### Backup, apply, undo

Read the current Global Theme and keep the name for the undo:

```bash
kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage
```

Save and export a konsave profile, see [konsave.md](konsave.md):

```bash
konsave -s before-glass-20261023 -f
```

```bash
konsave -e before-glass-20261023 -d ~
```

Check the profile really holds the layout file. konsave 2.3.0 catches its own errors and writes them to `~/.cache/konsave_log.txt` (`konsave/funcs.py` lines 27 to 44), and a real theme set measured exit status 0 for a failed save in a container:

```bash
test -f ~/.config/konsave/profiles/before-glass-20261023/configs/plasma-org.kde.plasma.desktop-appletsrc
```

Apply the look only, or the look and the layout. `lookandfeeltool` is a link to `plasma-apply-lookandfeel` (measured). UNVERIFIED, these change the session:

```bash
plasma-apply-lookandfeel --apply org.example.glass
```

```bash
plasma-apply-lookandfeel --apply org.example.glass --resetLayout
```

Undo in this order. The konsave 2.3.0 KDE file list (`konsave/conf_kde.yaml`) does not include `~/.config/kdedefaults`, where the Global Theme wrote its values, so the previous Global Theme goes back first. The same theme set measured this order in a container. UNVERIFIED here:

```bash
plasma-apply-lookandfeel --apply org.kde.breezedark.desktop
```

```bash
konsave -a before-glass-20261023
```

```bash
systemctl --user restart plasma-plasmashell
```

---

### Sources

Fetched or cloned on 2026-10-23.

| Source | Version | Used for |
|---|---|---|
| https://invent.kde.org/plasma/libplasma | v6.7.5 | selectors, `plasmarc` keys and defaults, element use, missing widget placeholder |
| https://invent.kde.org/frameworks/ksvg | v6.31.0 | selector file lookup |
| https://invent.kde.org/plasma/plasma-workspace | v6.7.5 | desktop widget blur, Global Theme apply, layout reset, color applier |
| https://invent.kde.org/plasma/kwin | v6.7.5, and commit `6d947619` through the GitLab API | blur capability, blur color matrix, contrast effect removal, decoration page |
| https://invent.kde.org/frameworks/kpackage | v6.31.0 | package listing by `KPackageStructure` |
| https://invent.kde.org/documentation/develop-kde-org, `content/docs/plasma/theme/` | master at 9e4ad7ab | folder meanings, `plasmarc` |
| https://specifications.freedesktop.org/icon-theme/latest/ | latest | `Inherits` and hicolor |
| https://github.com/Prayag2/konsave | v2.3.0 | file list, error handling |
