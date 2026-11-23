# Conventions

Companion reference for the [syncthing](../SKILL.md) skill. Load it before writing a command or a note that names a device, a folder or an address, and when judging how far to trust a command in the topic files.

---

### Facts about one setup

Device IDs, folder IDs, host names and LAN addresses of a real setup belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md`, never in this skill and never in a shared repository. Discover them with the read commands in the topic files. Every example here uses placeholders in angle brackets: `<device-id>`, `<folder-id>`, `<folder-label>`, `<peer-lan-ip>`.

---

### Verification

Written for Syncthing 2. Commands marked VERIFIED were executed in throwaway containers built from the `syncthing/syncthing` and `lscr.io/linuxserver/syncthing` images on an isolated Docker network. Every other command, every Windows and every macOS command included, is UNVERIFIED.
