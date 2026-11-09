# Backup, Restore and the Risky Calls

Read this before the first write to a device, before a restore, and whenever you have to judge how much a call can break. The rules live in [SKILL.md](../SKILL.md). Rule 3 there matters most on this page: no write before both files are saved and checked.

Written for WLED 16. Sources: https://kno.wled.ge/features/settings/ (Security settings) and the WLED 16 source files `wled00/wled_server.cpp`, `file.cpp`, `cfg.cpp`, `presets.cpp`, `set.cpp`, `json.cpp`, `button.cpp`, `util.cpp` and `wled.cpp` at https://github.com/wled/WLED. No call here was sent to a device.

Contents:

1. [What a backup holds](#what-a-backup-holds)
2. [Back up](#back-up)
3. [Restore](#restore)
4. [Copies the device keeps by itself](#copies-the-device-keeps-by-itself)
5. [Risky calls](#risky-calls)

---

### What a backup holds

1. `/presets.json` holds every preset and playlist, keyed by ID. The device creates it with `{"0":{}}` at boot when it is missing, so a device with no presets still answers (VERIFIED, `presets.cpp` `initPresetsFile`, called from `wled.cpp`).
2. `/cfg.json` holds every setting except the secrets. Wi-Fi passwords, the access point password, the MQTT password, the settings PIN and the OTA password sit in `wsec.json`, which no route serves (VERIFIED, `cfg.cpp` `serializeConfigSec`, `file.cpp` `handleFileRead` refuses any path holding `sec`). The docs say of Backup and Restore: "Restoring overwrites what is on the device. Passwords are not backed up" (VERIFIED, https://kno.wled.ge/features/settings/).
3. Both downloads work without the PIN, so a backup never needs it (VERIFIED, `file.cpp` `handleFileRead`). The Security settings page has the same two files behind its "Backup presets" and "Backup configuration" buttons.
4. Custom palettes (`/palette<n>.json`), ledmaps (`/ledmap.json`, `/ledmap<n>.json`) and other user files are not in either file. List them with `GET /edit?func=list`, which needs the PIN when one is set, and download each with `GET /<name>` (VERIFIED, `wled_server.cpp` `createEditHandler`).

---

### Back up

Save both files under names that carry the device and the time, before any write. On Linux and macOS:

```bash
curl -sf -o "<backup-dir>/<device>-presets-<time>.json" http://<wled-host>/presets.json
```

```bash
curl -sf -o "<backup-dir>/<device>-cfg-<time>.json" http://<wled-host>/cfg.json
```

On Windows PowerShell, the same with `curl.exe`:

```powershell
curl.exe -sf -o "<backup-dir>\<device>-presets-<time>.json" http://<wled-host>/presets.json
```

```powershell
curl.exe -sf -o "<backup-dir>\<device>-cfg-<time>.json" http://<wled-host>/cfg.json
```

Check that both files parse before going on. A truncated download is not a backup. The output goes to the null device so the files are not printed, and only an error appears. On Linux and macOS:

```bash
python3 -m json.tool "<backup-dir>/<device>-presets-<time>.json" > /dev/null
```

```bash
python3 -m json.tool "<backup-dir>/<device>-cfg-<time>.json" > /dev/null
```

On Windows, with the Python launcher:

```powershell
py -m json.tool "<backup-dir>\<device>-presets-<time>.json" > $null
```

```powershell
py -m json.tool "<backup-dir>\<device>-cfg-<time>.json" > $null
```

A board that cannot be reached over HTTP can still be copied whole over USB, settings and presets included, with esptool v5, whose `read-flash` takes `ALL` as the size (VERIFIED, `esptool/cli_util.py` `parse_size_arg`). Writing that image back restores the board as it was, and it holds `wsec.json` with the passwords, stored as a plain file (inferred, high confidence), so keep it like a password:

```bash
esptool --port <serial-port> read-flash 0 ALL "<backup-dir>/<device>-flash-<time>.bin"
```

Keep `<backup-dir>` outside every repository. `cfg.json` carries no passwords, but it carries the network layout, the MQTT broker and the device name.

---

### Restore

A restore is a write, so it needs its own yes. Upload the file with `POST /upload` as multipart form data. The server writes the upload to the path in its file name, adding a leading slash when missing, so the file name decides what is overwritten (VERIFIED, `wled_server.cpp` `handleUpload`). It needs the PIN when one is set, and answers 401 "Please unlock settings using PIN code!" while locked.

Restore the presets:

```bash
curl -s -F "data=@<backup-dir>/<device>-presets-<time>.json;filename=/presets.json" http://<wled-host>/upload
```

Restore the configuration. Any upload whose name holds `cfg.json` answers "Config restore ok." and reboots the device (VERIFIED, `handleUpload`, `doReboot = true`):

```bash
curl -s -F "data=@<backup-dir>/<device>-cfg-<time>.json;filename=/cfg.json" http://<wled-host>/upload
```

The form field name is not checked by the handler, only the file name (VERIFIED, `handleUpload` takes `filename`). After the reboot, read `GET /json/info` and `GET /json/cfg` and compare with the backup.

Restore a `cfg.json` only to the device it came from, or to the same board with the same wiring. It carries the LED output pins, the LED types and counts, the button and relay pins and the static IP address, and another board with those values can drive the wrong pins or come up on an address that clashes (inferred from the keys `serializeConfig` writes, high confidence). Restoring a `cfg.json` from an older WLED release onto WLED 16 is UNVERIFIED.

Because passwords are not in the backup, a restored device keeps the passwords already on it. A device that was factory reset first comes back with the settings but no Wi-Fi password, so it opens WLED-AP, and the user enters the Wi-Fi password again as [first-setup.md](first-setup.md) shows.

---

### Copies the device keeps by itself

All VERIFIED in the files named.

1. Before every config save the device copies `/cfg.json` to `/bkp.cfg.json` (`cfg.cpp` `serializeConfigToFS`, `file.cpp` `backupFile`), and before an OTA update too (`ota_update.cpp`).
2. At boot, a `/cfg.json` that does not parse is replaced from `/bkp.cfg.json`, and when that fails too it is renamed to `/rst.cfg.json` and the device starts with defaults (`wled.cpp` `WLED::setup`, `cfg.cpp` `resetConfig`).
3. After 5 crashes, each within 2 minutes of the boot before, the device first restores `/bkp.cfg.json`, then resets the config, then on ESP32 boots the other firmware slot (`util.cpp` `handleBootLoop`).

These copies help a device recover, but they are not a backup the user owns. Always take the two downloads above.

---

### Risky calls

| Call | Effect | Undo |
|---|---|---|
| `POST /json/state` with `psave` or `pdel` | Writes `/presets.json`, the light can freeze for a few seconds | Upload the presets backup |
| `POST /json/state` with `psave` and `"o":true` | Writes the body as a preset at once, the source warns this "often causes presets.json corruption" (`presets.cpp` `savePreset`) | Upload the presets backup |
| `POST /json/cfg` | Changes settings and saves them, some reboot the device. A body without `light.gc`, `hw.led.rgbwm`, `hw.led.fps` and `nw.linked_remote` resets those too, see "Change the config safely" in [json-api.md](json-api.md) | `POST /json/cfg` with the old values, or upload the cfg backup |
| `POST /json/cfg` with `nw.ins` | Changes Wi-Fi, and a slot without `ip`, `gw` and `sn` goes back to DHCP (`cfg.cpp` `deserializeConfig`) | Serial Improv or WLED-AP, see [first-setup.md](first-setup.md) |
| Any partial `POST /settings/<page>` | Saves every missing field as empty or off | Upload the cfg backup, re-enter passwords by hand |
| `POST /settings/sec` with `RS` | Factory reset: formats the file system, erasing settings, presets and passwords (`set.cpp`, `WLED_FS.format()`) | Set up again, then upload both backups |
| Button 0 held over 10 seconds and released | Same factory reset (`button.cpp`) | Same |
| Button 0 held 5 to 10 seconds and released | Opens WLED-AP (`button.cpp`, `WLED_LONG_AP 5000`) | Reboot |
| `POST /upload` with any file name | Overwrites that file, `cfg.json` also reboots | Upload the backup of that file |
| `GET /edit?func=delete&path=<file>` | Deletes a file | Upload the backup of that file |
| `GET /reset`, `"rb":true`, `/win&RB` | Reboots, the light goes dark for a few seconds | None needed |
| `POST /json/state` with `wifi.ap` | Starts or stops the access point at once (`json.cpp` `deserializeState`) | Send the opposite value |
| `POST /update`, `POST /updatebootloader` | Replaces firmware or bootloader, see [flashing-and-updates.md](flashing-and-updates.md) | `GET /update?revert` on ESP32, or flash over USB |
| `esptool erase-flash` | Erases everything, including settings and presets | Flash again, set up again, upload both backups |

`GET /reset` is a reboot, not a factory reset (VERIFIED, `wled_server.cpp`, the `/reset` handler sets only `doReboot`). The docs advise against many presets because each preset write is heavy and can freeze the light for a few seconds, see [presets-playlists.md](presets-playlists.md). How many writes the flash survives is not documented by WLED (UNVERIFIED).
