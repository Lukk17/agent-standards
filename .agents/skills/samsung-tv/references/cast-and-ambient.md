# Casting a dashboard, and Ambient Mode

Read this before showing a Home Assistant dashboard on the TV, or before promising custom content in Ambient Mode. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on a 2024 QN85D in the Polish region or read in the page or source named.

Sources: the Google Cast integration at https://www.home-assistant.io/integrations/cast/, and the `samsungtvws` art module `samsungtvws/art/art.py` at https://github.com/xchwarze/samsung-tv-ws-api.

---

### Home Assistant Cast

`cast.show_lovelace_view` shows one dashboard view on a Cast device. It runs on the Cast entity, never on the `samsungtv` one, see [home-assistant-control.md](home-assistant-control.md#two-media-players-for-one-tv).

```yaml
action: cast.show_lovelace_view
data:
  entity_id: <cast-entity>
  dashboard_path: <dashboard-path>
  view_path: <view-path>
```

It needs Home Assistant reachable over `https`. The Cast page: "Home Assistant Cast requires your Home Assistant installation to be accessible via https://. If you're using Home Assistant Cloud, you don't need to do anything. Otherwise you must make sure that you have configured the external_url in your configuration." VERIFIED. Without it the call fails with "Home Assistant Cast requires your instance to be reachable via HTTPS". VERIFIED by a real call.

Set the external URL in Settings, System, Network, which is a change in Home Assistant and needs the owner's yes. The `https` name has to resolve and carry a certificate the Cast receiver trusts. That a name only the home DNS knows, or a certificate from a private local CA, works here is UNVERIFIED.

Whether Samsung's built-in Cast runs the Home Assistant Cast receiver at all is UNVERIFIED. Test it once with the owner's yes before building on it.

---

### Ambient Mode

On a TV that is not a Frame, Ambient Mode takes no custom content. Samsung's 2024 guide lists My Album through SmartThings, weather and time only. VERIFIED.

The art API in `samsungtvws`, which uploads pictures, first checks `FrameTVSupport` in the device info and works only when it is `true`. VERIFIED in `art.py`. Read the field, see [tv-rest-api.md](tv-rest-api.md).

No Home Assistant project drives Ambient Mode. VERIFIED. For a dashboard on the screen, use Home Assistant Cast above instead.
