# First Setup: WLED-AP, Improv and Finding the Device

Read this before bringing a new, freshly flashed or factory reset device onto Wi-Fi, and when a device has to be found on the network. The rules live in [SKILL.md](../SKILL.md). Rule 4 there applies: giving a device Wi-Fi credentials is a Wi-Fi change, so do it only when the user asked for the setup, and confirm the network name with the user first.

Written for WLED 16. Sources: https://kno.wled.ge/basics/getting-started/, https://kno.wled.ge/interfaces/serial/, https://kno.wled.ge/advanced/custom-ap/ and https://kno.wled.ge/features/settings/, the Improv Wi-Fi serial specification at https://www.improv-wifi.com/serial/, and the WLED 16 source files `wled00/improv.cpp`, `wled_serial.cpp`, `wled.cpp`, `wled_server.cpp`, `cfg.cpp`, `button.cpp`, `wled.h` and `const.h` at https://github.com/wled/WLED. No packet and no call here was sent to a device.

Contents:

1. [Pick the path](#pick-the-path)
2. [Path 1: Improv over USB serial](#path-1-improv-over-usb-serial)
3. [The Improv serial packet](#the-improv-serial-packet)
4. [What WLED does with Improv](#what-wled-does-with-improv)
5. [Path 2: the WLED-AP access point](#path-2-the-wled-ap-access-point)
6. [When the access point opens](#when-the-access-point-opens)
7. [Find the device afterwards](#find-the-device-afterwards)

---

### Pick the path

| Situation | Path | Who does what |
|---|---|---|
| The board is plugged into the agent's computer by USB | Improv over serial | The agent does it all, the user gives the Wi-Fi name and password |
| The board was just flashed with the web installer | The installer asks for Wi-Fi over Improv at the end | The user types it in the browser |
| No USB link, the board is already mounted | WLED-AP | The user joins WLED-AP with a phone or laptop and types the Wi-Fi details |
| The agent's computer has a second Wi-Fi adapter, or runs on Ethernet with a free Wi-Fi adapter | WLED-AP from the agent | The agent may join WLED-AP after the user says yes to that change on the computer |

The agent usually cannot join WLED-AP itself. Joining it switches the computer's only Wi-Fi link to the device's network, which drops the agent's own connection to the user, the internet and the tools it runs through. So on a computer with one Wi-Fi link, the user does the access point steps by hand.

---

### Path 1: Improv over USB serial

1. Find the serial port as [flashing-and-updates.md](flashing-and-updates.md) shows for each operating system.
2. Use 115200 baud. The docs say: "The baud rate must remain at the default `115200` setting for the device to be detected as Improv-capable" (VERIFIED, https://kno.wled.ge/interfaces/serial/, and `wled.cpp` `WLED::setup`, `Serial.begin(115200)`).
3. Serial works only while the RX pin is not used for LEDs, and answers need the TX pin free (VERIFIED, docs "Pin usage limitation", `wled_serial.cpp` `handleSerial`, `serialCanRX`).
4. Check that WLED answers before sending credentials. A single `v` byte prints `WLED` and the build number (VERIFIED, `wled_serial.cpp`). Then send the Improv state request 0x02 and wait for a Current State packet, send the device information request 0x03, and go on only when the first string of the answer is `WLED`.
5. Check that the SSID is at most 32 bytes and the whole Wi-Fi data at most 126 bytes, because WLED drops a longer command without an answer (VERIFIED, `improv.cpp` `parseWiFiCommand`). Then send the Wi-Fi settings command. Read the password from where the user keeps it, straight into the program, never onto the screen or into the shell history.
6. Wait for the Provisioned state and the RPC result that carries `http://<ip>`, or for error 0x03, unable to connect.

Opening a serial port can reset an ESP board, because many USB to serial bridges wire DTR and RTS to the reset and boot pins. Open the port with both lines off, as the sketch below does (inferred from the usual auto-reset circuit, medium confidence, UNVERIFIED on a device).

A Python sketch with pyserial that follows steps 4 to 6, UNVERIFIED because it was not run against a device. It takes the port and the SSID as arguments and reads the password from standard input:

```python
import sys
import time

import serial

HEADER = b"IMPROV"


def improv_packet(rpc_command: int, data: bytes) -> bytes:
    body = bytes([rpc_command, len(data)]) + data
    packet = HEADER + bytes([1, 0x03, len(body)]) + body
    return packet + bytes([sum(packet) & 0xFF])


def read_packets(link: serial.Serial, seconds: float):
    buffer = b""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        buffer += link.read(256)
        start = buffer.find(HEADER)
        while start >= 0 and len(buffer) >= start + 9:
            end = start + 9 + buffer[start + 8] + 1
            if len(buffer) < end:
                break
            packet = buffer[start:end]
            buffer = buffer[end:]
            if packet[6] == 1 and sum(packet[:-1]) & 0xFF == packet[-1]:
                yield packet[7], packet[9:-1]
            start = buffer.find(HEADER)


def strings(data: bytes) -> list[str]:
    found, pos = [], 2
    while pos < len(data):
        size = data[pos]
        found.append(data[pos + 1:pos + 1 + size].decode("utf-8", "replace"))
        pos += 1 + size
    return found


def wait_for(link: serial.Serial, packet_type: int, command: int | None, seconds: float) -> bytes:
    for kind, data in read_packets(link, seconds):
        if kind == 0x02 and data and data[0] != 0x00:
            raise SystemExit(f"Improv error {data[0]:#04x}")
        if kind == packet_type and (command is None or (data and data[0] == command)):
            return data
    raise SystemExit("no Improv answer")


port, ssid = sys.argv[1], sys.argv[2]
password = sys.stdin.readline().rstrip("\n")
ssid_bytes = ssid.encode("utf-8")
password_bytes = password.encode("utf-8")
wifi = bytes([len(ssid_bytes)]) + ssid_bytes + bytes([len(password_bytes)]) + password_bytes
if len(ssid_bytes) > 32 or len(wifi) > 126:
    raise SystemExit("SSID over 32 bytes or Wi-Fi data over 126 bytes")

link = serial.Serial()
link.port = port
link.baudrate = 115200
link.timeout = 0.2
link.dtr = False
link.rts = False
link.open()

link.write(improv_packet(0x02, b""))
print("state", hex(wait_for(link, 0x01, None, 5)[0]))

link.write(improv_packet(0x03, b""))
info = strings(wait_for(link, 0x04, 0x03, 5))
if not info or info[0] != "WLED":
    raise SystemExit(f"not a WLED device: {info}")
print("device", info)

link.write(improv_packet(0x01, wifi))
print("result", strings(wait_for(link, 0x04, 0x01, 30)))
link.close()
```

The last line prints the RPC result of the Wi-Fi command, whose string is `http://<ip>` once the device is connected. An error 0x03 ends the program with "Improv error 0x03", unable to connect.

---

### The Improv serial packet

From https://www.improv-wifi.com/serial/ (VERIFIED, fetched as raw page text). All strings are UTF-8.

| Byte | Content |
|---|---|
| 1 to 6 | The header `IMPROV` |
| 7 | Version, 1 |
| 8 | Type |
| 9 | Length of the data |
| 10 to X | Data |
| X + 1 | Checksum |

The specification page lists the checksum byte but does not say how it is computed. WLED computes it as the sum of every byte before it, header included, kept to the low 8 bits, both when it checks a packet and when it sends one (VERIFIED, `improv.cpp` `handleImprovPacket` and `sendImprovStateResponse`). WLED also writes a line feed after each packet it sends.

| Type | Name | Direction |
|---|---|---|
| 0x01 | Current state | Device to client |
| 0x02 | Error state | Device to client |
| 0x03 | RPC command | Client to device |
| 0x04 | RPC result | Device to client |

States: 0x00 stopped, 0x02 ready (authorized), 0x03 provisioning, 0x04 provisioned. Errors: 0x00 none, 0x01 invalid RPC packet, 0x02 unknown RPC command, 0x03 unable to connect, 0x05 bad hostname, 0xFF unknown.

An RPC command's data is: the command byte, the data length, then the data. The Wi-Fi command 0x01 carries the SSID length, the SSID, the password length and the password. The specification's own example for SSID `MyWirelessAP` and password `mysecurepassword` is `01 1E 0C {MyWirelessAP} 10 {mysecurepassword}`. An RPC result's data is the command it answers, the data length, then strings, each one a length byte and the text.

| Command | Name | In WLED 16 |
|---|---|---|
| 0x01 | Send Wi-Fi settings | Yes |
| 0x02 | Request current state | Yes |
| 0x03 | Request device information | Yes |
| 0x04 | Request scanned Wi-Fi networks | Yes, except on ESP32-S2, C3 and S3, where it is compiled out |
| 0x05 | Get or set hostname | No, answers error 0x02 |
| 0x06 | Get or set device name | No, answers error 0x02 |
| 0x07 | Get network state | No, answers error 0x02 |

The WLED column is VERIFIED in `improv.cpp`: the `switch (rpcCommandType)` handles 0x01 to 0x04 and sends error 0x02 for anything else, and `WLED_DISABLE_IMPROV_WIFISCAN` is defined for those three chips.

---

### What WLED does with Improv

All VERIFIED in `improv.cpp` and `wled.cpp`.

1. Only RPC command packets are accepted, version 1 only, and a wrong checksum answers error 0x01.
2. The state request answers 0x02 when no Wi-Fi is configured, 0x03 when it is configured but not connected, and 0x04 plus an RPC result with `http://<ip>` when connected.
3. The device information request answers `WLED`, the version and build as `<ver>/<build>`, the chip name such as `esp32` or `esp8266`, and the mDNS name, or the device name when the user changed it from `WLED`.
4. The Wi-Fi command takes an SSID of at most 32 bytes and data of at most 126 bytes, writes them into Wi-Fi slot 0, replacing what was there, saves the config and reconnects. It does not check the settings PIN.
5. After connecting, the device sends state 0x04 and an RPC result with `http://<ip>`. When the connection does not come up, it sends error 0x03.
6. There is no Improv over Bluetooth in WLED.

Because Improv needs no PIN, anyone with USB access to the board can change its Wi-Fi. JSON over serial reaches the state only, never the config, so Improv is the only serial route to the Wi-Fi settings (VERIFIED, `wled_serial.cpp`).

---

### Path 2: the WLED-AP access point

1. The access point is named `WLED-AP` with the password `wled1234`, unless the firmware was built with other values (VERIFIED, `const.h` `DEFAULT_AP_SSID` and `DEFAULT_AP_PASS`, and https://kno.wled.ge/advanced/custom-ap/).
2. The device is at `4.3.2.1` on that network, and answers every other name with a redirect to it, so a phone shows a sign-in page (VERIFIED, `wled_server.cpp` `captivePortal`). The docs say "Open `wled.me` in your browser to control your lights. The IP `4.3.2.1` works too while you're connected to WLED-AP" (VERIFIED, https://kno.wled.ge/basics/getting-started/).
3. The Wi-Fi settings page needs no PIN while no Wi-Fi is configured (VERIFIED, `wled_server.cpp` `serveSettings`).
4. The user steps, to give the user word for word:
   1. On a phone or laptop, join the Wi-Fi network `WLED-AP` with the password `wled1234`.
   2. Open `http://4.3.2.1` in the browser.
   3. Press the Config (gear) icon, open WiFi & Network, enter the home Wi-Fi name and password, and press Save & Connect. The docs call the menu entry "WiFi Setup", the firmware labels it WiFi & Network (VERIFIED, https://kno.wled.ge/basics/getting-started/ and `wled00/data/settings.htm`).
   4. Rejoin the home Wi-Fi on the phone or laptop.
5. The docs also tell the user to change the access point password, "since `wled1234` is the same on every WLED device" (VERIFIED, getting-started page). Suggest it, as a later change with its own yes.
6. An agent that may join WLED-AP, on a computer with a spare Wi-Fi link, can set Wi-Fi with one config call instead of the form. The body below adds the network to slot 0 and reboots. A slot sent without `ip`, `gw` and `sn` uses DHCP (VERIFIED, `cfg.cpp` `deserializeConfig`, and `"rb"` at its end). Never send the Wi-Fi settings form partly filled, see rule 5 in [SKILL.md](../SKILL.md).

```bash
curl -s -X POST -H 'Content-Type: application/json' --data-binary @- http://4.3.2.1/json/cfg
```

The body holds `{"nw":{"ins":[{"ssid":"<ssid>","psk":"<wifi-password>"}]},"rb":true}` plus the five keys copied from `GET /json/cfg` that the section "Change the config safely" of [json-api.md](json-api.md) lists, because a config body without them resets them. Feed it on standard input, as the command shows. The command to join WLED-AP from Linux, for example `nmcli device wifi connect WLED-AP password wled1234 ifname <wifi-device>`, is UNVERIFIED, not run here, and it is a change on the user's computer that needs a yes.

---

### When the access point opens

The access point behaviour is a choice on the Wi-Fi settings page and the key `ap.behav` in the config (VERIFIED, `cfg.cpp`, `const.h` `AP_BEHAVIOR_*` and `wled.cpp` `WLED::handleConnection`):

| Value | Opens |
|---|---|
| 0, the default | When there is no connection after boot. With Wi-Fi configured, about 12 seconds after a reconnect attempt that failed, only if it never connected since boot |
| 1 | Also whenever the connection is lost |
| 2 | Always |
| 3 | Only when button 0 is held |
| 4 | Like 0, but only during the first 5 minutes, and it closes when no client is connected after that |

With no Wi-Fi configured the access point opens at boot. Once the device connects, the access point closes unless the setting is 2. Holding button 0 for more than 5 seconds and releasing it opens the access point, more than 10 seconds is a factory reset, so tell the user to count (VERIFIED, `button.cpp`).

---

### Find the device afterwards

1. Improv already printed `http://<ip>` and the mDNS name.
2. mDNS: a device answers at `wled-` followed by the last 6 hex digits of its MAC address, with `.local` after it, unless the user set another name (VERIFIED, `wled.cpp` `WLED::setup`). It announces `_http._tcp` and `_wled._tcp` on port 80 with a TXT record `mac` (VERIFIED, `wled.cpp` `WLED::initInterfaces`).
3. Browsing mDNS sends queries that every device on the network answers, so it is a read, but it touches the network. On Linux with Avahi, flags checked in `avahi-browse --help`:

```bash
avahi-browse -r -t _wled._tcp
```

On macOS (UNVERIFIED, not run here):

```bash
dns-sd -B _wled._tcp
```

4. Ask a WLED device that is already known. `GET /json/nodes` lists the devices it heard on UDP port 21324 with name, type, IP address, age and build (VERIFIED, `json.cpp` `serializeNodes`, and https://kno.wled.ge/interfaces/json-api/).

```bash
curl -s http://<wled-host>/json/nodes
```

5. The router's list of clients shows the device by its host name. The user reads it, the agent does not log into the router for this.
6. Confirm the find with `GET /json/info`: `brand` is `WLED` on standard builds, and `mac`, `ip`, `ver` and `release` identify the device and the firmware build (VERIFIED, `json.cpp` `serializeInfo`).
