---
name: home-assistant
description: Home Assistant standards for YAML style, entity_id references, native conditions, event-driven automations, automation modes, secrets, MCP exposure limits, and backup discipline. Use when you say "write an automation for this motion sensor", "my automation retriggers and cancels itself", "move these tokens into secrets.yaml", "expose these entities to the assistant", or "why did my template condition fail silently". Not for writing a custom integration in Python, use `python-patterns`.
---

# Home Assistant Standards

How a Home Assistant configuration stays reviewable and survives a device being re-paired, an upgrade, or a restore.
Most breakage here is not a bug, it is a reference that pointed at something transient or a condition that only
failed at runtime.

Baseline: Home Assistant Core current stable on the monthly 2026.x release train, and YAML 1.2 parsing rules.

---

### When to activate

- Writing or reviewing an automation, script, or blueprint.
- Debugging an automation that fires twice, cancels itself, or silently does nothing.
- Moving tokens and passwords into `secrets.yaml`.
- Deciding which entities an assistant or MCP client may see.
- Naming entities, or cleaning up entity IDs after a device rename.
- Planning backups, integration cleanup, or a core upgrade.

---

### When not to activate

- Writing a custom integration in Python against the Home Assistant developer API, use `python-patterns`.
- Writing a standalone script that talks to the REST API from outside, use `bash` or `powershell`.
- Designing the network, reverse proxy, or container the instance runs in, use `docker-patterns`.
- Building an external service that consumes Home Assistant events, use `backend-patterns`.
- Reviewing the security posture of an internet-exposed instance, use `security-review`.

---

### YAML syntax

Two-space indentation, block style everywhere, lowercase `true` and `false`. YAML 1.2 no longer treats `yes`, `no`,
`on`, and `off` as booleans, and the parser difference produces a config that loads on one version and not another.

Pass:

```yaml
automation:
  - alias: "Hallway light on motion"
    mode: restart
    initial_state: true
```

Fail:

```yaml
automation: [{alias: Hallway light on motion, initial_state: yes}]
```

Quote string values, leave null implicit rather than writing `~` or `null`, and prefer a UI-managed helper or config
entry over hand-written `template:` YAML wherever one exists. A helper is validated on save and travels in the
backup.

---

### Reference entities, never devices

`device_id` is a registry row that is regenerated when a device is removed and re-added. Every trigger, condition,
and action targets `entity_id`, which you control and which survives a re-pair.

Pass:

```yaml
trigger:
  - platform: state
    entity_id: binary_sensor.hallway_motion
    to: "on"
```

Fail:

```yaml
trigger:
  - platform: device
    device_id: 4f2c9b1ae8d3475fa0c6e2b7d914f083
    type: motion
```

Never edit anything under `.storage/` by hand. Go through the REST or WebSocket API, so the running instance stays
consistent with what is on disk.

---

### Native conditions over template conditions

A native condition is validated when the config loads. A template condition is only evaluated when the automation
runs, so a typo in it produces an automation that silently never fires and reports nothing.

Pass:

```yaml
condition:
  - condition: numeric_state
    entity_id: sensor.hallway_illuminance
    below: 15
```

Fail:

```yaml
condition:
  - condition: template
    value_template: "{{ states('sensor.hallway_iluminance') | float < 15 }}"
```

The failing version misspells the entity and coerces `unknown` to `0.0`, so it evaluates true forever and nobody
sees an error. Reach for a template condition only where no native condition can express the test, and validate it
in Developer Tools first.

---

### Wait on triggers, not on polled templates

`wait_template` re-evaluates against the state bus. `wait_for_trigger` subscribes to the event, so it costs nothing
while waiting and it cannot miss a transition between polls.

Pass:

```yaml
- wait_for_trigger:
    - platform: state
      entity_id: binary_sensor.hallway_motion
      to: "off"
      for: "00:02:00"
  timeout: "00:30:00"
  continue_on_timeout: true
```

Fail:

```yaml
- wait_template: "{{ is_state('binary_sensor.hallway_motion', 'off') }}"
  timeout: "00:30:00"
```

Always set a `timeout` and decide `continue_on_timeout` deliberately. A wait with no timeout leaves the automation
run alive indefinitely and it shows up as a stuck trace weeks later.

---

### Pick the automation mode on purpose

The default `single` drops a second trigger while the first run is still going, which is exactly wrong for a motion
timer: continued movement is ignored and the light goes out with someone standing under it. `restart` cancels the
running instance and starts the timer again.

Pass:

```yaml
- alias: "Hallway light on motion"
  mode: restart
  trigger:
    - platform: state
      entity_id: binary_sensor.hallway_motion
      to: "on"
  condition:
    - condition: numeric_state
      entity_id: sensor.hallway_illuminance
      below: 15
  action:
    - service: light.turn_on
      target:
        entity_id: light.hallway_ceiling
    - delay: "00:05:00"
    - service: light.turn_off
      target:
        entity_id: light.hallway_ceiling
```

Fail:

```yaml
- alias: "Hallway light on motion"
  mode: single
```

Use `queued` when every trigger must be handled in order, and `parallel` only when the runs genuinely do not touch
the same entity.

---

### Secrets

Every long-lived access token, API key, and password lives in `secrets.yaml` and is referenced with `!secret`.
`secrets.yaml` is never committed, and it is in `.gitignore` before the first token goes into it.

Pass:

```yaml
mqtt:
  broker: "mqtt.internal"
  username: !secret mqtt_username
  password: !secret mqtt_password
```

Fail:

```yaml
mqtt:
  broker: "mqtt.internal"
  username: "homeassistant"
  password: "hunter2"
```

- Ref: https://www.home-assistant.io/docs/configuration/secrets/
- Rotate long-lived access tokens used by MCP clients and external integrations at least every 90 days.

---

### MCP exposure

Home Assistant's MCP server speaks Streamable HTTP, and the current Claude Code CLI connects to remote MCP servers
over HTTP and SSE directly. A `stdio` proxy is only needed for a client that still supports nothing but `stdio`, so
check the client before adding one rather than assuming it.

Expose only what the assistant needs. Locks, garage doors, alarm panels, and anything else whose actuation has a
physical security consequence stay unexposed, whatever the client is.

Pass:

```yaml
homeassistant:
  expose:
    - light.hallway_ceiling
    - sensor.living_room_temperature
```

Fail:

```yaml
homeassistant:
  expose:
    - lock.front_door
    - cover.garage_door
    - alarm_control_panel.house
```

- Ref: https://www.home-assistant.io/integrations/mcp_server/
- Secure `/api/mcp` with a long-lived access token scoped to the agent, or OAuth where the client supports it.

---

### Entity naming

Use `domain.location_device_property`, lowercase with underscores, never abbreviated. The entity ID is the thing
every automation, dashboard, and script references, so it is a name you have to live with.

Pass:

```yaml
binary_sensor.front_door_contact
```

Fail:

```yaml
binary_sensor.fd_c
```

Group entities with the area registry rather than repeating the area inside the ID more than once.

---

### Reference files

| Open this | For |
|---|---|
| [references/operations.md](references/operations.md) | Choosing between a blueprint, an automation and a script, tracing and testing a change, backups and restores, HACS hygiene, the notification priority taxonomy, and upgrade discipline |

---

### Related skills

- `python-patterns` and `python-testing` for building and testing a custom integration in Python.
- `security-review` before exposing the instance, its API, or a new entity set to anything outside the LAN.
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
