---
name: wled
description: 'Controls WLED light controllers over their JSON API, WebSocket, serial and Improv, with or without a PIN, read only until the user approves a change, with presets and config backed up first. Use when the user says "turn on the WLED strip", "save this as a preset", "back up my WLED", "set up a new WLED board" or "flash WLED". Not for writing WLED firmware code or usermods, use `embedded-c-arduino`.'
license: MIT
metadata:
  version: "1.0.0"
---

# WLED

How an agent reads and controls a WLED device, and how it makes a change the user approved without losing presets or settings. WLED has no user accounts: anyone who can reach the device runs almost every call, and the settings PIN and the OTA lock guard only part of the interface. The rules below keep the agent to what the user asked. Written for WLED 16. A fact marked VERIFIED was read in the WLED 16 source under `wled00/` at https://github.com/wled/WLED or in the WLED docs at https://kno.wled.ge, and each reference file names the file and function or the page. A fact marked UNVERIFIED says why. The WLED project keeps its own agent rules for firmware work at https://github.com/wled/WLED/blob/main/AGENTS.md.

| Task | Open |
|---|---|
| Reading or changing state, segments, effects, palettes, info or config, the WebSocket, the `/win` API, JSON over serial | [json-api.md](references/json-api.md) |
| Checking, setting, removing, unlocking or locking a PIN or the OTA lock, what the PIN guards | [security-and-pin.md](references/security-and-pin.md) |
| Before the first write, restoring `/presets.json` or `/cfg.json`, judging whether a call is risky | [backup-and-restore.md](references/backup-and-restore.md) |
| Saving, applying, deleting or listing presets, building a playlist | [presets-playlists.md](references/presets-playlists.md) |
| A new or reset device, WLED-AP, Improv over serial, finding the device on the network | [first-setup.md](references/first-setup.md) |
| Flashing over USB on Linux, Windows or macOS, USB to serial drivers, picking the file, OTA updates | [flashing-and-updates.md](references/flashing-and-updates.md) |
| Syncing devices, E1.31, Art-Net, DDP, realtime streams, MQTT | [sync-realtime-mqtt.md](references/sync-realtime-mqtt.md) |

---

### When to activate

- Turning a light on or off, or changing its color, brightness, effect, palette or segments
- Saving, applying or deleting a preset, or building a playlist
- Backing up or restoring a device's presets and configuration
- A device whose settings ask for a PIN, or whose update page says OTA is locked
- Setting up a new board, flashing WLED, or updating its firmware
- Syncing devices, streaming realtime LED data, or connecting WLED to MQTT

---

### When not to activate

- Changing the WLED firmware source, building custom firmware or writing a usermod, use `embedded-c-arduino`
- Wiring, power supply sizing and LED strip choice, beyond pointing at https://kno.wled.ge/basics/compatible-hardware/

---

### Facts about one setup

The address, mDNS name, PIN and OTA password of a real device, the Wi-Fi credentials and the MQTT broker belong in the user's own notes, never in this skill or a shared repository. Examples use placeholders: `<wled-host>` for the IP address or mDNS name, `<pin>`, `<serial-port>`, `<backup-dir>`.

---

### Hard rules

1. Read-only calls are free: a `GET` of `/json`, `/json/state`, `/json/info`, `/json/si`, `/json/nodes`, `/json/eff`, `/json/fxdata`, `/json/pal`, `/json/palx`, `/json/cfg`, `/json/pins`, `/presets.json`, `/cfg.json`, and a settings page other than `/settings/lock`. Listening on the WebSocket is free only below the client limit, 8 on ESP32 and 3 on ESP8266, because a new client closes the oldest one, so read `ws` in `GET /json/info` first. The serial `v` byte is free only on a port opened with DTR and RTS held off, because toggling them can reset the board. `GET /json/net` starts a Wi-Fi scan, so call it only when the user wants the network list.
2. Some `GET` calls write: `/reset` reboots, `/settings/lock` locks the settings for every client, `/update?revert` rolls back the firmware, and a `/win&...` URL runs the HTTP API. Treat them as writes. A bare `GET /win` only reads.
3. Before any write, back up `/presets.json` and `/cfg.json`, then tell the user what changes, the worst case and the undo, and wait for a yes. One yes covers one change. When the device cannot be reached over HTTP, such as a bare board or one that does not boot, say that no backup over HTTP is possible, offer `esptool read-flash` over USB, and go on only after a yes.
4. Firmware and bootloader updates, `erase-flash`, a PIN change, a factory reset (the `RS` field of `POST /settings/sec`) and any Wi-Fi or access point change happen only when the user asks for that action by name.
5. Never post a partial `/settings/*` form. Every missing field is saved as empty or off, so a partial Wi-Fi form disables mDNS and opens an access point with no password, and a partial security form, while the OTA lock is off, switches the same subnet rule, ArduinoOTA and the Wi-Fi lock off. Change settings with `POST /json/cfg` instead, but never with only the wanted key: a missing `light.gc.bri`, `light.gc.col`, `hw.led.rgbwm`, `hw.led.fps` or `nw.linked_remote` is reset and saved. Read `GET /json/cfg`, send the wanted keys plus those five copied from it, then read it again and compare, as [json-api.md](references/json-api.md) shows.
6. Ask the user for the PIN and the OTA password. Never guess, loop over or print them, and never keep them beyond the one call that uses them: send them on standard input, or from a user-only file deleted right after the call. A wrong PIN locks the settings for every client.
7. Never retry a call that is not idempotent: `"on":"t"`, `"np":true`, `"psave"`. Read the state and send the value you want.
8. Never expose a device to the internet. WLED serves plain HTTP with no login and allows every web origin.

---

### Check for a PIN

Read only the status code of a protected settings page, which writes nothing:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://<wled-host>/settings/sec
```

`401` means a PIN is set and locked, `200` means the settings are open now, either with no PIN or unlocked in the last 15 minutes. Never probe with `POST /json/cfg` and `{}`, which on an open device runs the config parser and schedules a save. [security-and-pin.md](references/security-and-pin.md) has the source evidence and the unlock.

---

### Pick the interface

1. Light state, segments, presets: `POST /json/state`.
2. Watching changes made elsewhere: the WebSocket at `ws://<wled-host>/ws`.
3. Settings: `POST /json/cfg` with the wanted keys and the five keys of rule 5, plus the PIN when one is set.
4. Backup and restore: `GET /presets.json`, `GET /cfg.json`, `POST /upload`.
5. No Wi-Fi yet: Improv or JSON over USB serial at 115200 baud.
6. Flashing or recovering a board: the web installer or `esptool` over USB.
7. Updating a running device: `POST /update`.
8. A tool that can only open a URL: the `/win` HTTP API.

---

### Checklist

- [ ] The device was confirmed as WLED with `GET /json/info`, and `ver` and `release` were noted
- [ ] The PIN state was checked with a `GET` of `/settings/sec`, not with a `POST`
- [ ] `/presets.json` and `/cfg.json` were saved and parsed as valid JSON before the first write
- [ ] Every write had its own yes after the change, the worst case and the undo were stated
- [ ] No partial `/settings/*` form was posted
- [ ] `GET /json/cfg` was read before and after each config change, and only the intended keys differ
- [ ] The OTA lock is back in the state it had before the work
- [ ] Firmware, bootloader, PIN, factory reset and Wi-Fi changes happened only when the user named them
- [ ] No PIN, OTA password or Wi-Fi password was guessed or printed, and no file holding one outlived its call
- [ ] Every UNVERIFIED fact relied on was named to the user as unverified
