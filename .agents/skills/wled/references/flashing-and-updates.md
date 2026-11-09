# Flashing over USB and Updating over the Air

Read this before flashing WLED onto a board over USB, picking a firmware file, installing a USB to serial driver, or updating a running device. The rules live in [SKILL.md](../SKILL.md). Rule 4 there applies to every step on this page: flash, erase and update only when the user asked for that action by name, and back up `/presets.json` and `/cfg.json` first when the device still runs.

Written for WLED 16 and esptool v5. Sources: https://kno.wled.ge/basics/install-binary/, https://kno.wled.ge/basics/install-gui/ and https://kno.wled.ge/interfaces/serial/, the installer at https://install.wled.me and its repository https://github.com/wled/WLED-WebInstaller (`index.html`, `app.js`, `bin/boot/README.md`), the WLED 16 source files `wled00/wled_server.cpp`, `ota_update.cpp` and `wled_metadata.cpp` and `platformio.ini` at https://github.com/wled/WLED, the esptool v5 source `esptool/__init__.py` and `esptool/cli_util.py` at https://github.com/espressif/esptool, and the driver readme at https://github.com/WCHSoftGroup/ch34xser_macos. Nothing here was run against a board.

Contents:

1. [Pick the method](#pick-the-method)
2. [Pick the firmware file](#pick-the-firmware-file)
3. [The USB to serial driver](#the-usb-to-serial-driver)
4. [Linux](#linux)
5. [Windows](#windows)
6. [macOS](#macos)
7. [The web installer](#the-web-installer)
8. [esptool](#esptool)
9. [Boot mode and connection errors](#boot-mode-and-connection-errors)
10. [Update over the air](#update-over-the-air)
11. [A device that does not come back](#a-device-that-does-not-come-back)

---

### Pick the method

| Situation | Method |
|---|---|
| New board, desktop browser with Web Serial | The web installer |
| New board, no such browser, or the agent does it | `esptool` |
| Board that no longer boots | `esptool` with `erase-flash` first, which erases settings and presets |
| Running device, new release of the same build | OTA, `POST /update` |
| ESP01 builds | USB only, they answer 501 to `/update` |

---

### Pick the firmware file

A WLED release file is named `WLED_<version>_<release>.bin`, where `<release>` is the build name the device reports in `GET /json/info` as `release` (VERIFIED, `pio-scripts/output_bins.py` builds the name from `WLED_RELEASE_NAME`, and `json.cpp` `serializeInfo` reports `releaseString`). For an update, read `release` from the device and download that exact name:

```bash
curl -s http://<wled-host>/json/info
```

The files of every release are on https://github.com/wled/WLED/releases. Without a browser, list the file names of one release through the GitHub API, which needs no login:

```bash
curl -s https://api.github.com/repos/wled/WLED/releases/tags/<tag>
```

The `assets` array holds `name` and `browser_download_url` for each file. With the GitHub command line installed, `gh release view <tag> --repo wled/WLED` shows the same list.

The WLED 16 release names, VERIFIED in the `WLED_RELEASE_NAME` flags of `platformio.ini` and the assets of a WLED 16 release:

| Chip | Release names |
|---|---|
| ESP32 | `ESP32`, `ESP32_Ethernet`, `ESP32_WROVER`, `ESP32_DEBUG`, `ESP32_HUB75`, `ESP32_HUB75_forum_pinout` |
| ESP32-C3 | `ESP32-C3`, `ESP32-C3-QIO` |
| ESP32-S2 | `ESP32-S2` |
| ESP32-S3 | `ESP32-S3_4M_qspi`, `ESP32-S3_8MB_qspi`, `ESP32-S3_8MB_opi`, `ESP32-S3_8MB_none`, `ESP32-S3_16MB_opi`, `ESP32-S3_WROOM-2`, and the HUB75 and board builds |
| ESP8266, 4 MB flash | `ESP8266`, `ESP8266_160`, `ESP8266_compat` |
| ESP8266, 2 MB flash | `ESP02`, `ESP02_160`, `ESP02_compat`, `ESP02_min` |
| ESP8266, 1 MB flash | `ESP01`, `ESP01_160`, `ESP01_compat`, all without OTA |

A release file is the application only. The installer's boot README says it "does not contain a 2nd-stage bootloader or a partition table, and flashing it alone to a bare/erased chip will not boot" (VERIFIED, `bin/boot/README.md` in the WLED-WebInstaller repository). WLED does not publish those parts per chip, and the installer repository ships them under `bin/boot/bootloaders/<chip>/` and `bin/boot/partitions/`.

---

### The USB to serial driver

A computer needs a driver for the USB to serial chip on the board, not for the ESP itself, so which driver depends on the board. Look at the chip next to the USB socket, or at the USB vendor ID the computer reports.

| Chip on the board | Driver |
|---|---|
| WCH CH340, CH341, CH343, CH9102 (the CH34x family), USB vendor ID `1a86` | Built into Linux. Windows and macOS probably need the WCH driver |
| Silicon Labs CP2102, CP2104 and the other CP210x | Built into Linux. Windows probably needs the Silicon Labs driver |
| No bridge chip, the ESP's own USB on ESP32-S2, S3 and C3 | No driver needed, the board shows up as a USB serial device of its own |

The vendor ID `1a86` and the CH34x chip list are VERIFIED in the WCH readme at https://github.com/WCHSoftGroup/ch34xser_macos. Linux ships the drivers in the kernel: `ch341` (`drivers/usb/serial/ch341.c`), `cp210x` (`drivers/usb/serial/cp210x.c`) and `cdc_acm` for native USB (`drivers/usb/class/cdc-acm.c`), VERIFIED in the kernel source at https://github.com/torvalds/linux. A distribution can still build them as modules or leave one out, so `modinfo ch341` shows whether the running kernel has it. That native USB on ESP32-S2, S3 and C3 needs no driver on Windows and macOS is UNVERIFIED in this skill, high confidence. Many ESP32-S3 and C3 boards carry a bridge chip as well, often on a second USB socket, and then the bridge needs its driver.

---

### Linux

1. A bridge chip shows up as `/dev/ttyUSB<n>`, native USB as `/dev/ttyACM<n>`.
2. The device belongs to the group `dialout` on Debian, Ubuntu and Fedora, and to `uucp` on Arch, so add the user to that group or the port refuses to open. The WLED docs give the same tip: "make sure you give yourself permission to use that device, for example by adding your user to the group that has access to the tty port" (VERIFIED, install-binary page). The group names are UNVERIFIED in this skill, high confidence. Read the group of the port:

```bash
ls -l /dev/ttyUSB0 /dev/ttyACM0
```

3. ModemManager can open a new serial port to probe it and get in the way of flashing, and `brltty` can claim a CH340 with ID `1a86:7523` and make the port vanish. Both are from community sources, medium confidence, UNVERIFIED. Stopping or removing either is a change on the user's computer that needs a yes.
4. Read which bridge is attached, a read with no side effects:

```bash
lsusb
```

---

### Windows

1. The board shows up as a COM port under Ports (COM & LPT) in Device Manager.
2. List the port names from PowerShell (UNVERIFIED, not run here):

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
```

3. CP210x driver: Silicon Labs publishes it at https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers. That page answered HTTP 403 to an automated fetch, so its content is UNVERIFIED here.
4. CH34x driver: WCH publishes it at https://www.wch.cn/downloads/CH341SER_ZIP.html (page reached, not read in detail). Windows Update may install it by itself, UNVERIFIED.
5. GUI tool: the WLED docs name Espressif's Flash Download Tool, "an official GUI tool for Windows" that "can be used for the ESP8266 and ESP32" (VERIFIED, https://kno.wled.ge/basics/install-gui/). The agent uses `esptool` instead.
6. Run `esptool` the same way as on Linux, with `--port COM<n>`.

---

### macOS

1. Use the `/dev/cu.*` name of the port, such as `/dev/cu.usbserial-<id>` or `/dev/cu.usbmodem<id>`. That `cu` rather than `tty` is the one to open is UNVERIFIED in this skill, high confidence.
2. List the candidates:

```bash
ls /dev/cu.*
```

3. CH34x: macOS probably has no built-in driver for these chips, so the WCH driver is likely needed (UNVERIFIED). The WCH readme names "OS X 11.0(Big Sur) and above" as supported and says that from OS X 11 on, after installing, the user opens the CH34xVCPDriver app from Launchpad and clicks Install, and that newer macOS releases ask the user to allow it in the system settings (VERIFIED, https://github.com/WCHSoftGroup/ch34xser_macos). Installing a driver is a change on the user's computer that needs a yes, and the allow step is the user's.
4. CP210x on macOS: whether a driver is built in is UNVERIFIED.

---

### The web installer

1. https://install.wled.me flashes over Web Serial from the browser. The WLED docs say: "Make sure you are running a desktop version of Chrome, Edge, Opera, or Firefox 151 or newer" and "Safari cannot be used" (VERIFIED, https://kno.wled.ge/basics/install-binary/). The installer's own fallback text says "Please try on Desktop Chrome or Edge" (VERIFIED, `index.html`).
2. It is built on ESP Web Tools and offers to erase the flash before a new install (VERIFIED, `index.html` loads `esp-web-tools`, `app.js` sets `new_install_prompt_erase: true`). Erasing removes settings and presets.
3. It writes the bootloader and partition table with the firmware, and patches the bootloader for the chosen flash size in the browser (VERIFIED, `bin/boot/README.md`).
4. The WLED docs say "Improv is used by the WLED web installer for an easy installation and setup process" (VERIFIED, serial page), so the installer asks for Wi-Fi at the end.
5. Chips: ESP32, ESP32-C3, ESP32-S2, ESP32-S3 and ESP8266 (VERIFIED, `chipFamily` in `app.js`). The docs say the installer "is not yet available for ESPs with flash chips smaller than 4MB", but `app.js` maps ESP8266 1 MB and 2 MB to the ESP01 and ESP02 builds. Docs and installer disagree, so check the installer page itself.
6. The user clicks through the browser dialogs. The agent cannot do this step.

---

### esptool

1. Install it from PyPI into a virtual environment, then run it as `esptool`. In v5 the commands are written with dashes, such as `write-flash`, `erase-flash` and `flash-id`, and the v4 names with underscores run with a warning "Deprecated: Command ... is deprecated" (VERIFIED, `esptool/cli_util.py` `get_command`). The `esptool.py` name is deprecated too (VERIFIED, `check_deprecated_py_suffix` in `esptool/__init__.py`). Installing with pipx is UNVERIFIED.

```bash
python3 -m pip install esptool
```

2. Read the chip and the flash size first, which writes nothing:

```bash
esptool --port <serial-port> flash-id
```

3. The WLED esptool page does not match esptool v5 or the ESP32 layout: it uses `esptool.py`, covers only ESP8266 and ESP32, and writes a WLED 0.13 ESP32 bootloader at `0x0` (VERIFIED, install-binary page). On a classic ESP32 the bootloader belongs at `0x1000`, so do not follow that page for ESP32.
4. Offsets for a full install, VERIFIED in `bin/boot/README.md` of the installer repository for the bootloader and partition table, the application at `0x10000` VERIFIED on the WLED install-binary page:

| Chip | Bootloader | Partition table | Application |
|---|---|---|---|
| ESP32, ESP32-S2 | `0x1000` | `0x8000` | `0x10000` |
| ESP32-C3, ESP32-S3 | `0x0` | `0x8000` | `0x10000` |
| ESP8266 | none | none | the one release file at `0x0` |

5. A new board, after the user asked for an erase. This erases settings and presets:

```bash
esptool --port <serial-port> erase-flash
```

6. ESP8266:

```bash
esptool --port <serial-port> write-flash 0x0 WLED_<version>_<release>.bin
```

7. ESP32 or ESP32-S2, with the bootloader and the partition table for the board's flash size from the installer repository. `--flash-size detect` makes esptool set the size in the bootloader header to the real chip, because `write-flash` keeps the header as it is by default (VERIFIED, `esptool/__init__.py`, the `--flash-size` default `keep` and the `detect` choice for `write-flash`). The installer README says the bootloader files are built for 8 MB and patched for other sizes.

```bash
esptool --port <serial-port> write-flash --flash-size detect 0x1000 <bootloader>.bin 0x8000 <partitions>.bin 0x10000 WLED_<version>_<release>.bin
```

8. ESP32-C3 or ESP32-S3, the same with the bootloader at `0x0`:

```bash
esptool --port <serial-port> write-flash --flash-size detect 0x0 <bootloader>.bin 0x8000 <partitions>.bin 0x10000 WLED_<version>_<release>.bin
```

9. Pick the partition file by chip and flash size, such as `partitions_s3_8m.bin`, and on ESP32-C3 the DIO or QIO bootloader that matches the board. The README explains the choices. After an erase, empty OTA data makes the board boot the first application slot, so no OTA data file is needed (VERIFIED, README).
10. For an update of a board that runs, prefer OTA. Writing only the application at `0x10000` over USB keeps the settings, but a board that last updated over the air may boot from its second slot and keep running the old firmware (inferred from the two slot layout, medium confidence, UNVERIFIED).

---

### Boot mode and connection errors

1. Most boards enter the ROM download mode by themselves when esptool connects. The WLED docs say that when esptool shows `Connecting...`, "some ESP32 boards require you to hold the boot button" (VERIFIED, install-binary page). The boot button pulls GPIO0 low during reset, GPIO9 on ESP32-C3 (UNVERIFIED in this skill, high confidence).
2. On read or write errors, lower the speed with `--baud 115200`.
3. The ESP8266 ROM prints its boot messages at 74880 baud, so a serial monitor at 115200 shows garbage right after reset (UNVERIFIED in this skill, high confidence).
4. Advice on brownouts during flashing was not found in the WLED docs (UNVERIFIED). Use a USB cable and port that can carry the board's current, with the LED strip unplugged or powered separately.

---

### Update over the air

1. Check the guards first, as [security-and-pin.md](security-and-pin.md) shows: the PIN, the OTA lock and the same subnet rule. ESP01 builds have no OTA and answer 501 "This build does not support OTA update." (VERIFIED, `wled_server.cpp`, `platformio.ini`).
2. Read the device before choosing a file. `GET /json/info` gives `ver`, `release`, `arch`, `flash` (flash size in MB), `freeheap` and `maxalloc` (free heap and its largest block, in bytes) and `fs.u` and `fs.t` (file system used and total, in KB). WLED 0.15 reports the same keys (VERIFIED, `json.cpp` `serializeInfo` in the WLED 16 and WLED 0.15 source). Tell the user the values, and stop when `flash` is smaller than the release needs, such as an `ESP8266` build on a board that reports 1 or 2 MB.
3. The running firmware does the checking, not the new file. WLED 16 refuses another build with "Firmware release name mismatch: current='...', uploaded='...'.", a file without WLED metadata with "This firmware file is missing compatibility metadata.", and a file that demands a newer running version with "Cannot update from this version: requires at least ...". A `_V4` suffix on either name is ignored, so `ESP32` and `ESP32_V4` match (VERIFIED, `wled_metadata.cpp` `shouldAllowOTA`, `ota_update.cpp`). WLED 0.15 and older have none of these checks: the upload handler writes any file it gets (VERIFIED, `wled_server.cpp` in the WLED 0.15 source calls `Update.begin` with no check, and `wled_metadata.cpp` does not exist there). So on a device older than WLED 16 the agent checks it alone: the `<release>` in the file name equals `release` from step 2, and the chip in that name matches `arch`.
4. A jump of a major version, such as WLED 0.15 to 16 on an ESP8266, carries more risk than an update within one major version. The WLED 16 `ESP8266` file is about 5 percent larger than the WLED 0.15 one (VERIFIED, asset sizes in the GitHub releases API), and an ESP8266 has little flash and memory to spare. That this makes the jump fail more often is UNVERIFIED: no WLED source, release note or issue found states it. Say so to the user before the upload, with the `freeheap` and `flash` values from step 2.
5. Say before the upload that an ESP8266 has no `/update?revert`, because the rollback code is compiled only for ESP32 (VERIFIED, `wled_server.cpp`, the `revert` branch sits inside `#ifdef ARDUINO_ARCH_ESP32`). If the new firmware does not boot, USB flashing is the only way back.
6. Back up `/presets.json` and `/cfg.json`. The device also copies its config to `/bkp.cfg.json` before an update (VERIFIED, `ota_update.cpp`).
7. Check the download against the digest GitHub gives for each release file. The releases API returns a `digest` field in the form `sha256:<digest>` for every asset (VERIFIED, the releases API answered with that field for a WLED 16 release). Read it:

```bash
curl -s https://api.github.com/repos/wled/WLED/releases/tags/<tag> | python3 -c "import json,sys; [print(a['name'], a.get('digest')) for a in json.load(sys.stdin)['assets']]"
```

   Then hash the file and compare the two values. On Linux:

```bash
sha256sum WLED_<version>_<release>.bin
```

   On macOS:

```bash
shasum -a 256 WLED_<version>_<release>.bin
```

   On Windows PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 WLED_<version>_<release>.bin
```

   Stop when they differ. A missing `digest` means the check cannot be done, so tell the user.
8. Upload as multipart form data to `/update`. The web page names the file field `update`:

```bash
curl -s -F "update=@WLED_<version>_<release>.bin" http://<wled-host>/update
```

9. `skipValidation=1` sent as a form field before the file skips the release name check on WLED 16 (VERIFIED, `ota_update.cpp`, `request->getParam("skipValidation", true)`). Use it only when the user asks for a cross-build change by name, because the wrong build can leave LEDs dark or the board unable to boot.
10. The answer is "Update successful!" and a reboot, or "Update failed!" with the reason. An "Update successful!" only means the file was written, not that it boots.
11. Wait for the device. The device's own reboot message says "Please wait ~10 seconds." (VERIFIED, `wled_server.cpp`, the `/reset` handler). Poll `GET /json/info` every 5 seconds, for up to 3 minutes, which is a margin chosen here and not a WLED figure. Success is an answer with the new `ver` and the same `release`. Failure is no answer after 3 minutes, an answer with the old `ver`, or a device that answers and drops again.
12. Roll back on ESP32: `GET /update?revert` boots the previous firmware slot when one is there, from a client in a private range (VERIFIED, `wled_server.cpp` `serveSettings`). It is a firmware change, so only when the user names it.
13. `POST /updatebootloader` replaces the ESP32 bootloader and checks the chip ID ("Chip ID mismatch") (VERIFIED, `wled_server.cpp`, `ota_update.cpp`). A failed bootloader write can leave the board unbootable until it is flashed over USB, so do it only when the user asks for a bootloader update by name.

---

### A device that does not come back

Work through these in order, and tell the user each step before it:

1. Look for WLED-AP near the board. With the default access point setting, a device that boots but cannot join its Wi-Fi opens WLED-AP about 12 seconds after a failed reconnect attempt (VERIFIED, `wled.cpp` `WLED::handleConnection`), so WLED-AP means the board booted and the problem is the Wi-Fi link. Join it as [first-setup.md](first-setup.md) shows and read `GET /json/info` at `4.3.2.1`. No WLED-AP while the phone or laptop is in range points to a board that does not boot or reboots in a loop. That reading fails when the access point setting is 3 (button only) or 4 (closes after 5 minutes), so check `ap.behav` in the config backup first.
2. The user power cycles the board: unplug it, wait 10 seconds, plug it in. This is the user's step. Wait as in step 11 above.
3. Read the serial log over USB, read only, with no byte sent. WLED prints at 115200 baud (VERIFIED, `wled.cpp` `WLED::setup`). Open the port with DTR and RTS held off, as [first-setup.md](first-setup.md) explains, then ask the user to power cycle the board while the port is open, and keep the output. A crash report, a line of repeated boot messages, or nothing at all are the useful results. With pyserial (UNVERIFIED, not run here):

```bash
python3 -m serial.tools.miniterm --dtr 0 --rts 0 <serial-port> 115200
```

   After 5 crashes in a row, each within 2 minutes of the boot before, WLED first restores `/bkp.cfg.json`, then resets the config, and on ESP8266, which has no second slot to boot, then prints the files to serial (VERIFIED, `util.cpp` `handleBootLoop`, the ESP8266 case falls through to the dump). Those are signs of a boot loop in the log.
4. Flash over USB as the sections above show, with the build that ran before or the new one, after the user asks for it by name. An erase removes settings and presets, so restore `/presets.json` and `/cfg.json` from the backup afterwards as [backup-and-restore.md](backup-and-restore.md) shows, and enter the Wi-Fi password again, because the backup has no passwords.
