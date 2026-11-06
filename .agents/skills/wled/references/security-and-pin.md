# Devices With and Without a PIN or the OTA Lock

Read this before working with a device whose settings ask for a PIN, whose update page says OTA is locked, or whose protection you do not know yet. The rules live in [SKILL.md](../SKILL.md). Rule 6 there matters most on this page: ask the user for the PIN, never guess it.

Written for WLED 16. Sources: https://kno.wled.ge/advanced/ota-lock/ and https://kno.wled.ge/features/settings/, and the WLED 16 source files `wled00/wled_server.cpp`, `set.cpp`, `cfg.cpp`, `util.cpp`, `file.cpp`, `wled.h`, `wled.cpp` and `const.h` at https://github.com/wled/WLED, with the build flags in `platformio.ini`. No call here was sent to a device.

Contents:

1. [The security model](#the-security-model)
2. [Check the state without changing it](#check-the-state-without-changing-it)
3. [How the PIN works](#how-the-pin-works)
4. [Unlock](#unlock)
5. [What the PIN guards and what it does not](#what-the-pin-guards-and-what-it-does-not)
6. [The OTA lock](#the-ota-lock)
7. [Work on an unprotected device](#work-on-an-unprotected-device)

---

### The security model

The docs say: "WLED security model is based on assumption that it is run on a trusted network, and in most cases, anyone having a network access to a WLED device has permissions for any operation. OTA Lock is an exception." (VERIFIED, https://kno.wled.ge/advanced/ota-lock/). There is no HTTP basic auth, no API key and no token, and every answer carries `Access-Control-Allow-Origin: *`, so any web page the user opens can send calls to the device (VERIFIED, `wled_server.cpp` `initServer`). Traffic is plain HTTP, so the PIN and the OTA password cross the network unencrypted.

Three separate guards exist, and each one is off unless someone switched it on:

| Guard | Set where | Guards |
|---|---|---|
| Settings PIN | Security settings, 4 digits | Config writes, settings pages, the file editor, uploads, OTA |
| OTA lock | Security settings, with a passphrase | Firmware and bootloader uploads, and the Security fields themselves |
| Wi-Fi settings lock | Security settings, only with the OTA lock on | The Wi-Fi settings page |

---

### Check the state without changing it

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://<wled-host>/settings/sec
```

`401` means a PIN is set and locked, `200` means open now, either no PIN or entered in the last 15 minutes. VERIFIED in `wled_server.cpp` `serveSettings`: a page numbered above the Wi-Fi page (above the menu once Wi-Fi is configured) and below the lock page gets the PIN form with code 401 while `!correctPIN && strlen(settingsPIN) > 0`, and a `GET` saves nothing. The Security page is number 6 in `const.h`, so it is guarded in both cases.

Do not probe with `POST /json/cfg` and `{}`. On an open device that runs `cfg.cpp` `deserializeConfig`, which clears the list of linked ESP-NOW remotes (`linked_remotes.clear()`, outside any key check), resets brightness and color gamma, the auto white mode and the frame rate, and then marks the config for saving (VERIFIED, see "Change the config safely" in [json-api.md](json-api.md)). Do not probe with `GET /settings/lock` either: it is the only call that tells "no PIN" from "unlocked", answering "No PIN set" or "Settings locked", and it locks the device for every client.

Whether OTA is locked:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://<wled-host>/update
```

`401` with "Please unlock OTA in security settings!" means the OTA lock is on. A `401` with the PIN form means the PIN guards it. `501` means the build has no OTA at all, which is true of the ESP01 builds (VERIFIED, `wled_server.cpp` `initServer`, the `/update` handlers, and `platformio.ini` `-D WLED_DISABLE_OTA` on the `esp01_1m_*` environments). The page is read only, the upload is a `POST`.

---

### How the PIN works

All VERIFIED in the files named per line.

1. The PIN is 4 characters, compared on the first 4 only (`util.cpp` `checkSettingsPIN`, `strncmp(settingsPIN, pin, 4)`). `0000` cannot be saved, the form treats it as a placeholder (`set.cpp`).
2. The unlock is one global flag, `correctPIN` in `wled.h`. An unlock from one client opens the settings for every client, and a wrong PIN locks them for every client.
3. The unlock lasts 15 minutes after the last PIN check or settings save, `PIN_TIMEOUT 900000` in `const.h`, checked in `wled.cpp`.
4. After a wrong PIN, tries in the next 3 seconds are ignored with no error, `PIN_RETRY_COOLDOWN 3000`. Wait more than 3 seconds before trying again, and try again only with a PIN the user gave.

---

### Unlock

Send the PIN as a JSON string in a `POST` to `/json/state`. The server reads a `"pin"` key in any `POST` to a `/json` path before it looks at the path, and the state parser ignores the key, so this changes no light state (VERIFIED, `wled_server.cpp`, `if (root.containsKey("pin")) checkSettingsPIN(...)`). The `pin` key is not in the docs, so treat it as source behaviour that can change in a later release.

```bash
curl -s -X POST -H 'Content-Type: application/json' --data-binary @- http://<wled-host>/json/state
```

The body `{"pin":"<pin>"}` goes in on standard input, fed from where the user keeps the PIN, so it lands neither in the shell history nor in a file. Where a file cannot be avoided, create it under `umask 077` in a temporary folder and delete it right after the one call. Then confirm with the status check above, which now answers `200`. The same `"pin"` key can ride along in the `POST /json/cfg` body itself.

Do not unlock through a settings form. A `POST` of `PIN=` to `/settings/sec` while the settings are already open sets that value as the new PIN. While the OTA lock is off, the same post also switches the Wi-Fi lock, ArduinoOTA and the same subnet rule off, because the missing checkboxes count as off. While the OTA lock is on and no correct `OP=` is sent, those fields stay as they are (VERIFIED, `set.cpp` `handleSettingsSet`, the `SUBPAGE_SEC` block, `bool pwdCorrect = !otaLock`). A `POST` to any other settings page while open saves that page with every missing field empty.

Lock again when the work is done, which is a write the user should know about:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://<wled-host>/settings/lock
```

---

### What the PIN guards and what it does not

VERIFIED in `wled_server.cpp`, `set.cpp` and `file.cpp`.

| Guarded while locked | Answer |
|---|---|
| `POST /json/cfg` | 401 `{"error":1}` |
| Settings pages from LED settings to the pin info page | 401 with the PIN form |
| The Wi-Fi settings page, once Wi-Fi is configured | 401 with the PIN form |
| `GET /settings/settings.js?p=<n>` for a page above 0 | 401 |
| `/edit`, the file editor, listing, download and delete | 401, and 403 for `wsec.json` even when open |
| `POST /upload` | 401 "Please unlock settings using PIN code!" |
| `POST /update` and `POST /updatebootloader` | 401 |
| `GET /update?revert`, the ESP32 firmware rollback | 401 while the OTA lock is on, the PIN form while the PIN is locked, and only from a client in a private range (VERIFIED, `wled_server.cpp`, the `/update` GET handler, then `serveSettings` with `SUBPAGE_UPDATE` and `inLocalSubnet`) |

| Not guarded, works with no PIN | Why it matters |
|---|---|
| `POST /json/state`, including `psave`, `pdel`, `rb`, `playlist`, `wifi.ap` | Anyone on the network can overwrite presets, reboot, or open the access point |
| The `/win` HTTP API, including `PS=` and `RB` | Same |
| `GET /reset` | Reboots |
| `GET /json/cfg`, `GET /cfg.json`, `GET /presets.json` | The backup works on a locked device. Only paths holding `sec` are refused (`file.cpp` `handleFileRead`) |
| The WebSocket, UDP sync, MQTT, serial JSON and Improv | Improv over USB can set new Wi-Fi credentials with no PIN |
| The Wi-Fi settings page while no Wi-Fi is configured | So a new device can be set up |

The OTA lock does not guard `POST /upload` or `/edit` in WLED 16: both handlers check only `correctPIN` (VERIFIED, `wled_server.cpp` `handleUpload` and `createEditHandler`). A comment in `wled.h` says the file editor "Will also be disabled with OTA lock", and the presets docs say `/edit` needs the OTA lock off, but the handlers do not do that.

Passwords live in `wsec.json`, which no route serves.

---

### The OTA lock

1. Off in release builds. `otaLock` starts true only when the build sets `WLED_OTA_PASS`, and the default passphrase is `wledota` (VERIFIED, `wled.h`, and https://kno.wled.ge/advanced/ota-lock/).
2. There is no OTA password per upload. Unlock first, upload, and lock again if the user wants it.
3. Unlock through the config API with the passphrase the user gives, plus the PIN when one is set, with the call below. The body holds `{"pin":"<pin>","ota":{"psk":"<ota-password>","lock":false}}`, without `pin` when no PIN is set, plus the five keys copied from `GET /json/cfg` that the section "Change the config safely" of [json-api.md](json-api.md) lists, because a config body without them resets them. With the correct `psk`, `cfg.cpp` `deserializeConfig` takes `lock`, `lock-wifi`, `aota` and `same-subnet` from the body, and keys left out keep their value (VERIFIED in source, not run on a device). While the lock is already off, a `psk` in the body sets a new OTA password, so leave `psk` out then (VERIFIED, same function, `getStringFromJson(otaPass, pwd, 33)`). The `/update` handler reads the lock flag from memory, so no reboot should be needed (inferred from `wled_server.cpp`, high confidence). The unlock is saved with the config, so it survives a reboot (VERIFIED, `wled_server.cpp`, a config `POST` sets `configNeedsWrite`, and `cfg.cpp` `serializeConfig` writes `ota.lock`). Lock it again after the update, as step 7 shows.
4. The Security settings form also unlocks, with `OP=<ota-password>` and no `NO` field, but that is a full form, so send it only as the whole form the page itself posts, never as a partial post (rule 5 in [SKILL.md](../SKILL.md)).
5. The same subnet rule, `otaSameSubnet`, default on (VERIFIED, `wled_server.cpp` `/update` handler):
   1. on and no PIN set: the upload is refused unless the client is in the device subnet, 401 "Client is not on local subnet."
   2. on and a PIN set: no subnet check, the PIN is required.
   3. off: the client must be in 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, the device subnet, or 4.3.2.0/24 while the access point runs.
6. Every settings form `POST` needs a client in those private ranges, whatever the option says (VERIFIED, `serveSettings`, `inLocalSubnet`).
7. Lock again after the work, with the same call and the body `{"pin":"<pin>","ota":{"lock":true}}` plus the same five keys. While the lock is off no passphrase is needed for this, and leaving `psk` out keeps the passphrase that is set (VERIFIED, `cfg.cpp` `deserializeConfig`, `bool pwdCorrect = !otaLock`). Then check that `GET /update` answers 401 with "Please unlock OTA in security settings!".

The call for steps 3 and 7, with the body on standard input:

```bash
curl -s -X POST -H 'Content-Type: application/json' --data-binary @- http://<wled-host>/json/cfg
```

---

### Work on an unprotected device

Nothing above blocks the agent, so only the rules in [SKILL.md](../SKILL.md) keep it to what the user asked. Do not set a PIN or switch the OTA lock on unless the user asks. Suggest it once if the device is on a network other people use, and say that a forgotten PIN cannot be read back over the network: `GET /json/cfg` carries only password lengths, and the PIN sits in `wsec.json`, which no route serves (VERIFIED, `cfg.cpp` `serializeConfig` and `serializeConfigSec`). Restoring a `cfg.json` therefore does not clear it. Clearing it takes a factory reset by holding button 0 for more than 10 seconds and releasing it, or erasing the flash over USB, and both erase presets and settings (VERIFIED, `button.cpp`, `WLED_LONG_FACTORY_RESET 10000`). UNVERIFIED that no other route exists.
