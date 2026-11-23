# Scope

Companion reference for the [home-assistant](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

The skill covers YAML, automations, scripts, helpers, templates, dashboards, entity names and renames, backups, upgrades, MCP access and custom integrations in Python.

- Writing or reviewing an automation, script, scene, blueprint, helper or template.
- Debugging an automation that fires twice, cancels itself, or silently does nothing.
- Building or changing a dashboard.
- Renaming entities or devices, or replacing a template sensor with a helper.
- Moving tokens and passwords into `secrets.yaml`, or deciding what an assistant or MCP client may reach.
- Planning backups, a restore, integration cleanup, or a Core or OS upgrade.
- Building, testing or reviewing an integration in Python, in Core or under `custom_components/`.
- The user says "write a motion light automation", "rename these entities", "restore the backup", "review my custom integration", "expose these entities to the assistant" or "why did my condition fail silently".

---

### When not to activate

- General Python style and pytest habits outside the Home Assistant rules, use `python-patterns`.
- Writing a standalone script that talks to the REST API from outside, use `bash` or `powershell`.
- Designing the network, reverse proxy, or container the instance runs in, use `docker-patterns`.
- Driving one Samsung TV or WLED controller through its own interface, use `samsung-tv` or `wled`.
- Building an external service that consumes Home Assistant events, use `backend-patterns`.
- Reviewing the security posture of an internet-exposed instance, use the `security-auditor` agent.

---

### Related skills

- `python-patterns` for Python idioms, typing and pytest in an integration.
- `tdd-workflow` for the test-first loop when building an integration.
- The `security-auditor` agent before exposing the instance, its API, or a new entity set to anything outside the LAN.
- `docker-patterns` for the container and network the instance runs in.
- `bash` and `powershell` for external scripts driving the REST API.
- `observability-and-logging` for anything long-running that consumes the event stream.
