---
name: home-assistant
description: 'Home Assistant YAML, automations, dashboards, renames, backups, custom integrations. Use when the user says "write a motion light automation" or "rename these entities". Not for its container, use `docker-patterns`.'
metadata:
  version: "1.1.0"
---

# Home Assistant Standards

How a Home Assistant configuration, and an integration written for it, stays reviewable and survives a device being re-paired, a rename, an upgrade, or a restore. Written for Home Assistant Core on its monthly release train and YAML 1.2.

---

### When not to activate

- Designing the network, reverse proxy, or container the instance runs in, use `docker-patterns`.
- General Python style and pytest habits outside the Home Assistant rules, use `python-patterns`.
- Driving one Samsung TV or WLED controller through its own interface, use `samsung-tv` or `wled`.

---

### Rules

1. Two-space indentation, block style, lowercase `true` and `false` as the only booleans. Quote strings, leave null implicit.
2. Write these automation keys: `triggers:` with `trigger:`, `conditions:`, `actions:` with `action:`, entities in `target:` and settings in `data:`.
3. Every trigger, condition and action targets `entity_id` or an area, never `device_id`, which is regenerated on a re-pair. The one exception is the discovered device trigger of a Zigbee2MQTT button.
4. Never edit `.storage/` by hand. Create automations, scripts, scenes and helpers through the config API, and edit YAML-only integrations the way the operations reference gives.
5. Native first: a purpose-specific trigger or condition, then a generic native one, then a template. A helper before a template sensor, and Jinja used in several places becomes one macro.
6. Use `wait_for_trigger` for a change and `wait_template` for a state that may already hold, always with a `timeout`.
7. Declare `mode` on purpose: `restart` for a motion timer. The default `single` drops retriggers.
8. Every token, key and password lives in `secrets.yaml` behind `!secret`, gitignored before the first token goes in, and long-lived tokens are rotated on a schedule.
9. The exposed entity list limits only the Device control tools, and a server that holds a token has every right of its user. Keep locks, garage doors and alarm panels out of every assistant's reach.
10. Name entities `domain.location_device_property`, lowercase with underscores, unabbreviated, grouped by area. Before a rename, search every consumer, and after it, find no old ID left.
11. Read an object's definition before editing it, so writing it back is the undo. Take a manual full backup before anything that cannot be undone that way. Restoring a backup, deleting one, and upgrading Core or the OS each wait for the owner's yes every time.
12. Read the instance version before using a feature tied to a release, and check and link its documentation page. Mark a claim you could not check as unverified.
13. An integration stays a thin layer over a PyPI library, has no user-set polling interval, and is tested through Home Assistant rather than its internals.

---

### Reference files

| Open this | For |
|---|---|
| [configuration-examples.md](references/configuration-examples.md) | The reasoning and pass and fail YAML for the core rules, and MCP access |
| [automations-and-helpers.md](references/automations-and-helpers.md) | Triggers, restarts and `unavailable`, buttons, helpers, macros, scenes, blueprints, device actions |
| [dashboards.md](references/dashboards.md) | Sections views, cards, strategy dashboards, and checking a dashboard after a rename |
| [renames-and-refactoring.md](references/renames-and-refactoring.md) | The consumer search before a rename, where entity IDs hide, display names, swapping helpers or waits |
| [operations.md](references/operations.md) | Backups, recovery, what needs a yes, HACS, YAML-only integrations, notifications, tests, upgrades |
| [integration-development.md](references/integration-development.md) | An integration in Python: design, config flow, entities, tests, diagnostics, repairs |
| [conventions.md](references/conventions.md) | How far to trust a VERIFIED, INFERRED or UNVERIFIED mark |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job |
| [checklist.md](references/checklist.md) | Before calling a change or a review done |
