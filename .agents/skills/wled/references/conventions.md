# Conventions

Companion reference for the [wled](../SKILL.md) skill. Load it before writing a command or a note that names a device, and when judging how far to trust a fact in the topic files.

---

### Facts about one setup

The address, mDNS name, PIN and OTA password of a real device, the Wi-Fi credentials and the MQTT broker belong in the user's own notes, never in this skill or a shared repository. Examples use placeholders: `<wled-host>` for the IP address or mDNS name, `<pin>`, `<serial-port>`, `<backup-dir>`.

---

### Verification

The skill is written for WLED 16. A fact marked VERIFIED was read in the WLED 16 source under `wled00/` at https://github.com/wled/WLED or in the WLED docs at https://kno.wled.ge, and each reference file names the file and function or the page. A fact marked UNVERIFIED says why. The WLED project keeps its own agent rules for firmware work at https://github.com/wled/WLED/blob/main/AGENTS.md.
