---
name: home-assistant
description: 'Home Assistant standards for YAML style, entity_id references, native conditions, event-driven automations, automation modes, secrets, MCP exposure limits and backups. Use when the user says "write an automation for this motion sensor", "my automation retriggers and cancels itself" or "move these tokens into secrets.yaml". Not for a custom integration in Python, use `python-patterns`.'
---

# Home Assistant Standards

How a Home Assistant configuration stays reviewable and survives a device being re-paired, an upgrade, or a restore.
Most breakage here is not a bug, it is a reference that pointed at something transient or a condition that only
failed at runtime.

Written for Home Assistant Core on its monthly release train, and YAML 1.2 parsing rules.

---

### When to activate

- Writing or reviewing an automation, script, or blueprint.
- Debugging an automation that fires twice, cancels itself, or silently does nothing.
- Moving tokens and passwords into `secrets.yaml`.
- Deciding which entities an assistant or MCP client may see.
- Naming entities, or cleaning up entity IDs after a device rename.
- Planning backups, integration cleanup, or a core upgrade.
- The user says "expose these entities to the assistant" or "why did my template condition fail silently".

---

### When not to activate

- Writing a custom integration in Python against the Home Assistant developer API, use `python-patterns`.
- Writing a standalone script that talks to the REST API from outside, use `bash` or `powershell`.
- Designing the network, reverse proxy, or container the instance runs in, use `docker-patterns`.
- Building an external service that consumes Home Assistant events, use `backend-patterns`.
- Reviewing the security posture of an internet-exposed instance, use the `security-auditor` agent.

---

### Reference files

| Open this | For |
|---|---|
| [references/configuration-examples.md](references/configuration-examples.md) | The reasoning and pass and fail YAML for every rule below, with the vendor documentation links |
| [references/operations.md](references/operations.md) | Choosing between a blueprint, an automation and a script, tracing and testing a change, backups and restores, HACS hygiene, the notification priority taxonomy, and upgrade discipline |

---

### Rules

1. Two-space indentation, block style, lowercase `true` and `false`, never `yes`, `no`, `on` or `off` as booleans under YAML 1.2. Quote strings, leave null implicit, and prefer a UI-managed helper over hand-written `template:` YAML.
2. Every trigger, condition and action targets `entity_id`, never `device_id`, which is regenerated on a re-pair.
3. Never edit `.storage/` by hand. Go through the REST or WebSocket API.
4. Use a native condition wherever one exists. A template condition fails silently at runtime, so use one only when nothing native fits, validated in Developer Tools first.
5. Wait with `wait_for_trigger`, not `wait_template`, always with a `timeout` and a deliberate `continue_on_timeout`.
6. Declare `mode` on purpose: `restart` for a motion timer, `queued` when every trigger must run in order, `parallel` only when runs never touch the same entity. The default `single` drops retriggers.
7. Every token, key and password lives in `secrets.yaml` behind `!secret`, gitignored before the first token goes in. Rotate long-lived tokens used by MCP clients and external integrations at least every 90 days.
8. Expose to an assistant or MCP client only what it needs, and never a lock, garage door, alarm panel or anything else with a physical security consequence. Secure `/api/mcp` with a scoped long-lived token, or OAuth where supported, and add a `stdio` proxy only for a client that supports nothing else.
9. Name entities `domain.location_device_property`, lowercase with underscores, unabbreviated, and group them with the area registry.

---

### Related skills

- `python-patterns` for building and testing a custom integration in Python.
- The `security-auditor` agent before exposing the instance, its API, or a new entity set to anything outside the LAN.
- `docker-patterns` for the container and network the instance runs in.
- `bash` and `powershell` for external scripts driving the REST API.
- `observability-and-logging` for anything long-running that consumes the event stream.

---

### Checklist

- [ ] Two-space block YAML, lowercase booleans, quoted strings.
- [ ] Every trigger, condition, and action references `entity_id`, no `device_id`.
- [ ] Native conditions used wherever one exists, remaining templates validated in Developer Tools.
- [ ] Waits use `wait_for_trigger` with an explicit `timeout` and a deliberate `continue_on_timeout`.
- [ ] Every automation declares `mode` on purpose, motion timers use `restart`.
- [ ] No token, key, or password outside `secrets.yaml`, and `secrets.yaml` is gitignored.
- [ ] No lock, garage door, or alarm panel exposed to an assistant or MCP client.
- [ ] Entity IDs follow `domain.location_device_property` and are unabbreviated.
- [ ] Logic used in more than two automations is a script or a blueprint.
- [ ] Automation Trace inspected after the change, conditions exercised rather than skipped.
- [ ] Nothing under `.storage/` edited by hand.
