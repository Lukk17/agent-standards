# Sync, Realtime Streams and MQTT

Read this before making several WLED devices follow each other, streaming LED data from another program, or connecting a device to an MQTT broker. The rules live in [SKILL.md](../SKILL.md). Every setting here is a config change, made after a backup and a yes with `POST /json/cfg` the way "Change the config safely" in [json-api.md](json-api.md) shows, or with the full settings page, never with a partial Sync settings form.

Written for WLED 16. Sources: https://kno.wled.ge/interfaces/udp-realtime/, https://kno.wled.ge/interfaces/e1.31-dmx/, https://kno.wled.ge/interfaces/ddp/, https://kno.wled.ge/interfaces/mqtt/ and https://kno.wled.ge/interfaces/json-api/, and the WLED 16 source files `wled00/udp.cpp`, `mqtt.cpp`, `json.cpp`, `wled.cpp` and `wled.h` at https://github.com/wled/WLED. No packet here was sent to a device.

Contents:

1. [Ports](#ports)
2. [UDP sync between WLED devices](#udp-sync-between-wled-devices)
3. [Realtime streams](#realtime-streams)
4. [E1.31, Art-Net and DDP](#e131-art-net-and-ddp)
5. [MQTT](#mqtt)
6. [Safety](#safety)

---

### Ports

| Port | Protocol | Use | Source |
|---|---|---|---|
| UDP 21324 | WLED notifier, protocol version 12, also WARLS, DRGB, DRGBW, DNRGB | Sync between WLED devices, node discovery, simple realtime | VERIFIED, `wled.h` `udpPort`, `udp.cpp` `udpOut[11] = 12`, udp-realtime page |
| UDP 65506 | Second notifier port, TPM2.NET when set as the broadcast port | Realtime | VERIFIED, `wled.h` `udpPort2`, udp-realtime page |
| UDP 19446 | Hyperion UDP, protocol 0 | Ambilight, at most 490 LEDs | VERIFIED, `wled.h` `udpRgbPort`, udp-realtime page |
| UDP 5568 | E1.31 (sACN) | DMX lighting software | VERIFIED, `wled.h` `e131Port` |
| UDP 6454 | Art-Net | DMX lighting software | VERIFIED, `wled.h` comment on `e131Port` |
| UDP 4048 | DDP | Realtime from xLights, LedFx and others | VERIFIED, ddp page "WLED listens for DDP packets on port 4048", `wled.cpp` `ddp.begin` |
| UDP 11988, multicast 239.0.0.1 | Sound sync | Audio reactive builds | VERIFIED, udp-realtime page |
| TCP 1883 | MQTT client to the broker | Smart home control | VERIFIED, mqtt page, `wled.h` `mqttPort` |

All of these are plain UDP or TCP with no authentication. Anyone on the network who can send to the port can drive the LEDs.

---

### UDP sync between WLED devices

1. A device sends a notifier packet when the light changes through the web page or the HTTP API, and applies brightness, color, effect and palette from packets it receives, in group 1 for both by default (VERIFIED, `wled.h`, `notifyDirect`, `receiveNotificationBrightness`, `receiveNotificationColor`, `receiveNotificationEffects`, `receiveNotificationPalette`, `syncGroups` and `receiveGroups` all set to on or `0x01`). Segment options and bounds are not applied by default (`receiveSegmentOptions`, `receiveSegmentBounds` false).
2. Node discovery is on by default, so `GET /json/nodes` lists peers (VERIFIED, `wled.h` `nodeListEnabled`, `nodeBroadcastEnabled`).
3. The state keys `udpn.send`, `udpn.sgrp` and `udpn.rgrp` switch sending and set the send and receive groups at run time, and `udpn.nn` skips the packet for one call (VERIFIED, json-api page, `json.cpp` `deserializeState`).
4. The main segment's values are what UDP sync sends (VERIFIED, json-api page `mainseg`).
5. Packets with a protocol version under 9 are read in the old format, and custom versions above 199 are dropped (VERIFIED, `udp.cpp` `parseNotifyPacket`). Devices on very different WLED releases may not agree on every field (inferred, medium confidence).

To make two devices follow each other, read both configs, pick one group number, and set the send group on the leader and the receive group on the follower. Show the user both changes before sending them.

---

### Realtime streams

1. Realtime data takes over the LEDs and the effect stops. After the last packet the device waits for the timeout, 2500 ms by default, then goes back to normal (VERIFIED, `wled.h` `realtimeTimeoutMs`).
2. On the notifier port, byte 0 of the packet picks the protocol: 1 WARLS up to 255 LEDs, 2 DRGB up to 490, 3 DRGBW up to 367, 4 DNRGB up to 489 per packet, 0 the WLED notifier. Byte 1 is the timeout in seconds, and 255 means no timeout (VERIFIED, udp-realtime page).
3. `{"live":true}` in the JSON API blanks the LEDs and holds realtime mode until the state changes, and the docs expect `{"live":false}` when the sender stops (VERIFIED, json-api page `live`).
4. `lor` overrides live data: 1 until the live data ends, 2 until reboot (VERIFIED, json-api page).
5. Binary WebSocket messages also carry realtime packets: first byte 2 for DDP, the tested path, 0 for E1.31 and 1 for Art-Net, both untested by the docs' own account (VERIFIED, https://kno.wled.ge/interfaces/websocket/).
6. JSON over serial, Adalight and TPM2 work over USB at the serial baud rate, which "is only sufficient for about 50-100 LEDs" at 115200 (VERIFIED, https://kno.wled.ge/interfaces/serial/).

---

### E1.31, Art-Net and DDP

1. E1.31 carries "170 LEDs (510 DMX channels) per universe", and the docs suggest "no more than 3 universes (510 LEDs)" for 40 frames per second (VERIFIED, e1.31-dmx page). The first universe is 1 by default, unicast by default (VERIFIED, `wled.h` `e131Universe`, `e131Multicast`).
2. Art-Net uses the same settings, but "You will need to switch to Art-Net mode in Sync settings and reboot once" (VERIFIED, e1.31-dmx page). The switch to DDP mode on that same setting also needs a reboot.
3. DDP is received on port 4048 (VERIFIED, ddp page).
4. A reboot is a write, so changing the mode needs a yes for the setting and the reboot together.

---

### MQTT

1. Off by default, port 1883, and "Secure connections are not currently supported" (VERIFIED, `wled.h` `mqttEnabled`, mqtt page). Use a broker on the local network only, and a password used for nothing else.
2. The device topic defaults to `wled/` followed by the last 6 hex digits of the MAC address (VERIFIED, `wled.cpp`, `sprintf_P(mqttDeviceTopic, PSTR("wled/%*s"), 6, escapedMac.c_str() + 6)`). The docs write it as `wled/macaddr`.
3. Commands the device takes, on the device topic and on the optional group topic (VERIFIED, `mqtt.cpp` `onMqttConnect` and `onMqttMessage`, mqtt page):

| Topic | Payload |
|---|---|
| `<device-topic>` | Brightness 0 to 255, or `ON`, `OFF`, `T` to toggle |
| `<device-topic>/col` | Color as `#RRGGBB`, `#WWRRGGBB` or a 32 bit decimal |
| `<device-topic>/api` | A JSON API object starting with `{`, or an HTTP API string such as `FX=73` |
| `<group-topic>`, `<group-topic>/col`, `<group-topic>/api` | The same for every device in the group |

4. State the device publishes after a change (VERIFIED, `mqtt.cpp` `publishMqtt`):

| Topic | Payload |
|---|---|
| `<device-topic>/g` | Brightness 0 to 255 |
| `<device-topic>/c` | Color as `#RRGGBB`, or `#WWRRGGBB` when white is set |
| `<device-topic>/v` | The XML answer of the HTTP API |
| `<device-topic>/status` | `online`, retained, and `offline` as the last will |

5. The `/api` topic reaches the state only, like the JSON API state path, with no PIN check (VERIFIED, `mqtt.cpp`, `deserializeState`). It can save and delete presets and reboot, so anyone who can publish to the broker controls the device.
6. A `.local` broker name is resolved over mDNS since WLED 16 (VERIFIED, mqtt page).

---

### Safety

1. Read `GET /json/cfg` before and after each sync, realtime or MQTT change, and compare only the keys you meant to change.
2. A realtime sender left running holds the LEDs, and the light seems frozen to the user. Stop the sender, or send `{"live":false}`, before any other change.
3. Never send realtime packets to a device the user did not name, because a broadcast or multicast reaches every device that listens on the port.
