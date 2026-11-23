# Serial Protocols and OTA

The subsystems that only apply to some targets: a versioned serial frame, and an over-the-air update with rollback. The rules that apply to every firmware build live in [SKILL.md](../SKILL.md).

---

### Communication protocol versioning

Every serial frame starts with a magic byte sequence and a one-byte protocol version.

```c
#define FRAME_MAGIC_0    0xAAU
#define FRAME_MAGIC_1    0x55U
#define FRAME_VERSION    0x03U
```

Reject an unknown version gracefully: record the received value and return a NACK byte. Never process a frame whose version you do not recognise, because the field layout behind it is unknown by definition.

Document the complete frame format, every field, its size, the byte order, and the CRC algorithm, in `docs/PROTOCOL.md`, and increment the version field on any breaking change to that structure.

---

### OTA update safety

On a platform that supports it (ESP32, ESP8266, Arduino Nano 33 IoT), use a dual-bank flash scheme: one bank active, one receiving the incoming image.

- Verify the downloaded image's checksum, CRC32 or SHA-256, before committing the update and rebooting.
- Implement automatic rollback: if the new firmware does not mark itself valid within N seconds of its first boot, by calling the bootloader's confirm API after its self-test passes, or if the watchdog resets it first, revert to the previous bank without human involvement. On ESP-IDF that call is `esp_ota_mark_app_valid_cancel_rollback()` with `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE` set.
- Log every attempt, checksum result, and rollback to non-volatile storage (EEPROM or NVS). A device that bricked in the field is only diagnosable from what it wrote down before it did.
