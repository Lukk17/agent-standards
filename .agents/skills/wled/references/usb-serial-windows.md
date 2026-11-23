# USB Serial Port on Windows

Read this before flashing a board over USB from a Windows computer: the COM port, the driver for the bridge chip, and the GUI tool the WLED docs name. The driver table, the firmware file, the web installer and the `esptool` steps are in [flashing-and-updates.md](flashing-and-updates.md). The rules live in [SKILL.md](../SKILL.md), and rule 4 there applies: flash only when the user asked for that action by name.

---

### Find and open the port

1. The board shows up as a COM port under Ports (COM & LPT) in Device Manager.
2. List the port names from PowerShell (UNVERIFIED, not run here):

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
```

3. CP210x driver: Silicon Labs publishes it at https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers. That page answered HTTP 403 to an automated fetch, so its content is UNVERIFIED here.
4. CH34x driver: WCH publishes it at https://www.wch.cn/downloads/CH341SER_ZIP.html (page reached, not read in detail). Windows Update may install it by itself, UNVERIFIED.
5. GUI tool: the WLED docs name Espressif's Flash Download Tool, "an official GUI tool for Windows" that "can be used for the ESP8266 and ESP32" (VERIFIED, https://kno.wled.ge/basics/install-gui/). The agent uses `esptool` instead.
6. Run `esptool` as [flashing-and-updates.md](flashing-and-updates.md#esptool) shows, with `--port COM<n>`.
