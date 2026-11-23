# USB Serial Port on Linux

Read this before flashing a board over USB from a Linux computer: the port name, the group that may open it, and the programs that can get in the way. The driver table, the firmware file, the web installer and the `esptool` steps are in [flashing-and-updates.md](flashing-and-updates.md). The rules live in [SKILL.md](../SKILL.md), and rule 4 there applies: flash only when the user asked for that action by name.

---

### Find and open the port

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
