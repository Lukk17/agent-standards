# Controlling the TV from Home Assistant

Read this before writing a script or an automation that launches an app, changes a channel or sends a key. The rules live in [SKILL.md](../SKILL.md), and the general YAML style lives in the `home-assistant` skill. Facts marked VERIFIED were read in the Home Assistant core source, `homeassistant/components/samsungtv/media_player.py` at https://github.com/home-assistant/core/blob/dev/homeassistant/components/samsungtv/media_player.py, or on https://www.home-assistant.io/integrations/samsungtv/.

---

### Two media players for one TV

Many Samsung TVs also appear in Home Assistant's Google Cast integration, so one TV can have two `media_player` entities:

| Entity | Integration | Use it for |
|---|---|---|
| `<tv-entity>` | `samsungtv` | apps, channels, keys, power, volume |
| `<cast-entity>` | `cast` | Home Assistant Cast and casting media, see [cast-and-ambient.md](cast-and-ambient.md) |

Read the integration of an entity in Settings, Devices and services, or from its attributes, before using it. Write the real entity IDs into the owner's notes.

---

### Launch an app

`async_play_media` accepts two media types: `app`, which sends the app launch over the websocket, and `channel`, which takes a channel number. Anything else logs "Unsupported media type". A URL is not supported. VERIFIED in the source.

```yaml
action: media_player.play_media
target:
  entity_id: <tv-entity>
data:
  media_content_type: app
  media_content_id: "<app-id>"
```

Quote the ID so YAML keeps it a string. Confirm the ID first, see [app-ids.md](app-ids.md). That every confirmed ID also launches through this call is UNVERIFIED per app until it was run once with the owner's yes.

A script that opens one app, for a dashboard button or a voice phrase:

```yaml
alias: "<app-name> on TV"
mode: single
sequence:
  - action: media_player.play_media
    target:
      entity_id: <tv-entity>
    data:
      media_content_type: app
      media_content_id: "<app-id>"
```

When the TV may be off, turn it on first and wait for the entity to be `on` with a `wait_for_trigger` and a `timeout`, as the `home-assistant` skill describes. How long a QN85D takes from the magic packet to accepting a launch is UNVERIFIED.

---

### Change a channel

```yaml
action: media_player.play_media
target:
  entity_id: <tv-entity>
data:
  media_content_type: channel
  media_content_id: "<channel-number>"
```

The source checks that the ID is a positive whole number. VERIFIED.

---

### Send a remote key

`remote.send_command` on the `samsungtv` remote entity sends `KEY_*` codes. The page says "The supported keys vary between TV models." VERIFIED. The community key list is https://github.com/xchwarze/samsung-tv-ws-api/blob/master/COMMANDS.md.

```yaml
action: remote.send_command
target:
  entity_id: <tv-remote-entity>
data:
  command: KEY_HOME
```

`KEY_AMBIENT` is in the key list. Whether it opens Ambient Mode on a 2024 model is UNVERIFIED.

---

### Turn off

`media_player.turn_off` on the `samsungtv` entity sends `KEY_POWER` over the websocket, held for 3 seconds when `FrameTVSupport` is `true`. VERIFIED in `_async_send_power_off` in `homeassistant/components/samsungtv/bridge.py`. Turning on is different, see [power-on.md](power-on.md).
