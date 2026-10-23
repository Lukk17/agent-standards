# Widget Development

How to build, test, package and publish a Plasma 6 widget (plasmoid). The rules live in [SKILL.md](../SKILL.md). Placing an installed widget on a panel is in [panels-and-widgets.md](panels-and-widgets.md), finding its id in [widget-plugin-ids.md](widget-plugin-ids.md).

Checked on 2026-10-23 against libplasma, plasma-workspace, plasma5support and KWin v6.7.5, KPackage, KNewStuff, KWallet and frameworkintegration v6.31.0, and the develop.kde.org widget pages. Sources are listed at the end. Commands that were not executed are marked UNVERIFIED.

---

### Project layout

Only `package/` is installed and shipped. Tests, store pictures and build scripts stay outside it, as the develop.kde.org Setup page describes.

```text
weather-widget/
  package/
    metadata.json
    contents/
      ui/main.qml
      ui/CompactView.qml
      ui/FullView.qml
      ui/ConfigGeneral.qml
      config/main.xml
      config/config.qml
      code/forecast.mjs
  tests/
    unit/forecast.test.mjs
    qml/tst_widget.qml
    docker/qml.Dockerfile
  docs/store-assets/
```

---

### metadata.json

```json
{
    "KPackageStructure": "Plasma/Applet",
    "KPlugin": {
        "Authors": [{ "Name": "Example Author" }],
        "Category": "System Information",
        "Description": "Shows the weather for one city",
        "Icon": "weather-clear",
        "Id": "org.example.weather",
        "License": "GPL-3.0-or-later",
        "Name": "Weather Example",
        "Version": "1.0.0",
        "Website": "https://example.org/weather-widget"
    },
    "X-Plasma-API-Minimum-Version": "6.0"
}
```

| Key | Rule |
|---|---|
| `KPackageStructure` | `Plasma/Applet`, which makes the folder a widget package |
| `Id` | The install folder name under `~/.local/share/plasma/plasmoids/` and the id panels store. KPackage accepts only letters, digits, `_`, `-` and `.` (`^[\w\-\.]+$` in `packagejobthread.cpp`). Never change it after a release |
| `Version` | Raise it on every release and use the same value in the store form |
| `X-Plasma-API-Minimum-Version` | The Setup page: "is required to enable Plasma 6 support. Plasmoids without this key are assumed to only work with Plasma 5 and will not be made available in the UI." Set it to the oldest Plasma version you tested |
| `License` | An SPDX id, the same as the `LICENSE` file and the store form |
| `Category` | One of the names on the develop.kde.org Widget Properties page |

Ship `metadata.json` only. The Setup page calls a `metadata.desktop` file discouraged.

---

### QML entry point

The root item is a `PlasmoidItem`. The KF6 porting guide: "The root QML object of a plasmoid is now required to be a `PlasmoidItem`". The representations, the tooltip and `expanded` are properties of that root item. The attached `Plasmoid` object is the applet: `Plasmoid.configuration`, `Plasmoid.formFactor`, `Plasmoid.location`, `Plasmoid.title`, `Plasmoid.icon`, `Plasmoid.backgroundHints`.

```qml
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents

import "../code/forecast.mjs" as Forecast

PlasmoidItem {
    id: root

    readonly property bool onDesktop: Plasmoid.formFactor === PlasmaCore.Types.Planar

    preferredRepresentation: onDesktop ? fullRepresentation : compactRepresentation
    toolTipMainText: Plasmoid.title

    compactRepresentation: Kirigami.Icon {
        source: Plasmoid.icon
        MouseArea {
            anchors.fill: parent
            onClicked: root.expanded = !root.expanded
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 16
        PlasmaComponents.Label {
            text: Forecast.title(Plasmoid.configuration.city)
        }
    }
}
```

