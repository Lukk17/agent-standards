# Conventions

Companion reference for the [samsung-tv](../SKILL.md) skill. Load it before writing a command or a note that names the TV, an entity or an address, and when judging how far to trust a fact in the topic files.

---

### Facts about one setup

The TV's address, its MAC address, its entity IDs, the Home Assistant address and the token of a real setup belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md`, never in this skill and never in a shared repository. Every example uses placeholders in angle brackets: `<tv-ip>`, `<tv-mac>`, `<tv-entity>` for the `samsungtv` media player, `<tv-remote-entity>` for its remote, `<cast-entity>` for the Google Cast one, `<app-id>`, `<dashboard-path>`, `<view-path>`.

---

### Verification

Written for Tizen TVs from 2016 on that use the websocket API, and Home Assistant 2026.10 and newer, where the `samsungtv` integration no longer sends Wake on LAN itself. A fact marked VERIFIED was measured on a 2024 QN85D in the Polish region, the launch and power facts on 2026-11-06 with Home Assistant 2026.10.4, or read in the source or vendor page that the reference file names. INFERRED carries a confidence and a reason. Everything else is UNVERIFIED and stays marked until it is measured.
