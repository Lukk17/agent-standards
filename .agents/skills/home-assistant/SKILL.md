---
name: home-assistant
description: 'Home Assistant standards for YAML, automations, scripts, helpers, templates, dashboards, entity names and renames, backups, upgrades, MCP access and custom integrations in Python. Use when the user says "write a motion light automation", "rename these entities", "restore the backup" or "review my custom integration". Not for the container or network the instance runs in, use `docker-patterns`.'
---

# Home Assistant Standards

How a Home Assistant configuration, and an integration written for it, stays reviewable and survives a device being re-paired, a rename, an upgrade, or a restore. Most breakage here is not a bug, it is a reference that pointed at something transient, a condition that only failed at runtime, or a change made with no way back.

Written for Home Assistant Core on its monthly release train and YAML 1.2. Reference facts are marked VERIFIED with the source read, INFERRED with a confidence, or UNVERIFIED.

---

### When to activate

- Writing or reviewing an automation, script, scene, blueprint, helper or template.
- Debugging an automation that fires twice, cancels itself, or silently does nothing.
- Building or changing a dashboard.
- Renaming entities or devices, or replacing a template sensor with a helper.
- Moving tokens and passwords into `secrets.yaml`, or deciding what an assistant or MCP client may reach.
- Planning backups, a restore, integration cleanup, or a Core or OS upgrade.
- Building, testing or reviewing an integration in Python, in Core or under `custom_components/`.
- The user says "expose these entities to the assistant" or "why did my condition fail silently".

---

### When not to activate

- General Python style and pytest habits outside the Home Assistant rules, use `python-patterns`.
- Writing a standalone script that talks to the REST API from outside, use `bash` or `powershell`.
- Designing the network, reverse proxy, or container the instance runs in, use `docker-patterns`.
- Driving one Samsung TV or WLED controller through its own interface, use `samsung-tv` or `wled`.
- Building an external service that consumes Home Assistant events, use `backend-patterns`.
- Reviewing the security posture of an internet-exposed instance, use the `security-auditor` agent.

---

### Reference files

| Open this | For |
|---|---|
| [references/configuration-examples.md](references/configuration-examples.md) | The reasoning and pass and fail YAML for the core rules, the automation keys, and MCP access |
| [references/automations-and-helpers.md](references/automations-and-helpers.md) | Purpose-specific triggers, restarts and `unavailable`, buttons, helpers before templates, macros, scenes, blueprints, device actions |
| [references/dashboards.md](references/dashboards.md) | Sections views, cards, strategy dashboards, and checking a dashboard after a rename |
| [references/renames-and-refactoring.md](references/renames-and-refactoring.md) | The consumer search before a rename, where entity IDs hide, display names, swapping helpers or waits |
| [references/operations.md](references/operations.md) | Backups, recovery, what needs a yes, HACS, YAML-only integrations, notifications, tests, upgrades |
| [references/integration-development.md](references/integration-development.md) | An integration in Python: design, config flow, entities, actions, quality scale, tests, diagnostics, repairs |

---

### Rules

1. Two-space indentation, block style, lowercase `true` and `false`, never `yes`, `no`, `on`, `off`, `True` or `False` as booleans. Quote strings, leave null implicit.
2. Write these automation keys: `triggers:` with `trigger:`, `conditions:`, `actions:` with `action:`, entities in `target:` and settings in `data:`.
3. Every trigger, condition and action targets `entity_id` or an area, never `device_id`, which is regenerated on a re-pair. The one exception is the discovered device trigger of a Zigbee2MQTT button.
4. Never edit `.storage/` by hand. Create automations, scripts, scenes and helpers through the config API, and edit YAML-only integrations with a copy kept, `check_config`, and the domain reload.
5. Native first: a purpose-specific trigger or condition, then a generic native one, then a template. A helper before a template sensor, a Template helper before `template:` YAML, and Jinja used in several places becomes one macro.
6. Use `wait_for_trigger` for a change and `wait_template` for a state that may already hold, always with a `timeout`, a deliberate `continue_on_timeout`, and a check of `wait.completed`.
7. Declare `mode` on purpose: `restart` for a motion timer, `queued` when every trigger must run in order, `parallel` only when runs never touch the same entity. The default `single` drops retriggers.
8. Every token, key and password lives in `secrets.yaml` behind `!secret`, gitignored before the first token goes in. Rotate long-lived tokens used by MCP clients and external integrations at least every 90 days.
9. The exposed entity list limits only the Device control tools. Point a limited assistant at `/api/mcp/assist` or restrict the main URL, treat a token-holding server such as ha-mcp as having every right of its user, and keep locks, garage doors and alarm panels out of reach.
10. Name entities `domain.location_device_property`, lowercase with underscores, unabbreviated, grouped by area. Before a rename, search every consumer, and after it, find no old ID left.
11. Read an object's definition before editing it, so writing it back is the undo. Take a manual full backup before anything that cannot be undone that way. Restoring a backup, deleting one, and upgrading Core or the OS each wait for the owner's yes every time.
12. Read the instance version before using a feature tied to a release, check the documentation page for it, and link it. Mark a claim you could not check as unverified.
13. An integration stays a thin layer over a PyPI library, has no user-set polling interval, and is tested through Home Assistant rather than its internals, as the integration reference describes.

---

### Related skills

- `python-patterns` for Python idioms, typing and pytest in an integration.
- `tdd-workflow` for the test-first loop when building an integration.
- The `security-auditor` agent before exposing the instance, its API, or a new entity set to anything outside the LAN.
- `docker-patterns` for the container and network the instance runs in.
- `bash` and `powershell` for external scripts driving the REST API.
- `observability-and-logging` for anything long-running that consumes the event stream.

---

### Checklist

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
