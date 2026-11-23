---
name: samsung-tv
description: 'A Samsung Tizen TV through Home Assistant, read only on its REST API: app launch, power on. Use when the user says "open Netflix on the TV" or "find the Disney+ app ID". Not for Home Assistant YAML, use `home-assistant`.'
metadata:
  version: "1.1.0"
---

# Samsung TV

How an agent drives a Samsung Tizen TV from Home Assistant and checks it directly without changing anything on it. The TV answers a REST API on port 8001 with no login, which is enough to read its state and to confirm whether an app is installed. Every command that changes something goes through Home Assistant, and every change there is asked of the owner first: an app launch through a `rest_command` that posts to port 8001, and a key or power through the `samsungtv` integration, which holds the token for the secure websocket on port 8002.

Written for Tizen TVs from 2016 on that use the websocket API, and Home Assistant 2026.10 and newer. Setup facts belong in the owner's notes, never here, and examples use `<placeholders>`.

---

### When not to activate

- Home Assistant YAML style, automation modes, secrets and backups in general, use `home-assistant`
- The Docker VM, its Compose stack and its services, use `homelab-services`
- The router, its DHCP leases and its Wi-Fi, use `asus-router`

---

### Hard rules

1. The agent only reads the TV directly: `GET` on `http://<tv-ip>:8001/api/v2/` and `http://<tv-ip>:8001/api/v2/applications/<app-id>`. It never opens the websocket, sends a key, launches an app or sends any other method to the TV itself. The launch `POST` is sent by Home Assistant, never by the agent.
2. Ask before every change in Home Assistant: an automation, a script, an integration option, a restart, and every service call that acts on the TV. Say what changes, the worst case and how to undo it, then wait for a yes. One yes covers one change. Reading states and the TV's REST API is free.
3. Confirm every app ID on the TV the script is for with the applications call before writing it into a script. A `404` means that ID is not installed there. IDs differ by region and model.
4. Launch an app with a Home Assistant `rest_command` that sends `POST` to `http://<tv-ip>:8001/api/v2/applications/<app-id>`, called from one shared script that stops with an error when the status is not `200`. Never use `media_player.play_media` with `media_content_type: app` for it, and never the Cast entity.
5. Turning on needs an automation on the `samsungtv.turn_on` trigger, because the integration sends no magic packet itself. `KEY_POWER` is a toggle, so the automation sends it only after `GET http://<tv-ip>:8001/api/v2/` reported `PowerState` `standby`.
6. Never print the websocket token from the config entry, and never copy it out of Home Assistant.
7. A claim stays UNVERIFIED until it was measured on a real TV, and the mark goes with it into every note and script comment.

---

### Reference files

| You are about to | Open |
|---|---|
| Read the TV's device info, network type, MAC, Frame support or power state from port 8001, or what the launch `POST` answers | [tv-rest-api.md](references/tv-rest-api.md) |
| Find, confirm or choose an app ID, or explain why Home Assistant lists no apps | [app-ids.md](references/app-ids.md) |
| Launch an app, change a channel or send a remote key from Home Assistant, explain why `play_media` opens no app, or tell the two media players apart | [home-assistant-control.md](references/home-assistant-control.md) |
| Turn the TV on from Home Assistant, explain why the magic packet does not wake it, or why the entity has no turn on | [power-on.md](references/power-on.md) |
| Cast a Home Assistant dashboard to the TV, or put custom content in Ambient Mode | [cast-and-ambient.md](references/cast-and-ambient.md) |
| Write the script a voice phrase runs to open a TV app, or give it several phrases on Alexa, Google Assistant or Assist | [voice-assistants.md](references/voice-assistants.md) |
| Name the TV, an entity or an address, or judge a VERIFIED mark | [conventions.md](references/conventions.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling the work done | [checklist.md](references/checklist.md) |
