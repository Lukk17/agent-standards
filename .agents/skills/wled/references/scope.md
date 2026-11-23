# Scope

Companion reference for the [wled](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

The skill controls WLED light controllers over their JSON API, WebSocket, serial and Improv, with or without a PIN, read only until the user approves a change, with presets and config backed up first.

- Turning a light on or off, or changing its color, brightness, effect, palette or segments
- Saving, applying or deleting a preset, or building a playlist
- Backing up or restoring a device's presets and configuration
- A device whose settings ask for a PIN, or whose update page says OTA is locked
- Setting up a new board, flashing WLED, or updating its firmware
- Syncing devices, streaming realtime LED data, or connecting WLED to MQTT
- The user says "turn on the WLED strip", "save this as a preset", "back up my WLED", "set up a new WLED board" or "flash WLED"

---

### When not to activate

- Changing the WLED firmware source, building custom firmware or writing a usermod, use `embedded-c-arduino`
- Wiring, power supply sizing and LED strip choice, beyond pointing at https://kno.wled.ge/basics/compatible-hardware/
