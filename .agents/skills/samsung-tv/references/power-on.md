# Turning the TV on

Read this before wiring turn on, or when the TV entity offers no turn on. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were read in the source, the pull request or the vendor page named, or measured on a 2024 QN85D in the Polish region.

Sources: Home Assistant core pull request 182771 at https://github.com/home-assistant/core/pull/182771, `homeassistant/components/samsungtv/media_player.py` at https://github.com/home-assistant/core/blob/dev/homeassistant/components/samsungtv/media_player.py, the Wake on LAN integration at https://www.home-assistant.io/integrations/wake_on_lan/, and Samsung's page at https://www.samsung.com/au/support/tv-audio-video/power-on-tv-smartthings-app/.

---

### What changed in Home Assistant 2026.10

Pull request 182771, "Cleanup deprecated wake-on-lan for SamsungTV", merged for Home Assistant 2026.10, removed the magic packet the integration used to send by itself. VERIFIED.

Now `turn_on` only fires the `samsungtv.turn_on` device trigger. The entity offers turn on only while an automation uses that trigger. The source: "`turn_on` triggers are not yet registered during initialisation, so this property needs to be dynamic", and it adds `MediaPlayerEntityFeature.TURN_ON` only when a turn on action exists. VERIFIED.

The `samsungtv` documentation page still says "If the integration knows the MAC address of the TV from discovery, it will attempt to wake it using wake on LAN when calling turn on." That sentence is outdated for 2026.10 and newer. Trust the source.

---

### The automation

The Wake on LAN integration has to be set up first. Then the automation, from the device page (Device is requested to turn on) or in YAML:

```yaml
alias: "TV turn on with Wake on LAN"
mode: single
triggers:
  - trigger: samsungtv.turn_on
    entity_id: <tv-entity>
actions:
  - action: wake_on_lan.send_magic_packet
    data:
      mac: "<tv-mac>"
```

Read `<tv-mac>` from `wifiMac` in the device info, see [tv-rest-api.md](tv-rest-api.md). After the automation is saved, the entity shows turn on again.

---

### The TV settings

Samsung's page for 2022 to 2026 TVs names the setting: Settings > All Settings > Connections > Network > Expert Settings > Power On with Mobile. VERIFIED. IP Remote sits next to it. Both were on during the measurements.

---

### Wired or wireless

Read `networkType` before relying on the magic packet. Wake on LAN is reliable on Ethernet and uncertain on Wi-Fi, UNVERIFIED, from community reports only. On Wi-Fi, test it once with the owner's yes while the TV has been in standby for a while, and record the result.

---

### Cast does not wake it

The Cast entity's `turn_on` only starts an app on the Cast receiver: the source says "The only way we can turn the Chromecast is on is by launching an app" (`homeassistant/components/cast/media_player.py`). VERIFIED. That this does not wake the TV from standby is UNVERIFIED. Use the `samsungtv` entity for power.
