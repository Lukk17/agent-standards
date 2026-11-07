# Configuration Rules in Depth

Contents:

- [YAML syntax](#yaml-syntax)
- [Automation keys](#automation-keys)
- [Reference entities, never devices](#reference-entities-never-devices)
- [Native conditions over template conditions](#native-conditions-over-template-conditions)
- [Pick the right wait](#pick-the-right-wait)
- [Pick the automation mode on purpose](#pick-the-automation-mode-on-purpose)
- [Secrets](#secrets)
- [MCP access](#mcp-access)
- [Entity naming](#entity-naming)

Companion reference for the [home-assistant](../SKILL.md) skill. Load it for the reasoning and the pass and fail YAML behind each rule: YAML syntax, the automation keys, entity references, native conditions, waits, automation modes, secrets, MCP access, and entity naming. Triggers, helpers, templates and device actions in more depth are in [automations-and-helpers.md](automations-and-helpers.md).

VERIFIED means read in the Home Assistant documentation source, github.com/home-assistant/home-assistant.io on branch `current`, or in the page named.

---

### YAML syntax

Two-space indentation, block style everywhere, lowercase `true` and `false`. YAML 1.2 no longer treats `yes`, `no`, `on`, and `off` as booleans, and the parser difference produces a config that loads on one version and not another. `True` and `False` are out as well. VERIFIED, the YAML style guide in home-assistant/contributors.home-assistant.io, `src/content/docs/writing/reference/yaml.md`, published at https://contributors.home-assistant.io/writing/reference/yaml/, section "Booleans": "Use only `true` and `false`, in lowercase."

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

Quote string values with double quotes, leave null implicit rather than writing `~` or `null`, and prefer a UI-managed helper or config entry over hand-written `template:` YAML wherever one exists. A helper is validated on save and travels in the backup. VERIFIED for quoting and nulls, same page, sections "Strings" ("Quote strings with double quotes.") and "Null values".

---

### Automation keys

Automations list `triggers:`, `conditions:` and `actions:`. Each trigger names its kind with `trigger:`, and each action names what it calls with `action:`. Entities go in `target:` and settings in `data:`. VERIFIED, `source/_docs/automation/trigger.markdown` ("In YAML, list each trigger under `triggers`") and `source/_docs/automation/yaml.markdown`. Older files still use `platform:` in a trigger, `service:` in an action, and singular top-level `trigger:`, `condition:` and `action:`. Home Assistant still loads them, and the editor rewrites them to the new names on save, but one place must not mix an old and a new key, so an agent writes only the new ones. VERIFIED, `source/_docs/automation/yaml.markdown`, section "Older YAML syntax": "Home Assistant still accepts the old keys, so these examples keep working."

Pass:

```yaml
triggers:
  - trigger: motion.detected
    target:
      entity_id: binary_sensor.hallway_motion
actions:
  - action: light.turn_on
    target:
      entity_id: light.hallway_ceiling
```

Fail:

```yaml
trigger:
  - platform: state
    entity_id: binary_sensor.hallway_motion
action:
  - service: light.turn_on
    data:
      entity_id: light.hallway_ceiling
```

Create automations, scripts, scenes and helpers through the config API, or the MCP server tools built on it, rather than handing over a YAML snippet to paste. The API validates what it is given. With no API access, give the YAML for the editor's Edit in YAML mode, or the form fields of a helper, and name every entity ID you assumed.

---

### Reference entities, never devices

`device_id` is a registry row that is regenerated when a device is removed and re-added. Every trigger, condition, and action targets `entity_id`, which you control and which survives a re-pair.

Pass:

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.hallway_motion
    to: "on"
```

Fail:

```yaml
triggers:
  - trigger: device
    device_id: 4f2c9b1ae8d3475fa0c6e2b7d914f083
    domain: binary_sensor
    type: motion
```

Never edit anything under `.storage/` by hand. Go through the REST or WebSocket API, so the running instance stays consistent with what is on disk. The one exception to the `entity_id` rule, the discovered device trigger of a Zigbee2MQTT button, is in [automations-and-helpers.md](automations-and-helpers.md).

---

### Native conditions over template conditions

A native condition is validated when the config loads. A template condition is only evaluated when the automation runs, so a typo in it produces an automation that silently never fires and reports nothing.

Pass:

```yaml
conditions:
  - condition: numeric_state
    entity_id: sensor.hallway_illuminance
    below: 15
```

Fail:

```yaml
conditions:
  - condition: template
    value_template: "{{ states('sensor.hallway_iluminance') | float < 15 }}"
```

The failing version misspells the entity and coerces `unknown` to `0.0`, so it evaluates true forever and nobody sees an error. Reach for a template condition only where no native condition can express the test, and validate it in the template editor first.

---

### Pick the right wait

`wait_for_trigger` waits for a change that happens after the wait starts. `wait_template` waits for a condition and continues at once when it already holds. VERIFIED, `source/_building_blocks/wait_for_trigger.markdown`: "The wait only reacts to a change that happens after the wait starts. If the state is already there, the automation or script keeps waiting." And `source/_building_blocks/wait_template.markdown`: "If the template is already true when the wait starts, the next steps run right away."

Use `wait_for_trigger` for an event or a transition, such as the door closing. Use `wait_template` when the state may already be there, such as waiting for a media player to be idle. A `wait_for_trigger` on a state that already holds waits until the entity leaves it and comes back, or forever without a timeout.

Pass, waiting for a change:

```yaml
- wait_for_trigger:
    - trigger: state
      entity_id: binary_sensor.hallway_motion
      to: "off"
      for:
        minutes: 2
  timeout: "00:30:00"
  continue_on_timeout: true
```

Pass, waiting for a state that may already hold:

```yaml
- wait_template: "{{ is_state('media_player.living_room', 'idle') }}"
  timeout: "00:05:00"
  continue_on_timeout: false
```

Always set a `timeout` and decide `continue_on_timeout` deliberately, because it is on by default. VERIFIED, both pages: "Turned on by default." A wait with no timeout leaves the run alive indefinitely and it shows up as a stuck trace weeks later. Check `wait.completed` afterwards when the next step depends on whether the wait ended in time.

---

### Pick the automation mode on purpose

The default `single` drops a second trigger while the first run is still going, which is exactly wrong for a motion timer: continued movement is ignored and the light goes out with someone standing under it. `restart` cancels the running instance and starts the timer again.

Pass:

```yaml
- id: "hallway_light_on_motion"
  alias: "Hallway light on motion"
  mode: restart
  triggers:
    - trigger: motion.detected
      target:
        entity_id: binary_sensor.hallway_motion
  conditions:
    - condition: numeric_state
      entity_id: sensor.hallway_illuminance
      below: 15
  actions:
    - action: light.turn_on
      target:
        entity_id: light.hallway_ceiling
    - delay: "00:05:00"
    - action: light.turn_off
      target:
        entity_id: light.hallway_ceiling
```

Fail:

```yaml
- alias: "Hallway light on motion"
  mode: single
```

Use `queued` when every trigger must be handled in order, `parallel` only when the runs genuinely do not touch the same entity, and `single` for a one-shot notification. A restart ends the five-minute delay above as well, see [automations-and-helpers.md](automations-and-helpers.md).

---

### Secrets

Every long-lived access token, API key, and password lives in `secrets.yaml` and is referenced with `!secret`. `secrets.yaml` is never committed, and it is in `.gitignore` before the first token goes into it.

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

### MCP access

Two different servers reach Home Assistant, and the exposed entity list limits only part of one of them.

1. The built-in Model Context Protocol integration groups its tools into sets. Device control sees and controls only the entities on the exposed entities page, while the Home Assistant set "can read all entities, logs, and history, and perform any action". The main URL `/api/mcp` offers every set by default, and `/api/mcp/assist` offers Device control only. VERIFIED, `source/_integrations/mcp_server.markdown`, introduction and "Configuration options".
2. So an assistant that should touch only some devices connects to `/api/mcp/assist`, or the main URL is configured with Expose all AI tools turned off and Device control chosen, and Read-only turned on where it only needs to look. VERIFIED, same page. Which entities it sees is then set on Settings, Voice assistants, Expose, not in YAML.
3. A server that holds a long-lived access token, such as ha-mcp, acts with every right of that user, because a long-lived token has no scope of its own, and the exposed entity list does not limit it. INFERRED, high confidence, because exposure belongs to the Assist API and the REST and WebSocket APIs have no such filter. Give it the token of a dedicated user that may log in only from the local network, and rotate it on schedule.
4. Never put a lock, garage door, alarm panel or anything else with a physical security consequence within reach of an assistant that should not have it, whatever the client is.
5. Home Assistant's server speaks Streamable HTTP, and Claude Code connects to remote MCP servers over HTTP directly. A `stdio` proxy is only needed for a client that supports nothing else, so check the client before adding one. OAuth with PKCE is supported, so use it where the client can. VERIFIED for OAuth, same page, "Client configuration".
6. When the ha-mcp server is connected, read its best-practices skill before a matching task, through the MCP resource `skill://home-assistant-best-practices/SKILL.md` or, when resources cannot be read, the `ha_get_skill_guide` tool. Before filing a GitHub issue about ha-mcp, run its `ha_report_issue` tool first. VERIFIED, the server's own instructions to the client.
7. Avoid polling the instance in a tight loop from an assistant. Batch reads, and back off on `HTTP 429`, as [operations.md](operations.md) describes.

---

### Entity naming

Use `domain.location_device_property`, lowercase with underscores, never abbreviated. The entity ID is the thing every automation, dashboard, and script references, so it is a name you have to live with.

Pass:

```yaml
binary_sensor.front_door_contact
```

Fail:

```yaml
binary_sensor.fd_c
```

Group entities with the area registry rather than repeating the area inside the ID more than once. Renaming an entity that is already in use follows [renames-and-refactoring.md](renames-and-refactoring.md).