| Import | Holds |
|---|---|
| `org.kde.plasma.plasmoid` | `PlasmoidItem` and the `Plasmoid` attached object |
| `org.kde.plasma.core as PlasmaCore` | `PlasmaCore.Types` (form factors, locations, background hints) |
| `org.kde.plasma.components as PlasmaComponents` | Plasma controls (Label, Button, Menu) |
| `org.kde.kirigami as Kirigami` | `Kirigami.Units`, `Kirigami.Icon`, `Kirigami.Heading`, which replace the Plasma 5 `PlasmaCore.Units` and `PlasmaCore.IconItem` |
| `org.kde.ksvg as KSvg` | SVG theme pieces, which moved out of Plasma Framework |
| `org.kde.plasma.plasma5support as Plasma5Support` | `DataSource`, the old data engines |
| `org.kde.kcmutils as KCM` | Root types of configuration pages |

Keep the logic in plain `.mjs` modules under `contents/code/` with no Qt import, so `node --test` runs them without Qt. Qt calls `.mjs` files ECMAScript modules and imports them from QML as shown above. The QML files then only connect data to controls.

---

### Configuration

`contents/config/main.xml` is the schema. The develop.kde.org Configuration page: the properties "will be serialized into `~/.config/plasma-org.kde.plasma.desktop-appletsrc`. All properties will be accessible with `plasmoid.configuration.variableName` regardless of what group it's in."

```xml
<?xml version="1.0" encoding="UTF-8"?>
<kcfg xmlns="http://www.kde.org/standards/kcfg/1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.kde.org/standards/kcfg/1.0 http://www.kde.org/standards/kcfg/1.0/kcfg.xsd">
  <kcfgfile name=""/>
  <group name="General">
    <entry name="city" type="String">
      <default>Paris</default>
    </entry>
    <entry name="refreshMinutes" type="Int">
      <default>30</default>
      <min>5</min>
      <max>240</max>
    </entry>
  </group>
</kcfg>
```

`contents/config/config.qml` lists the tabs of the configure dialog:

```qml
import QtQuick
import org.kde.plasma.configuration

ConfigModel {
    ConfigCategory {
        name: i18n("General")
        icon: "configure"
        source: "ConfigGeneral.qml"
    }
}
```

The porting guide: the root of a configuration page "now must be one of the KCM components from the `org.kde.kcmutils` import", most often `KCM.SimpleKCM`. Each key gets a `cfg_<name>` property bound to a control, and Apply writes it:

```qml
import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    property alias cfg_city: cityField.text

    Kirigami.FormLayout {
        QQC2.TextField {
            id: cityField
            Kirigami.FormData.label: i18n("City:")
        }
    }
}
```

---

### Data that must survive a reset

The applet configuration lives inside the panel layout file, so it goes away with the layout. Applying a Global Theme layout runs `ShellCorona::loadLookAndFeelDefaultLayout`, which deletes every group of `plasma-org.kde.plasma.desktop-appletsrc` (plasma-workspace v6.7.5 `shell/shellcorona.cpp` lines 705 to 710). Removing the widget and adding it again starts it empty, and a second copy of the widget has its own separate configuration.

| Keep in the applet configuration | Keep in an own settings file |
|---|---|
| Look of one copy: size, font, colors, what to show | User data that took effort to enter: accounts, lists, a chosen location |
| Values that may differ between a panel copy and a desktop copy | Values every copy should share |

For an own file, use a KConfig file named after the widget with `rc` at the end, such as `~/.config/weather-widgetrc`, read and written with `kreadconfig6` and `kwriteconfig6` through the executable engine below. Rules learned from a real widget that does this:

1. Read the value back after every write, and treat the write as failed unless the file holds the new value. The exit status is not a reliable sign. Measured here on KConfig 6.31.0: `kwriteconfig6` on a new file in a read-only `XDG_CONFIG_HOME` exited 2, while that widget's own test image on KConfig 6.30 saw exit 0 in its read-only case.
2. Run both tools inside `timeout`. Measured here on KConfig 6.31.0: `kreadconfig6` with a read-only `XDG_CONFIG_HOME` never returned and was stopped by `timeout 5` with status 124.
3. Never put a user value into the command text. Pass it encoded, for example as base64 decoded inside the command with `base64 -d`, and check names against a strict pattern before building any command.
4. Read the file, apply the change, then write, so two copies do not undo each other. Read it again on a timer so a change in one copy shows in the others.
5. Migrate once: when the file has no value yet and the applet configuration has one, copy it into the file and leave the old copy untouched.
6. Never store a secret in the file. Secrets go to KWallet, below.

