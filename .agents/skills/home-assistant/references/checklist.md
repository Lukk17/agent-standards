# Home Assistant Checklist

Run it before calling a Home Assistant change or review done. The rules behind the items are in [SKILL.md](../SKILL.md).

- [ ] Two-space block YAML, lowercase booleans, quoted strings, `triggers`, `actions` and `action` keys.
- [ ] Every trigger, condition, and action references `entity_id` or an area, no `device_id` outside a Zigbee2MQTT button trigger.
- [ ] Purpose-specific or native triggers and conditions used wherever one exists, remaining templates validated first.
- [ ] A helper checked before every template sensor.
- [ ] Waits match the case, each with a `timeout` and a deliberate `continue_on_timeout`.
- [ ] Every automation declares `mode` on purpose and has an `id`.
- [ ] No token, key, or password outside `secrets.yaml`, and `secrets.yaml` is gitignored.
- [ ] Each assistant reaches only the tools and entities it needs, no lock, garage door, or alarm panel.
- [ ] Entity IDs follow `domain.location_device_property`, and a rename left no old ID behind.
- [ ] Logic used in more than two automations is a script or a blueprint.
- [ ] Automation trace inspected after the change, conditions exercised rather than skipped.
- [ ] Nothing under `.storage/` edited by hand.
- [ ] Definitions read before editing, a backup before an irreversible step, and a yes before any restore, backup deletion or upgrade.
- [ ] An integration change passes the integration reference: thin layer, config flow errors, symmetric entity setup, tests through Home Assistant.
