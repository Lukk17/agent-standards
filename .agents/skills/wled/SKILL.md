---
name: wled
description: 'WLED light controllers over the JSON API, read only until the user approves a change: presets, backup. Use when the user says "turn on the WLED strip" or "flash WLED". Not for firmware code, use `embedded-c-arduino`.'
license: MIT
metadata:
  version: "1.1.0"
---

# WLED

How an agent reads and controls a WLED device, and how it makes a change the user approved without losing presets or settings. WLED has no user accounts: anyone who can reach the device runs almost every call, and the settings PIN and the OTA lock guard only part of the interface. The rules below keep the agent to what the user asked. Written for WLED 16. The address, PIN, passwords and Wi-Fi credentials of a real device belong in the user's own notes, never in this skill or a shared repository.

---

### When not to activate

- Changing the WLED firmware source, building custom firmware or writing a usermod, use `embedded-c-arduino`

---

### Hard rules

1. Read-only calls are free: a `GET` of a `/json` route, `/presets.json`, `/cfg.json`, and a settings page other than `/settings/lock`. Listening on the WebSocket is free only below the client limit, so read `ws` in `GET /json/info` first. The serial `v` byte is free only on a port opened with DTR and RTS held off. `GET /json/net` starts a Wi-Fi scan, so call it only when the user wants the network list.
2. Some `GET` calls write: `/reset` reboots, `/settings/lock` locks the settings for every client, `/update?revert` rolls back the firmware, and a `/win&...` URL runs the HTTP API. Treat them as writes. A bare `GET /win` only reads.
3. Before any write, back up `/presets.json` and `/cfg.json`, then tell the user what changes, the worst case and the undo, and wait for a yes. One yes covers one change. When the device cannot be reached over HTTP, say that no backup over HTTP is possible, offer `esptool read-flash` over USB, and go on only after a yes.
4. Firmware and bootloader updates, `erase-flash`, a PIN change, a factory reset (the `RS` field of `POST /settings/sec`) and any Wi-Fi or access point change happen only when the user asks for that action by name.
5. Never post a partial `/settings/*` form, because every missing field is saved as empty or off. Change settings with `POST /json/cfg` instead, but never with only the wanted key: read `GET /json/cfg`, send the wanted keys plus the five keys copied from it that a missing key resets, then read it again and compare.
6. Ask the user for the PIN and the OTA password. Never guess, loop over or print them, and never keep them beyond the one call that uses them: send them on standard input, or from a user-only file deleted right after the call. A wrong PIN locks the settings for every client.
7. Never retry a call that is not idempotent: `"on":"t"`, `"np":true`, `"psave"`. Read the state and send the value you want.
8. Never expose a device to the internet. WLED serves plain HTTP with no login and allows every web origin.
9. Check for a PIN by the status code of `GET /settings/sec`, never with a `POST`.

---

### Reference files

| Task | Open |
|---|---|
| Which reads are free, picking the interface, state, segments, effects, config, the WebSocket, the `/win` API, JSON over serial | [json-api.md](references/json-api.md) |
| A PIN or the OTA lock: checking, setting, removing, unlocking, what the PIN guards | [security-and-pin.md](references/security-and-pin.md) |
| Before the first write, restoring a backup, judging whether a call is risky | [backup-and-restore.md](references/backup-and-restore.md) |
| Presets and playlists | [presets-playlists.md](references/presets-playlists.md) |
| A new or reset device, WLED-AP, Improv, finding the device on the network | [first-setup.md](references/first-setup.md) |
| Flashing over USB, picking the file, OTA updates | [flashing-and-updates.md](references/flashing-and-updates.md) |
| The serial port and its driver for flashing | [Linux](references/usb-serial-linux.md), [Windows](references/usb-serial-windows.md), [macOS](references/usb-serial-macos.md) |
| Syncing devices, realtime streams, MQTT | [sync-realtime-mqtt.md](references/sync-realtime-mqtt.md) |
| Naming a device or judging a VERIFIED mark | [conventions.md](references/conventions.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling the work done | [checklist.md](references/checklist.md) |
