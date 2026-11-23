# WLED Checklist

Run it before calling work on a WLED device done. The rules behind the items are in [SKILL.md](../SKILL.md).

- [ ] The device was confirmed as WLED with `GET /json/info`, and `ver` and `release` were noted
- [ ] The PIN state was checked with a `GET` of `/settings/sec`, not with a `POST`
- [ ] `/presets.json` and `/cfg.json` were saved and parsed as valid JSON before the first write
- [ ] Every write had its own yes after the change, the worst case and the undo were stated
- [ ] No partial `/settings/*` form was posted
- [ ] `GET /json/cfg` was read before and after each config change, and only the intended keys differ
- [ ] The OTA lock is back in the state it had before the work
- [ ] Firmware, bootloader, PIN, factory reset and Wi-Fi changes happened only when the user named them
- [ ] No PIN, OTA password or Wi-Fi password was guessed or printed, and no file holding one outlived its call
- [ ] Every UNVERIFIED fact relied on was named to the user as unverified
