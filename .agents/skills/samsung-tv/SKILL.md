---
name: samsung-tv
description: 'Controls a Samsung Tizen smart TV from 2016 on through Home Assistant, with read-only checks against its local REST API: launching apps with a Home Assistant REST command, confirming app IDs, turning it on with a guarded power key, voice assistant scripts and casting a dashboard. Use when the user says "open Netflix on the TV", "find the Disney+ app ID", "the TV does not turn on from Home Assistant" or "show a dashboard on the TV". Not for Home Assistant YAML style in general, use `home-assistant`.'
---

# Samsung TV

How an agent drives a Samsung Tizen TV from Home Assistant and checks it directly without changing anything on it. The TV answers a REST API on port 8001 with no login, which is enough to read its state and to confirm whether an app is installed. Every command that changes something goes through Home Assistant, and every change there is asked of the owner first: an app launch through a `rest_command` that posts to port 8001, and a key or power through the `samsungtv` integration, which holds the token for the secure websocket on port 8002.

Written for Tizen TVs from 2016 on that use the websocket API, and Home Assistant 2026.10 and newer, where the `samsungtv` integration no longer sends Wake on LAN itself. A fact marked VERIFIED was measured on a 2024 QN85D in the Polish region, the launch and power facts on 2026-11-06 with Home Assistant 2026.10.4, or read in the source or vendor page that the reference file names. INFERRED carries a confidence and a reason. Everything else is UNVERIFIED and stays marked until it is measured.

| You are about to | Open |
|---|---|
| Read the TV's device info, network type, MAC, Frame support or power state from port 8001, or what the launch `POST` answers | [tv-rest-api.md](references/tv-rest-api.md) |
| Find, confirm or choose an app ID, or explain why Home Assistant lists no apps | [app-ids.md](references/app-ids.md) |
| Launch an app, change a channel or send a remote key from Home Assistant, explain why `play_media` opens no app, or tell the two media players apart | [home-assistant-control.md](references/home-assistant-control.md) |
| Turn the TV on from Home Assistant, explain why the magic packet does not wake it, or why the entity has no turn on | [power-on.md](references/power-on.md) |
| Cast a Home Assistant dashboard to the TV, or put custom content in Ambient Mode | [cast-and-ambient.md](references/cast-and-ambient.md) |
| Write the script a voice phrase runs to open a TV app, or give it several phrases on Alexa, Google Assistant or Assist | [voice-assistants.md](references/voice-assistants.md) |

---

### Facts about one setup

The TV's address, its MAC address, its entity IDs, the Home Assistant address and the token of a real setup belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md`, never in this skill and never in a shared repository. Every example uses placeholders in angle brackets: `<tv-ip>`, `<tv-mac>`, `<tv-entity>` for the `samsungtv` media player, `<tv-remote-entity>` for its remote, `<cast-entity>` for the Google Cast one, `<app-id>`, `<dashboard-path>`, `<view-path>`.

---

### When to activate

- Launching an app on the TV from Home Assistant, a script or an automation
- Finding or confirming the app ID of Netflix, YouTube, Disney+, Spotify or any other TV app
- Turning the TV on or off from Home Assistant, or a TV entity that offers no turn on
- Writing a voice assistant script that opens a TV app
- Casting a Home Assistant dashboard view to the TV
- Reading the TV's network type, MAC address or Frame support without touching its settings
- The user says "which Netflix ID works on my TV", "the app script runs but nothing opens", "Wake on LAN stopped working after the update" or "can Ambient Mode show my dashboard"

---

### When not to activate

- Home Assistant YAML style, automation modes, secrets and backups in general, use `home-assistant`
- The Docker VM, its Compose stack and its services, use `homelab-services`
- The router, its DHCP leases and its Wi-Fi, use `asus-router`
- SmartThings appliances such as a washer or a fridge, which this skill does not cover
- Judging whether the TV's open ports or the token are acceptable, use the `security-auditor` agent

---

### Hard rules

1. The agent only reads the TV directly: `GET` on `http://<tv-ip>:8001/api/v2/` and `http://<tv-ip>:8001/api/v2/applications/<app-id>`. It never opens the websocket, sends a key, launches an app or sends any other method to the TV itself. The launch `POST` is sent by Home Assistant, never by the agent.
2. Ask before every change in Home Assistant: an automation, a script, an integration option, a restart, and every service call that acts on the TV. Say what changes, the worst case and how to undo it, then wait for a yes. One yes covers one change. Reading states and the TV's REST API is free.
3. Confirm every app ID on the TV the script is for with the applications call before writing it into a script. A `404` means that ID is not installed there. IDs differ by region and model.
4. Launch an app with a Home Assistant `rest_command` that sends `POST` to `http://<tv-ip>:8001/api/v2/applications/<app-id>`, called from one shared script that stops with an error when the status is not `200`. Never use `media_player.play_media` with `media_content_type: app` for it, which does not open apps on a QN85D, and never the Cast entity.
5. Turning on needs an automation on the `samsungtv.turn_on` trigger, because the integration sends no magic packet itself in Home Assistant 2026.10 and newer. The magic packet did not wake a QN85D from standby, a `KEY_POWER` did. `KEY_POWER` is a toggle, so the automation sends it only after `GET http://<tv-ip>:8001/api/v2/` reported `PowerState` `standby`.
6. Never print the websocket token from the config entry, and never copy it out of Home Assistant.
7. A claim stays UNVERIFIED until it was measured on a real TV, and the mark goes with it into every note and script comment.

---

### Related skills

- `home-assistant` owns automation and script style, modes, secrets and backups
- `homelab-services` owns the VM and the services that run beside Home Assistant
- `asus-router` owns the router that hands the TV its address
- The `home-assistant-engineer` agent owns building and changing the Home Assistant configuration
- The `security-auditor` agent owns judging exposed ports and tokens

---

### Checklist

- [ ] Every app ID in a script answered the applications call with its `name` on the TV the script is for
- [ ] Apps launch through the shared script and its `rest_command` `POST`, which stops with an error on a status other than `200`, never through `media_player.play_media`
- [ ] An automation on `samsungtv.turn_on` sends `KEY_POWER` only when `PowerState` reads `standby`, and the entity shows turn on
- [ ] Power On with Mobile is on in the TV's Expert Settings, and the network type was read before trusting Wake on LAN
- [ ] Home Assistant Cast is used only with an `https` external URL set
- [ ] No address, MAC, entity ID or token of a real setup in the skill or a shared repository
- [ ] Every change in Home Assistant had its own yes after the worst case and the undo were stated
- [ ] Every UNVERIFIED fact used is still marked UNVERIFIED in the result