---

### Secrets in KWallet

Never put a key in `main.xml`, a settings file, a command line or a log. The applet configuration is plain text that backup tools and dotfile repositories copy.

Save the key from QML through the KWallet D-Bus API with the Plasma QML D-Bus module `org.kde.plasma.workspace.dbus` (plasma-workspace `components/dbus`, first released in Plasma 6.1). The installed interface `kf6_org.kde.KWallet.xml` (KWallet 6.31.0) has `openAsync(wallet, wId, appid, handleSession)`, answered by the `walletAsyncOpened` signal, then `writePassword(handle, folder, key, value, appid)` and `close`. Service `org.kde.kwalletd6`, path `/modules/kwalletd6`, both present on the verified host. The module is not described on the develop.kde.org widget pages read on 2026-10-23, so treat it as UNVERIFIED as a stable API and set `X-Plasma-API-Minimum-Version` to the version you tested.

Read the key only inside the command that uses it, so it never enters plasmashell again. kwalletd6 gives a KWallet entry the Secret Service attributes `server` (the folder), `user` (the entry name) and `type` `plaintext` (KWallet v6.31.0 `src/runtime/kwalletd/secretserviceclient.cpp` lines 28, 95, 236 and 237), so `secret-tool` finds it. Send it to curl on standard input. The curl 8.22.0 manual: "Using @- makes curl read the header file from stdin."

```bash
key=$(timeout 10 secret-tool lookup server weather-widget user api.main type plaintext) && printf 'Authorization: Bearer %s\n' "$key" | timeout 25 curl --disable --fail-with-body --proto =https --max-redirs 0 --max-time 20 --max-filesize 1048576 -H @- https://api.example.org/v1/forecast
```

UNVERIFIED as written, the pattern runs in a real widget. Known limits: at save time the key passes once through plasmashell and the session bus, and KWallet protects keys from other users, not from programs running as the same user. Say both in the README.

---

### Running local commands

`Plasma5Support.DataSource` with `engine: "executable"` runs each source name as a shell command. In plasma5support v6.7.5 `src/dataengines/executable/executable.cpp` lines 26 to 49, the source name goes to `KProcess::setShellCommand`, and the result arrives in `onNewData` with the keys `exit code`, `exit status`, `stdout` and `stderr`.

```qml
import QtQuick
import org.kde.plasma.plasma5support as Plasma5Support

Plasma5Support.DataSource {
    id: runner
    engine: "executable"
    signal finished(string command, int exitCode, string stdout, string stderr)

    connectedSources: []
    onNewData: (sourceName, data) => {
        disconnectSource(sourceName)
        finished(sourceName, data["exit code"], data["stdout"], data["stderr"])
    }
    function run(command) {
        connectSource(command)
    }
}
```

Risks, each read from the same source file unless marked:

1. The command is shell code running as the user with plasmashell's environment. Any user text inside it can run other commands. Quote every value in single quotes, or encode it, and validate it first.
2. The command text is in the process list, readable by every user on the machine, while it runs. No secret goes into it.
3. The engine never writes to the process, so it has no standard input. A secret cannot be handed in, it has to be read inside the command.
4. There is no time limit and the whole output is read into memory. Wrap every command in `timeout` and cap the output size.
5. One command string is one source. Requesting the same string while it runs starts no second process. Disconnect the source after `onNewData`, or it stays connected.
6. `plasmoids.knsrc` carries `ContentWarning=Executables`, so the store and Get New Widgets treat widgets as code that can run programs. Say in the store description which programs the widget runs.

---

### Tests

