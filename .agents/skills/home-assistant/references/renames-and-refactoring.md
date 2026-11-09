# Renames and refactoring

Companion reference for the [home-assistant](../SKILL.md) skill. Load it before renaming an entity or a device, replacing a template sensor with a helper, turning a device trigger into an entity trigger, or restructuring an automation that other things call.

The steps follow the `safe-refactoring` reference of the best-practices skill that the ha-mcp server ships, `home-assistant-best-practices` in homeassistant-ai/skills. They are UNVERIFIED against a primary source unless marked VERIFIED, which means read in the Home Assistant documentation source, github.com/home-assistant/home-assistant.io on branch `current`.

---

### The order

1. Scope. Write down what changes: an entity ID, a display name, a sensor type, or how a trigger behaves.
2. Siblings. List every entity of the same device, such as the battery sensor, the update entity and a diagnostic button, and plan their names together. A physical device set up through two config entries shows up as two devices, so search by its name or identifier as well, not only by one device entry.
3. Consumers. Search every place that can hold the old ID before changing anything, and keep the list as the checklist for step 5.
4. Change. Rename, replace or restructure.
5. Update. Work through the checklist.
6. Verify. Search for the old ID again and expect nothing. Search for the new ID and expect every place from the checklist. When a reference cannot be updated, rename the entity back and tell the user which place blocks the change.

When the user does the steps by hand, give them in the same order, with the consumer search first.

---

### Where an entity ID hides

| Place | How to search |
|---|---|
| Automations, scripts, scenes | the config API, or `automations.yaml`, `scripts.yaml`, `scenes.yaml` |
| Dashboards edited in the UI | the Lovelace config through the WebSocket API, see [dashboards.md](dashboards.md). A rename does not update them |
| UI groups | the group config entry, members in `options.entities`. A rename does not update them, so pick the member again in the group's options |
| `min_max` helpers and custom integrations such as Better Thermostat | the `data` and `options` of every config entry. A rename does not update them. Single-source helpers such as `threshold` update themselves |
| Other tools | AppDaemon apps, Node-RED flows, Pyscript and any custom integration |

When an integration keeps the ID in config entry `data` and offers no way to change it after setup, tell the user and take a full backup before the rename, as [operations.md](operations.md) describes.

---

### Display names

The entity ID and the display name are separate fields. Renaming in the UI writes a user override (`name` on the entity, `name_by_user` on the device) and leaves the integration's own value (`original_name`, `name`) underneath. The override wins while it is set, so a later fix from the integration never shows. Rename at the source when the source is wrong, keep the override for names Home Assistant itself owns, and use labels or areas, not names, to mark or group entities.

---

### Replacing a helper or a trigger

1. A new helper has a new entity ID. Point every consumer of the old template sensor at it, and compare the two for units, precision and how each handles `unavailable` before removing the old one.
2. `wait_for_trigger` waits for a change, `wait_template` for a condition. When the state already holds at the start, the template wait continues at once and the trigger wait keeps waiting. VERIFIED, `source/_building_blocks/wait_for_trigger.markdown`: "If the state is already there, the automation or script keeps waiting." Check which one the old behaviour relied on before swapping them.
3. Renaming or splitting an automation changes its entity ID, which breaks any script or automation that calls it with `automation.trigger` or `automation.turn_on`. Search for those callers too.
