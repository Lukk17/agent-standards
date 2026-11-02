# KWin: Effects, Rules, Tiling, Desktops

The D-Bus service is `org.kde.KWin` and the main file is `~/.config/kwinrc`. The rules live in [SKILL.md](../SKILL.md).

Read the versions, outputs and compositor state first. Verified, read-only:

```bash
qdbus6 org.kde.KWin /KWin org.kde.KWin.supportInformation
```

---

### Reconfigure

The method exists on the verified host. The call reloads `kwinrc` and `kwinrulesrc`:

```bash
qdbus6 org.kde.KWin /KWin org.kde.KWin.reconfigure
```

---

### Effects

The `/Effects` object has the properties `loadedEffects`, `activeEffects` and `listOfEffects`, and the methods `isEffectLoaded(name)`, `loadEffect`, `unloadEffect`, `toggleEffect` and `reconfigureEffect`. Verified read-only:

```bash
qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.loadedEffects
```

```bash
qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.isEffectLoaded blur
```

`loadEffect` and `unloadEffect` last only until KWin restarts. To persist, write the plugin switch under `[Plugins]` in `kwinrc`, then reconfigure. UNVERIFIED key naming:

```bash
kwriteconfig6 --file kwinrc --group Plugins --key blurEnabled --type bool false
```

---

### Read the current kwinrc

```bash
kreadconfig6 --file kwinrc --dump
```

Groups to expect: `[Desktops]` with `Number` and `Rows`, `[Tiling]` subgroups per desktop and output, `[Windows]` for focus behaviour, `[Xwayland]` for the scale, and `[Plugins]` only once an effect was toggled away from its default.

---

### Tiling

Layouts live in the `[Tiling]` groups as JSON in a `tiles` key. Edit them with the built-in editor, action `Edit Tiles`, bound to Meta+T by default, never by hand.

---

### Virtual desktops

`/VirtualDesktopManager` and `org.kde.KWin.currentDesktop` and `setCurrentDesktop` exist. Count and rows are `Number` and `Rows` under `[Desktops]`. Switching desktop is a session change. UNVERIFIED.

---

### Window rules

`~/.config/kwinrulesrc` does not exist until the first rule is created. Create rules in System Settings, Window Management, Window Rules, which writes the file and reconfigures KWin. A hand-written rules file needs `[General]` with `count=N` and `rules=` listing the group names. UNVERIFIED.

---

### KWin scripts

D-Bus `/Scripting` offers `loadScript(path[, pluginName])`, `unloadScript(name)` and `isScriptLoaded(name)`, verified present. Prefer installing a script as a package, UNVERIFIED:

```bash
kpackagetool6 --type KWin/Script --install <dir>
```