Run every test in an isolated container. Copy the package and the tests into the image with `COPY`, never mount a host folder, and use a throwaway `HOME` and `XDG_*` folders, fake keys in a throwaway keyring and invented fixture data. Pin the base image by digest, and on Arch pin the Plasma version with an Arch Linux Archive date.

1. Unit tests: the `.mjs` modules with the Node test runner. The Node.js manual: "The Node.js test runner can be invoked from the command line by passing the `--test` flag".

```bash
node --test 'tests/unit/**/*.test.mjs'
```

2. QML tests: Qt Quick Test `TestCase` files from `import QtTest`, run by `qmltestrunner` from qt6-declarative, with `QT_QPA_PLATFORM=offscreen` and inside `dbus-run-session` when the widget talks to D-Bus.

```bash
/usr/lib/qt6/bin/qmltestrunner -input tests/qml
```

3. Lint every view:

```bash
/usr/lib/qt6/bin/qmllint -I /usr/lib/qt6/qml package/contents/ui/main.qml
```

4. Smoke test the installed package inside the container: `kpackagetool6 -t Plasma/Applet -i package` into the throwaway home, then `plasmawindowed org.example.weather`, and check that it starts with no QML error.

Run the container with no network and no privileges, then copy the results out with `docker cp`:

```bash
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges --pids-limit 512 weather-widget-test:qml
```

UNVERIFIED as written, the pattern runs in a real widget's suite. On the desktop itself, `plasmawindowed <id>` and `plasmoidviewer -a package` (from plasma-sdk) show a widget in its own window, per the develop.kde.org Testing page.

---

### Making the .plasmoid file

A `.plasmoid` file is a zip archive of the package. Measured here with KPackage 6.31.0: an archive with `metadata.json` and `contents/` at the top level installs, and so does one whose only top-level entry is a folder holding them, because KPackage steps into a single top folder (`src/kpackage/private/packagejobthread.cpp` lines 190 to 232). It also accepts tar archives. Put `metadata.json` at the top level, as the release archive of a published widget does. From inside `package/`:

```bash
zip -r ../org.example.weather-1.0.0.plasmoid metadata.json contents
```

```bash
unzip -l ../org.example.weather-1.0.0.plasmoid
```

Leave tests, screenshots, `.git` and build scripts out of the archive.

---

### Installing and upgrading

All three were measured here in a throwaway `XDG_DATA_HOME` with kpackagetool6 from KPackage 6.31.0:

```bash
kpackagetool6 -t Plasma/Applet -i org.example.weather-1.0.0.plasmoid
```

```bash
kpackagetool6 -t Plasma/Applet -u org.example.weather-1.0.0.plasmoid
```

```bash
kpackagetool6 -t Plasma/Applet -r org.example.weather
```

1. `-i` on an installed id fails with `already exists` and exit 4.
2. `-u` (`--upgrade`) removes the installed copy and installs the new one (`src/kpackagetool/kpackagetool.cpp` lines 535 to 547). It worked with an unchanged `Version`, and it exits 2 with `Plugin ... is not installed` when there is nothing to upgrade.
3. Both take a `.plasmoid` file or the `package/` folder. Never use `--global`.

Then restart plasmashell so it loads the new QML. A running plasmashell keeps the old QML, an observation from a real widget, UNVERIFIED in source:

```bash
systemctl --user restart plasma-plasmashell
```

---

### Installing by KDE Store id

`/usr/lib/kf6/kpackagehandlers/knshandler` comes from frameworkintegration. It takes one `kns://<knsrc file>/<provider>/<entry id>` address. The widget knsrc file is `plasmoids.knsrc` (plasma-workspace 6.7.5, `KPackageStructure=Plasma/Applet`), and the provider id of the KDE Store is `api.kde-look.org`, from https://autoconfig.kde.org/ocs/providers.xml, the KNewStuff default provider list (`src/core/enginebase.cpp` line 163).

```bash
/usr/lib/kf6/kpackagehandlers/knshandler kns://plasmoids.knsrc/api.kde-look.org/<id>
```

