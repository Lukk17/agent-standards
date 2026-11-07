# Controlling the TV from Home Assistant

Read this before writing a script or an automation that launches an app, changes a channel or sends a key. The rules live in [SKILL.md](../SKILL.md), and the general YAML style lives in the `home-assistant` skill. Facts marked VERIFIED were read in the Home Assistant core source, `homeassistant/components/samsungtv/media_player.py` at https://github.com/home-assistant/core/blob/dev/homeassistant/components/samsungtv/media_player.py, or on https://www.home-assistant.io/integrations/samsungtv/, or measured on a 2024 QN85D in the Polish region on 2026-11-06 with Home Assistant 2026.10.4.

More sources, read on 2026-11-07: the core source at tag 2026.10.4, `homeassistant/components/samsungtv/bridge.py` and `homeassistant/components/rest_command/__init__.py` under https://github.com/home-assistant/core/tree/2026.10.4/homeassistant/components, `samsungtvws/remote.py` of `samsungtvws` 3.0.6, the version the integration's `manifest.json` pins, at https://github.com/xchwarze/samsung-tv-ws-api/blob/v3.0.6/samsungtvws/remote.py, the RESTful Command page at https://www.home-assistant.io/integrations/rest_command/, the Stop building block at https://www.home-assistant.io/building-blocks/stop/ and the Scripts page at https://www.home-assistant.io/integrations/script/.

---

### Two media players for one TV

Many Samsung TVs also appear in Home Assistant's Google Cast integration, so one TV can have two `media_player` entities:

| Entity | Integration | Use it for |
|---|---|---|
| `<tv-entity>` | `samsungtv` | channels, keys, power, volume. Apps launch through the TV's REST API, see [Launch an app](#launch-an-app) |
| `<cast-entity>` | `cast` | Home Assistant Cast and casting media, see [cast-and-ambient.md](cast-and-ambient.md) |

Read the integration of an entity in Settings, Devices and services, or from its attributes, before using it. Write the real entity IDs into the owner's notes.

---

### Launch an app

Send `POST` to `http://<tv-ip>:8001/api/v2/applications/<app-id>` with no body and no login. The TV answers HTTP `200` and opens the app. VERIFIED with Disney+ and Netflix. How to read `running` and `visible` after a launch, and the one app that may stay in the background, is in [tv-rest-api.md](tv-rest-api.md#one-app).

In Home Assistant the `POST` is a `rest_command`, which is set up in YAML in `configuration.yaml`:

```yaml
rest_command:
  tv_launch_app:
    url: "http://<tv-ip>:8001/api/v2/applications/{{ app_id }}"
    method: post
    timeout: 5
```

The `url` takes a template, `method` defaults to `get` and `timeout` to 10 seconds. VERIFIED in `rest_command/__init__.py`. Load it with a restart or the `rest_command.reload` action, which is a change in Home Assistant and needs the owner's yes.

One shared script calls it and checks the answer. The RESTful Command page: "REST commands provide an action response in a dictionary containing `status` (containing the HTTP response code)", read through `response_variable`. VERIFIED. A status of `400` or more only logs a warning, while a timeout or a connection error raises an error. VERIFIED in the source. So the script checks the status itself, and `stop` with `error: true` marks the run as failed, as the Stop page says: "If `true`, the run is marked as failed." VERIFIED.

```yaml
tv_launch_app:
  alias: "Launch an app on the TV"
  mode: queued
  fields:
    app_id:
      name: App ID
      required: true
      selector:
        text:
  sequence:
    - action: rest_command.tv_launch_app
      data:
        app_id: "{{ app_id }}"
      response_variable: launch
    - if:
        - condition: template
          value_template: "{{ launch['status'] != 200 }}"
      then:
        - stop: "The TV did not accept the app launch"
          error: true
```

A script that opens one app, for a dashboard button or a voice phrase, calls the shared one directly. Quote the ID so YAML keeps it a string, and confirm it first, see [app-ids.md](app-ids.md).

```yaml
alias: "<app-name> on TV"
mode: single
sequence:
  - action: script.tv_launch_app
    data:
      app_id: "<app-id>"
```

A direct call waits for the shared script, and its error stops the caller too. INFERRED, high confidence, from the Scripts page, which says of starting it with `script.turn_on` instead: "This way, the first script also isn't stopped if the second one fails".

When the TV may be off, turn it on first and wait for the entity to be `on` with a `wait_for_trigger` and a `timeout`, as the `home-assistant` skill describes. A `KEY_POWER` woke a QN85D from standby within 5 seconds, VERIFIED, see [power-on.md](power-on.md). Whether a launch `POST` sent to a TV in standby wakes it or is lost, and how long after waking the TV accepts a launch, is UNVERIFIED.

#### Why not play_media

`media_player.play_media` with `media_content_type: app` on the `samsungtv` entity does not open apps on a QN85D. The applications `GET` then shows `running` `false`, and the app stays closed. VERIFIED, measured with Home Assistant 2026.10.4.

The integration sends only a websocket launch of the `DEEP_LINK` type. `async_play_media` hands an `app` to `async_launch_app` in `bridge.py`, which sends `ChannelEmitCommand.launch_app(app_id)`, and in `samsungtvws` 3.0.6 that is `launch_app(app_id, app_type: str = "DEEP_LINK", meta_tag: str = "")`, the `ed.apps.launch` event. VERIFIED in the source. `async_play_media` accepts only `app` and `channel`, and anything else logs "Unsupported media type". A URL is not supported. VERIFIED in the source. Whether the websocket launch works on other models is UNVERIFIED.

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

`KEY_POWER` is a toggle: it wakes a QN85D from standby and turns an on TV off. VERIFIED. Send it to turn on only after the TV reported `PowerState` `standby`, see [power-on.md](power-on.md#the-automation).

---

### Turn off

`media_player.turn_off` on the `samsungtv` entity sends `KEY_POWER` over the websocket, held for 3 seconds when `FrameTVSupport` is `true`. VERIFIED in `_async_send_power_off` in `homeassistant/components/samsungtv/bridge.py`. Turning on is different, see [power-on.md](power-on.md).
