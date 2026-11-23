# USB Serial Port on macOS

Read this before flashing a board over USB from a Mac: the port name and the driver for the bridge chip. The driver table, the firmware file, the web installer and the `esptool` steps are in [flashing-and-updates.md](flashing-and-updates.md). The rules live in [SKILL.md](../SKILL.md), and rule 4 there applies: flash only when the user asked for that action by name.

---

### Find and open the port

1. Use the `/dev/cu.*` name of the port, such as `/dev/cu.usbserial-<id>` or `/dev/cu.usbmodem<id>`. That `cu` rather than `tty` is the one to open is UNVERIFIED in this skill, high confidence.
2. List the candidates:

```bash
ls /dev/cu.*
```

3. CH34x: macOS probably has no built-in driver for these chips, so the WCH driver is likely needed (UNVERIFIED). The WCH readme names "OS X 11.0(Big Sur) and above" as supported and says that from OS X 11 on, after installing, the user opens the CH34xVCPDriver app from Launchpad and clicks Install, and that newer macOS releases ask the user to allow it in the system settings (VERIFIED, https://github.com/WCHSoftGroup/ch34xser_macos). Installing a driver is a change on the user's computer that needs a yes, and the allow step is the user's.
4. CP210x on macOS: whether a driver is built in is UNVERIFIED.
