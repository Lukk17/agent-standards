# Turning the TV on

Read this before wiring turn on, when the TV entity offers no turn on, or when the magic packet does not wake the TV. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were read in the source, the pull request or the vendor page named, or measured on a 2024 QN85D in the Polish region, the wake tests on 2026-11-06 with Home Assistant 2026.10.4.

Sources: Home Assistant core pull request 182771 at https://github.com/home-assistant/core/pull/182771, `homeassistant/components/samsungtv/media_player.py` at https://github.com/home-assistant/core/blob/dev/homeassistant/components/samsungtv/media_player.py, the Wake on LAN integration at https://www.home-assistant.io/integrations/wake_on_lan/, the RESTful Command page at https://www.home-assistant.io/integrations/rest_command/, and Samsung's page at https://www.samsung.com/au/support/tv-audio-video/power-on-tv-smartthings-app/.

---

### What changed in Home Assistant 2026.10

Pull request 182771, "Cleanup deprecated wake-on-lan for SamsungTV", merged for Home Assistant 2026.10, removed the magic packet the integration used to send by itself. VERIFIED.

Now `turn_on` only fires the `samsungtv.turn_on` device trigger. The entity offers turn on only while an automation uses that trigger. The source: "`turn_on` triggers are not yet registered during initialisation, so this property needs to be dynamic", and it adds `MediaPlayerEntityFeature.TURN_ON` only when a turn on action exists. VERIFIED.

The `samsungtv` documentation page still says "If the integration knows the MAC address of the TV from discovery, it will attempt to wake it using wake on LAN when calling turn on." That sentence is outdated for 2026.10 and newer. Trust the source.

---

### What wakes the TV

With the TV in `PowerState` `standby`, the screen off and the network still up, two broadcast magic packets and one unicast packet did not wake it within 30 seconds. One `KEY_POWER` sent with `remote.send_command` on the `samsungtv` remote entity woke it within 5 seconds. VERIFIED, both measured on a QN85D.

`KEY_POWER` is a toggle, so the same key turns an on TV off. VERIFIED. Read `PowerState` first, see [tv-rest-api.md](tv-rest-api.md#device-info), and send the key only on `standby`.

The key cannot reach a TV that does not answer at all, fully off with its network down, because the websocket needs the network. INFERRED, high confidence. Whether the magic packet wakes a TV from such a deeper sleep is UNVERIFIED.

---

### The automation

The Wake on LAN integration has to be set up first. Then a `rest_command` that reads the device info, set up in YAML in `configuration.yaml` like the launch command in [home-assistant-control.md](home-assistant-control.md#launch-an-app):

```yaml
rest_command:
  tv_device_info:
    url: "http://<tv-ip>:8001/api/v2/"
    timeout: 5
```

Then the automation, from the device page (Device is requested to turn on) or in YAML. It sends the magic packet for the deeper sleep case, then the key only when the TV reports `standby`:

```yaml
alias: "TV turn on"
mode: single
triggers:
  - trigger: samsungtv.turn_on
    entity_id: <tv-entity>
actions:
  - action: wake_on_lan.send_magic_packet
    data:
      mac: "<tv-mac>"
  - action: rest_command.tv_device_info
    response_variable: info
  - variables:
      power_state: >-
        {% set body = info['content'] %}
        {{ (body if body is mapping else body | from_json)['device']['PowerState'] }}
  - if:
      - condition: template
        value_template: "{{ power_state == 'standby' }}"
    then:
      - action: remote.send_command
        target:
          entity_id: <tv-remote-entity>
        data:
          command: KEY_POWER
```

`content` holds the parsed JSON only when the TV sends the `application/json` content type, and text otherwise, VERIFIED in `homeassistant/components/rest_command/__init__.py` at tag 2026.10.4, so the template parses text with `from_json`. Which content type the TV sends is UNVERIFIED. When the TV does not answer, the `rest_command` raises an error, VERIFIED in the same source, so the run stops before the key. The automation as a whole is UNVERIFIED until it was run once with the owner's yes, in standby and with the TV on.

Read `<tv-mac>` from `wifiMac` in the device info, see [tv-rest-api.md](tv-rest-api.md). After the automation is saved, the entity shows turn on again.

---

### The TV settings

Samsung's page for 2022 to 2026 TVs names the setting: Settings > All Settings > Connections > Network > Expert Settings > Power On with Mobile. VERIFIED. IP Remote sits next to it. Both were on during the measurements.

---

### Wired or wireless

Read `networkType` before relying on the magic packet, and record it with every wake result. That Wake on LAN is reliable on Ethernet and uncertain on Wi-Fi is UNVERIFIED, from community reports only, and from standby it did not wake a QN85D at all, see [What wakes the TV](#what-wakes-the-tv). On Wi-Fi, test it once with the owner's yes while the TV has been in standby for a while, and record the result.

---

### Cast does not wake it

The Cast entity's `turn_on` only starts an app on the Cast receiver: the source says "The only way we can turn the Chromecast is on is by launching an app" (`homeassistant/components/cast/media_player.py`). VERIFIED. That this does not wake the TV from standby is UNVERIFIED. Use the `samsungtv` entity for power.