UNVERIFIED, not run here because it installs into the real home. Read in frameworkintegration v6.31.0 `src/kpackage-install-handlers/kns/main.cpp`:

1. The knsrc file is found by the host part of the address (lines 79 to 89), and the path must be exactly provider and id (line 92).
2. It installs only an entry the store reports as downloadable, and prints `already installed.` for every other state (lines 169 to 186). So it does not upgrade an installed widget. Use `kpackagetool6 -u` with the new file, or Get New Widgets.
3. Every run also creates `~/.local/share/knewstuff3/window-decorations.knsregistry` and the link `aurorae.knsregistry` when they are missing (lines 39 to 63).

---

### Publishing on store.kde.org

1. Log in and open https://store.kde.org/product/add, which sends a visitor who is not logged in to the login page (measured: HTTP 302 to `/oauth/login`).
2. Category: Plasma 6 Extensions, then Plasma 6 Applets. The API names that category `Plasma 6 Applets`, type id 706, and `plasmoids.knsrc` lists `Categories=Plasma 6 Extensions`, which is how Get New Widgets finds it.
3. Form fields, from one owner's listing record and UNVERIFIED here, because the form needs a login: product name, the same as `Name` in `metadata.json`, whether it is original work, license, the same SPDX id as `metadata.json`, version, a source link, the logo, tags, description and changelog.
4. Logo: a square PNG, for example 512 by 512 pixels rendered from an SVG. The API lists the logo as the first preview picture, before the gallery (measured).
5. Gallery: screenshots rendered in an isolated container from the widget code, with invented accounts, names and numbers only. Never a screenshot of a real desktop, which shows names, e-mail addresses, notifications and keys.
6. Files tab: upload the `.plasmoid` file. Afterwards the API shows its file name, `download_version1` and `downloadtags1` `data##mimetype=application/zip` (measured on two live widgets).
7. The Files tab has a "Download lock for archived files" box. Its effect is not documented anywhere found on 2026-10-23. Leave it at its default and do not rely on it. UNVERIFIED.

Check the product through the OCS API, which Get New Widgets and knshandler read:

```bash
curl -s "https://api.kde-look.org/ocs/v1/content/data/<id>" | grep -o '<statuscode>[0-9]*</statuscode>'
```

`https://api.kde-look.org/ocs/v1/content/data/<id>` answers `statuscode` 999 with `unknown request` for an id that does not exist yet and for a wrong id (measured on 2026-10-23 with id 999999999), so 999 alone cannot tell them apart. Check the id on the product page, `https://store.kde.org/p/<id>`, and wait for `statuscode` 100 before testing an install from the store.

---

### Sources

Fetched or cloned on 2026-10-23.

| Source | Version | Used for |
|---|---|---|
| https://invent.kde.org/documentation/develop-kde-org, `content/docs/plasma/widget/` (setup, configuration, porting_kf6, testing, properties) | master at 9e4ad7ab | metadata keys, PlasmoidItem, config pages, testing tools |
| https://invent.kde.org/frameworks/kpackage | v6.31.0 | archive install, id pattern, `--upgrade` |
| https://invent.kde.org/frameworks/frameworkintegration | v6.31.0 | knshandler |
| https://invent.kde.org/frameworks/knewstuff | v6.31.0 | default provider, `kns://` address form |
| https://invent.kde.org/frameworks/kwallet | v6.31.0 | Secret Service attributes |
| https://invent.kde.org/plasma/plasma5support | v6.7.5 | executable engine |
| https://invent.kde.org/plasma/plasma-workspace | v6.7.5 | layout reset, QML D-Bus module, `plasmoids.knsrc` |
| https://doc.qt.io/qt-6/qtqml-javascript-imports.html | Qt 6.12 | `.mjs` modules |
| https://nodejs.org/api/test.html | Node.js 24 | `node --test` |
| https://api.kde-look.org/ocs/v1/content/data/ | live | store API answers |
