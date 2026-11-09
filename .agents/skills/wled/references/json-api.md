# JSON API, WebSocket and the HTTP API

Read this before reading or changing the state, the segments, the effects, the palettes or the config of a WLED device. The rules live in [SKILL.md](../SKILL.md). Rules 1 to 3 there matter most on this page: a `GET` is free except the few that write, and every `POST` waits for a backup and a yes.

Written for WLED 16. Sources: https://kno.wled.ge/interfaces/json-api/, https://kno.wled.ge/interfaces/http-api/, https://kno.wled.ge/interfaces/websocket/, https://kno.wled.ge/interfaces/serial/ and https://kno.wled.ge/interfaces/e1.31-dmx/, and the WLED 16 source files `wled00/wled_server.cpp`, `json.cpp`, `cfg.cpp`, `set.cpp`, `ws.cpp`, `wled_serial.cpp`, `wled.cpp`, `wled.h`, `const.h` and `data/settings_wifi.htm` at https://github.com/wled/WLED. No call here was sent to a device.

Contents:

1. [Read routes](#read-routes)
2. [How a POST works](#how-a-post-works)
3. [Change the config safely](#change-the-config-safely)
4. [Wi-Fi sleep](#wi-fi-sleep)
5. [State keys](#state-keys)
6. [Segment keys](#segment-keys)
7. [WebSocket](#websocket)
8. [HTTP API](#http-api)
9. [JSON over serial](#json-over-serial)
10. [Error codes](#error-codes)

---

### Read routes

All VERIFIED in the route table of https://kno.wled.ge/interfaces/json-api/ and in `json.cpp` `serveJson`.

| Route | Returns |
|---|---|
| `GET /json` | `state`, `info`, `effects` and `palettes` in one object |
| `GET /json/state` | The state object |
| `GET /json/info` | The info object, read only |
| `GET /json/si` | State and info together |
| `GET /json/nodes` | Other WLED devices heard on the network |
| `GET /json/eff` | Array of effect names, the index is the effect ID |
| `GET /json/fxdata` | Effect metadata: which sliders and options each effect uses |
| `GET /json/pal` | Array of built-in palette names, the index is the palette ID |
| `GET /json/palx?page=<n>` | Palette color previews including custom palettes, paged, the `m` key is the last page |
| `GET /json/net` | Wi-Fi networks from the last scan, and starts a scan when none is cached |
| `GET /json/cfg` | The config object, with no passwords in it |
| `GET /json/pins` | Pin allocations, since WLED 16 |

The documented names are `/json/eff` and `/json/pal`. The server picks the sub-object by searching the URL for a substring, so `/json/effects` and `/json/palettes` answer the same, and any other longer path answers 501 with `{"error":4}` (VERIFIED, `json.cpp` `serveJson`, `url.indexOf(F("eff"))`, `url.indexOf("pal")`). Use the documented names.

`/json/live` is compiled in only with `WLED_ENABLE_JSONLIVE`, and `wled.h` defines that flag only when WebSockets are switched off, so standard builds do not have it (VERIFIED, `wled.h`). Use the WebSocket `{"lv":true}` stream for a live preview instead.

Plain text routes: `GET /version` returns the build number, `GET /uptime` the milliseconds since boot, `GET /freeheap` the free memory (VERIFIED, `wled_server.cpp` `initServer`).

`/presets.json` and `/cfg.json` are files, read with a plain `GET`, as [backup-and-restore.md](backup-and-restore.md) shows.

---

### How a POST works

1. Send `Content-Type: application/json`. A body that does not parse answers 400 with `{"error":9}` (VERIFIED, `wled_server.cpp`, `serveJsonError(request, 400, ERR_JSON)`).
2. A `POST` to `/json/state` or `/json` with part of the state changes only those keys. Every other `/json` path takes state the same way, except a path holding `cfg`, which takes part of the config object (VERIFIED, https://kno.wled.ge/interfaces/json-api/ "only paths containing `cfg` (normally `/json/cfg`) are different", and `wled_server.cpp`, `isConfig = url.indexOf(F("cfg")) > -1`). The docs say "Stick to `/json/state`".
3. The answer is `{"success":true}`. With `"v":true` in the body the answer is the full object for that path, the state for `/json/state` (VERIFIED, docs `v` row and `wled_server.cpp`). A body of only `{"v":true}` changes nothing and returns the state.
4. A `"pin"` key is read before the path is looked at, and unlocks or locks the settings for every client, as [security-and-pin.md](security-and-pin.md) explains.
5. `POST /json/cfg` answers 401 with `{"error":1}` while a PIN is set and not entered (VERIFIED, `wled_server.cpp`, `serveJsonError(request, 401, ERR_DENIED)`). A body with only the keys to change is not safe, see [Change the config safely](#change-the-config-safely). In the config body, `"rb":true` reboots after the change and `"sv":false` keeps the change in memory without saving it (VERIFIED, `cfg.cpp` end of `deserializeConfig`).
6. The device has one JSON buffer. When it is busy the server delays the answer (VERIFIED, `request->deferResponse()`). Send one request at a time and wait for the answer.

Read the state:

```bash
curl -s http://<wled-host>/json/state
```

Turn the light on at about half brightness and get the new state back. This is a write, so the backup and the yes come first:

```bash
curl -s -X POST -H 'Content-Type: application/json' -d '{"on":true,"bri":128,"v":true}' http://<wled-host>/json/state
```

Set the primary color of segment 0 to red:

```bash
curl -s -X POST -H 'Content-Type: application/json' -d '{"seg":[{"id":0,"col":[[255,0,0]]}]}' http://<wled-host>/json/state
```

---

### Change the config safely

`POST /json/cfg` runs `cfg.cpp` `deserializeConfig` on the body. Most keys go through `CJSON(a,b)`, defined as `a = b | a`, so a missing key keeps its value. A few do not, and a body without them resets them and the change is saved (VERIFIED, `cfg.cpp` `deserializeConfig`, and the open WLED pull request https://github.com/wled/WLED/pull/5885 "Keep linked remotes, FPS, auto-white mode and gamma on a partial /json/cfg POST"):

| Key left out | What happens | Source line |
|---|---|---|
| `light.gc.bri` | Brightness gamma switches off | `float light_gc_bri = light["gc"]["bri"] \| 1.0f` |
| `light.gc.col` | Color gamma switches on with `light.gc.val` | `float light_gc_col = light["gc"]["col"] \| gammaCorrectVal` |
| `hw.led.rgbwm` | The global auto white mode is disabled | `Bus::setGlobalAWMode(hw_led[F("rgbwm")] \| AW_GLOBAL_DISABLED)` |
| `hw.led.fps` | The frame rate goes back to the build default | `unsigned targetFPS = hw_led["fps"] \| WLED_FPS` |
| `nw.linked_remote` | The list of linked ESP-NOW remotes is emptied, on builds with ESP-NOW | `linked_remotes.clear()` before the key is read |
| `ip`, `gw`, `sn` in a sent `nw.ins` slot | That slot goes back to DHCP | `IPAddress nIP = (uint32_t)0U` and `CJSON(nIP[i], ip[i])` on a local that starts at zero |

`GET /json/cfg` writes all five top keys (VERIFIED, `cfg.cpp` `serializeConfig`), so the safe change is:

1. Read the config and keep the answer as the before copy:

```bash
curl -s -o <before-file> http://<wled-host>/json/cfg
```

2. Build a body with the keys to change, plus `light.gc` with its `bri`, `col` and `val`, `hw.led.rgbwm`, `hw.led.fps`, and `nw.linked_remote` when the before copy has it, all copied from the before copy, plus `"pin"` when a PIN is set. Leave `hw.led.ins` out unless the LED outputs are the change, because sending it rebuilds the LED outputs. For example, to change the device name, the body holds `{"id":{"name":"<name>"},"light":{"gc":{"bri":<bri>,"col":<col>,"val":<val>}},"hw":{"led":{"rgbwm":<rgbwm>,"fps":<fps>}},"nw":{"linked_remote":[<copied>]}}`.
3. Send it on standard input, so a PIN in it lands in no file:

```bash
curl -s -X POST -H 'Content-Type: application/json' --data-binary @- http://<wled-host>/json/cfg
```

4. Read the config again and compare it with the before copy. Only the intended keys may differ. When anything else changed, send the old values back the same way.

The list above is what WLED 16 source shows. A later release can add or remove such keys, so the compare in step 4 is the check that holds on every release.

---

### Wi-Fi sleep

`wifi.sleep` in the config controls modem sleep, the power saving mode of the Wi-Fi radio. The key is stored inverted from the internal `noWifiSleep`, so `true` allows sleep and `false` turns it off (VERIFIED, `cfg.cpp`, `noWifiSleep = !(wifi[F("sleep")] | !noWifiSleep)`, the same line in WLED 0.15.1). The settings page shows the opposite sense: a ticked "Disable WiFi sleep" box, form field `WS`, means `false` (VERIFIED, `data/settings_wifi.htm` and `set.cpp`).

1. Default: sleep is off on ESP32 and on on ESP8266 (VERIFIED, `wled.h`, `noWifiSleep _INIT(true)` under `ARDUINO_ARCH_ESP32`, `_INIT(false)` otherwise).
2. Turn sleep off when a device drops off the network, is slow to answer or streams realtime. On an ESP32 the docs say it "can reduce/eliminate visual stuttering/lag of effects, and significantly reduce ping times" (VERIFIED, https://kno.wled.ge/interfaces/e1.31-dmx/).
3. The cost is more power use and more heat. The source says "disabling modem sleep modes will increase heat output and power usage, but may help with connection issues" (VERIFIED, `wled.h`).
4. A saved change applies only at the next Wi-Fi connection, in practice after a reboot. `wled.cpp` `initConnection` applies it with `WiFi.setSleep(!noWifiSleep)` on ESP32 and `wifi_set_sleep_type` on ESP8266, and saving this key starts no reconnect (VERIFIED, `cfg.cpp` and `set.cpp`).
5. Make the change as [Change the config safely](#change-the-config-safely) shows, with `"wifi":{"sleep":false}` as the key to change and `"rb":true` to reboot after it. It is a Wi-Fi change, so only when the user names it, and the yes must cover the reboot, as the rules in [SKILL.md](../SKILL.md) say.

---

### State keys

VERIFIED in the state object table of https://kno.wled.ge/interfaces/json-api/ and in `json.cpp` `deserializeState`, unless the row says otherwise.

| Key | Values | Notes |
|---|---|---|
| `on` | `true`, `false`, `"t"` | `"t"` toggles, so never retry it |
| `bri` | 0 to 255 | Use 1 to 255 and `"on":false` to switch off |
| `transition` | 0 to 65535 | In units of 100 ms, kept as the new default |
| `tt` | 0 to 65535 | Transition for this call only |
| `ps` | -1 to 250 | Apply a preset. `"1~17~"` steps through 1 to 17, `"4~10r"` picks one at random |
| `psave` | 1 to 250 | Save the current state as a preset, writes flash |
| `pdel` | 1 to 250 | Delete a preset, writes flash |
| `pl` | -1 to 250 | Running playlist, read only |
| `playlist` | object | Start a playlist, see [presets-playlists.md](presets-playlists.md) |
| `np` | `true` | Next playlist entry, since 0.15, never retry it |
| `nl.on`, `nl.dur`, `nl.mode`, `nl.tbri` | bool, 1 to 255 minutes, 0 to 3, 0 to 255 | Nightlight. Modes: 0 instant, 1 fade, 2 color fade, 3 sunrise. `nl.rem` is read only |
| `udpn.send`, `udpn.recv`, `udpn.sgrp`, `udpn.rgrp`, `udpn.nn` | bool, bool, bitfield, bitfield, bool | UDP sync, `nn` skips the sync packet for this call |
| `live` | bool | Enters realtime mode and blanks the LEDs, send `{"live":false}` when done |
| `lor` | 0, 1, 2 | Live data override: off, until live data ends, until reboot |
| `mainseg` | segment ID | The segment UDP sync and segment-less calls use |
| `seg` | object or array | Segments, see below |
| `time` | Unix time | Sets the clock |
| `rb` | `true` | Reboots at once, ignored when `psave` is in the same body |
| `ledmap` | 0 to 9 | Loads a ledmap file |
| `rmcpal` | value | Deletes a custom palette file, a write |
| `win` | string | Runs an HTTP API string inside the JSON call (VERIFIED, `json.cpp`, `const char* httpwin = root["win"]`, not in the docs table) |
| `wifi.ap` | bool | Starts or stops the access point at once, with no PIN check (VERIFIED, `json.cpp` end of `deserializeState`, not in the docs table). A Wi-Fi change, so only when the user names it |

---

### Segment keys

VERIFIED in the segment table of https://kno.wled.ge/interfaces/json-api/ and in `json.cpp` `deserializeSegment`.

| Key | Values | Notes |
|---|---|---|
| `id` | 0 to `info.leds.maxseg` minus 1 | Taken from the array order when left out |
| `start`, `stop` | LED index | `stop` is not included. `stop` at or below `start` deletes the segment, the docs advise `"stop":0` |
| `len` | count | Ignored when `stop` is present |
| `startY`, `stopY` | row | 2D only |
| `grp`, `spc`, `of` | 0 to 255, 0 to 255, offset | Grouping, spacing, offset |
| `col` | up to 3 colors | Each `[r,g,b]` or `[r,g,b,w]` or a hex string, primary, background, third. `"r"` is random since WLED 16 |
| `fx` | effect ID, `"~"`, `"~-"`, `"r"` | Look names up in `/json/eff` |
| `sx`, `ix` | 0 to 255 | Speed and intensity, `"~10"` steps by 10 |
| `c1`, `c2`, `c3` | 0 to 255, 0 to 255, 0 to 31 | Custom sliders, labels in `/json/fxdata` |
| `o1`, `o2`, `o3` | bool | Effect options |
| `pal` | palette ID, `"~"`, `"~-"`, `"r"` | Look names up in `/json/pal` |
| `sel` | bool | Selected segments take calls from APIs without segments |
| `rev`, `mi`, `rY`, `mY`, `tp` | bool | Reverse, mirror, and the 2D versions and transpose |
| `on`, `bri`, `cct` | bool, 0 to 255, 0 to 255 or 1900 to 10091 | Per segment power, brightness, white temperature |
| `frz` | bool | Freezes the effect |
| `i` | array | Individual LED colors, not in the state answer |
| `n` | string | Segment name |
| `rpt` | bool | Repeats the segment until the LEDs run out |
| `fxdef` | bool | Loads the effect defaults from the metadata |

---

### WebSocket

All VERIFIED in https://kno.wled.ge/interfaces/websocket/ and `ws.cpp`.

1. Connect to `ws://<wled-host>/ws`. There is no TLS, so no `wss://`.
2. On connect the server sends the same object as `GET /json/si`, then sends it again to every client after each change, at most about once per second, so fast changes merge into one message.
3. Send a JSON state object as text to change the state, the same keys as `POST /json/state`. One message is at most 1428 bytes, 528 on ESP8266, and a longer message split over frames answers `{"error":9}`.
4. `{"lv":true}` starts the live LED stream for one client, `{"lv":false}` stops it.
5. Up to 8 clients on ESP32 and 3 on ESP8266, a new client over the limit closes the oldest, which can be the user's own web page or app. Read `ws` in `GET /json/info` before connecting, and connect only while it is below the limit.

---

### HTTP API

`/win&...` is the older API. The docs say "While this API is not deprecated, it is highly recommended to use the JSON API instead of the HTTP API for new integrations" (VERIFIED, https://kno.wled.ge/interfaces/http-api/). It answers in XML. Any URL holding `win` that matches no other route runs it, even a `GET` (VERIFIED, `wled_server.cpp` `onNotFound` and `set.cpp` `handleSet`, `if (!(req.indexOf("win") >= 0)) return false`), so a `/win` URL is a write. It does not check the PIN, and `PS=` applies a preset and `RB` reboots through it. Use it only where a tool can do nothing but open a URL.

---

### JSON over serial

A line starting with `{` on the USB serial port at 115200 baud goes to the same state parser as `POST /json/state`, and `{"v":true}` returns state and info (VERIFIED, `wled_serial.cpp` `handleSerial` and https://kno.wled.ge/interfaces/serial/). It reaches the state only, never the config, and has no PIN check. It works only while the serial RX pin is not used for LEDs, and the reply needs the TX pin free (VERIFIED, docs "Pin usage limitation"). The `v` byte alone prints the WLED build number.

---

### Error codes

From `const.h` (VERIFIED): 1 permission denied, 2 another client active, 3 JSON buffer busy, 4 not implemented, 7 not enough memory for pixels, 8 effect memory full, 9 JSON parse failed or input too large, 10 file system did not start, 11 file system full, 12 preset does not exist, 19 general file system error.
