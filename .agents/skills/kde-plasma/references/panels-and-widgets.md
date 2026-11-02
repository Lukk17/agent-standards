# Panels and Widgets

Contents:

- [Calling it](#calling-it)
- [Read the live layout](#read-the-live-layout)
- [Scripting API](#scripting-api)
- [Recipes](#recipes)
- [plasma-apply tools](#plasma-apply-tools)

Read this before reading or changing a panel, a widget or a desktop containment. The rules live in [SKILL.md](../SKILL.md).

The entry point is the D-Bus service `org.kde.plasmashell`, object `/PlasmaShell`, method `evaluateScript(QString)`, which returns whatever the script `print()`s. Check it exists with `qdbus6 org.kde.plasmashell /PlasmaShell`. API names were checked against `https://develop.kde.org/docs/plasma/scripting/api/`.

---

### Calling it

```bash
qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript 'print("hi")'
```

For anything longer than a line, put the script in a variable through a heredoc and pass the variable:

```bash
SCRIPT=$(cat <<'JS'
panels().forEach(function (p) { print(p.id + " " + p.location); });
JS
)
qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "$SCRIPT"
```

Other `org.kde.PlasmaShell` methods: `dumpCurrentLayoutJS`, `toggleWidgetExplorer`, `toggleDashboard`, `refreshCurrentShell`, `setWallpaper`, `wallpaper(screen)`, property `editMode`. `loadLookAndFeelDefaultLayout` and `changeShell` replace the whole layout, never call them without a snapshot.

---

### Read the live layout

Read-only. Run this before any change, because panel and widget ids differ on every machine and change when a panel is recreated:

```bash
qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript 'var out=[]; panels().forEach(function(p){out.push("PANEL id="+p.id+" loc="+p.location+" h="+p.height+" screen="+p.screen+" hiding="+p.hiding+" alignment="+p.alignment+" widgets="+p.widgetIds.length); p.widgetIds.forEach(function(i){out.push("  "+i+" "+p.widgetById(i).type)})}); desktops().forEach(function(d){out.push("DESKTOP id="+d.id+" screen="+d.screen+" wp="+d.wallpaperPlugin+" widgets="+d.widgetIds.length); d.widgetIds.forEach(function(i){out.push("  "+i+" "+d.widgetById(i).type)})}); print(out.join("\n"))'
```

The whole layout as replayable JavaScript:

```bash
qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.dumpCurrentLayoutJS
```

In that dump panel height is in grid units, while `panel.height` inside a script returned pixels on the verified host. Do not mix the two.

---

### Scripting API

Names confirmed in the documentation. Writes were not executed.

Globals: `panels()`, `panelById(id)`, `desktops()`, `desktopById(id)`, `desktopForScreen(n)`, `desktopsForActivity(id)`, `createActivity(name[, plugin])`. `getApiVersion(1)` appears in live dumps but not on the documentation page.

Panel properties: `location` (top, bottom, left, right, floating), `height`, `alignment` (left, center, right), `hiding` (none, autohide, dodgewindows, windowsgobelow), `lengthMode` (fill, fit, custom), `minimumLength`, `maximumLength`, `offset`, `screen`, `floating`. `opacity` appears in live dumps but not on the documentation page.

Containment, which is a panel or a desktop: `widgetIds`, `widgets([type])`, `widgetById(id)`, `addWidget(typeName[, x, y, w, h])`, `addWidget(existingWidget, x, y)` to move a widget between containments, `locked`, `remove()`, `reloadConfig()`.

Widget: `id`, `type`, `index` (position within a panel, read-write), `remove()`, `readConfig(key, default)`, `writeConfig(key, value)`, `currentConfigGroup = ["Group", "Sub"]`, `configKeys`, `configGroups`, `readGlobalConfig`, `writeGlobalConfig`, `reloadConfig()`, `showConfigurationInterface()`. The documentation page spells the last one `showConfigurationInteface`, so try both.

---

### Recipes

All UNVERIFIED. Run each only after the snapshot in [safety.md](safety.md), with the ids read from the live layout above.

Add a widget to the end of a panel:

```js
var p = panelById(<panel id>);
var w = p.addWidget("org.kde.plasma.kickoff");
print(w.id);
```

Configure a widget. Keys differ per widget, so read them first with `w.configKeys` and `w.configGroups`:

```js
var w = panelById(<panel id>).widgetById(<widget id>);
w.currentConfigGroup = ["General"];
w.writeConfig("icon", "start-here-kde");
w.reloadConfig();
```

Remove a widget:

```js
panelById(<panel id>).widgetById(<widget id>).remove();
```

Reorder: set `w.index` in a script, or edit `AppletOrder` under `[Containments][<panel id>][General]` in the appletsrc, a semicolon separated list of widget ids. The file route needs plasmashell stopped, see [config-files.md](config-files.md).

Create a panel:

```js
var p = new Panel;
p.location = "bottom";
p.height = 44;
p.addWidget("org.kde.plasma.taskmanager");
```

Set the wallpaper on one desktop, in the path form the documentation shows:

```js
var d = desktopForScreen(0);
d.wallpaperPlugin = "org.kde.image";
d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
d.writeConfig("Image", "file:///usr/share/wallpapers/Next/contents/images/1920x1080.png");
```

Widget ids for `addWidget` come from [widget-plugin-ids.md](widget-plugin-ids.md). A wrong id does not always throw, so read the panel back after adding.

---

### plasma-apply tools

Present and listing verified on one host, applying not run.

| Tool | List | Apply |
|---|---|---|
| `plasma-apply-colorscheme` | `--list-schemes` | `plasma-apply-colorscheme BreezeDark` |
| `plasma-apply-cursortheme` | `--list-themes` | `plasma-apply-cursortheme breeze_cursors` |
| `plasma-apply-desktoptheme` | `--list-themes` | `plasma-apply-desktoptheme breeze-dark` |
| `plasma-apply-wallpaperimage` | none | `plasma-apply-wallpaperimage /path/img.png` |

More in [theming.md](theming.md).
