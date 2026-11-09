# Automations, helpers, templates and devices

Contents:

- [Choosing a trigger or condition](#choosing-a-trigger-or-condition)
- [Restarts, reloads and unavailable states](#restarts-reloads-and-unavailable-states)
- [Buttons and remotes](#buttons-and-remotes)
- [Helpers before templates](#helpers-before-templates)
- [Template entities and shared macros](#template-entities-and-shared-macros)
- [Actions inside a sequence](#actions-inside-a-sequence)
- [Turning an automation off](#turning-an-automation-off)
- [Putting devices back with a scene](#putting-devices-back-with-a-scene)
- [Blueprints](#blueprints)
- [Device actions](#device-actions)

Companion reference for the [home-assistant](../SKILL.md) skill. Load it to write the triggers, conditions and actions of an automation or a script, to choose a helper over a template, to share Jinja between templates, or to write a blueprint. The pass and fail YAML for the core rules is in [configuration-examples.md](configuration-examples.md).

VERIFIED means read in the Home Assistant documentation source, github.com/home-assistant/home-assistant.io on branch `current`, in the file named. UNVERIFIED means taken from the best-practices skill that the ha-mcp server ships, `home-assistant-best-practices` in homeassistant-ai/skills, and not checked against a primary source. Several features below arrived in a specific release, so read the instance version first, as rule 12 of SKILL.md says.

---

### Choosing a trigger or condition

Pick in this order: a purpose-specific trigger or condition, then a generic native one, then a template.

1. A purpose-specific trigger is named `<domain>.<name>`, such as `motion.detected`, `motion.cleared`, `door.opened` or `battery.became_low`, and takes a `target:` that can be an entity, an area, a floor, a device or a label. VERIFIED, `source/_triggers/motion.detected.markdown`.
2. With several targets, `options.behavior` decides when it fires: `each` (the default), `first` or `all`. `options.for` sets how long the state must hold. VERIFIED, same file.
3. "No motion anywhere in the area for ten minutes" is one `motion.cleared` trigger on the area with `behavior: all` and a `for:`, not a list of sensors with a delay. VERIFIED for the options, the rest of the pattern UNVERIFIED.
4. One known sensor is no reason to fall back to `trigger: state`. The purpose-specific trigger takes `target: {entity_id: ...}` as well. VERIFIED, same file.
5. Older purpose-specific keys such as `battery.low`, and `behavior: any` or `last`, were renamed and the old forms stop loading. UNVERIFIED. Open the trigger's own page under `/triggers/` before writing a key from memory.
6. Common native swaps: a float comparison template becomes `numeric_state` with `above:`, two `is_state` tests become `condition: and` with two state conditions, an hour test becomes `condition: time` with `after:`. Conditions check the state once, right after the trigger, and never again later. VERIFIED, `source/_docs/automation/how-automations-react-to-changes.markdown`.

---

### Restarts, reloads and unavailable states

1. A reload or a save stops the runs of the automations that changed and cancels their running "For at least" waits. A restart does the same for every automation. A cancelled wait does not resume by itself. VERIFIED, `how-automations-react-to-changes.markdown`, section "Startup, reload, and restart".
2. A restart also stops every run that sits in a `wait_for_trigger`, and it does not continue afterwards. VERIFIED, `source/_building_blocks/wait_for_trigger.markdown`.
3. So a long `delay` or a long `for:` is no safety net. Record the real start in an `input_datetime` helper and compare the elapsed time against it, or use a `timer` helper. The helper pattern is UNVERIFIED.
4. Most purpose-specific triggers ignore an entity that comes back from `unavailable` or `unknown`, while the generic state trigger reacts to it. VERIFIED, same file.
5. A `numeric_state` trigger is armed again when its entity passes through `unavailable`, so an unchanged value can fire it after a restart or a short drop. Guard a costly action with a condition on `trigger.from_state` that checks `trigger.platform` first, knowing it also drops real crossings that passed through `unavailable`. UNVERIFIED.

---

### Buttons and remotes

1. When the integration offers an `event.*` entity for the button, trigger on `event.received` with that entity as the target, and read the possible values from its `event_types` attribute. VERIFIED that `event.received` exists, `source/_triggers/event.received.markdown`, the rest UNVERIFIED.
2. ZHA has no event entities for buttons, so use an `event` trigger on `zha_event` keyed by `device_ieee`, which survives a re-pair. UNVERIFIED.
3. Zigbee2MQTT event entities are experimental and off by default, so use its discovered device trigger or an `mqtt` trigger. That discovered device trigger is the one exception to the `entity_id` rule in SKILL.md, rule 3. UNVERIFIED.

---

### Helpers before templates

Before writing a template sensor, check for a helper that already does the job. A helper is set up in Settings, Devices and services, Helpers, validates its fields, and travels in the backup. UNVERIFIED for the table, which follows the ha-mcp skill.

| Need | Helper |
|---|---|
| Sum, mean, min or max of several sensors | `min_max` |
| Average or other statistic over time | `statistics` |
| Rate of change | `derivative` |
| On or off past a limit, with hysteresis | `threshold` |
| Rising or falling | `trend` |
| Use per day, week or month | `utility_meter` |
| Time spent in a state | `history_stats` |
| Power into energy | `integration` |
| Any on or all on | `group` |
| Smooth a noisy sensor, drop out-of-range values | `filter` |
| Counting, a countdown, a weekly plan, a time-of-day window | `counter`, `timer`, `schedule`, `tod` |
| A thermostat from a switch and a temperature sensor | `generic_thermostat` |
| A switch shown as a light, a cover or a lock | `switch_as_x` |
| A value set by a person | `input_boolean`, `input_number`, `input_select`, `input_text`, `input_datetime`, `input_button` |

1. When no helper fits, create a Template helper in the same menu. Write a `template:` YAML block only when the user asks for it or when the entity needs something the helper form has no field for, such as its own triggers or `attributes:`. UNVERIFIED.
2. Several energy sensors for the Energy dashboard are added there one by one, not summed with `min_max`, because a `measurement` sensor compiles no `sum` statistics. UNVERIFIED.

---

### Template entities and shared macros

1. Every entity in a `template:` YAML block has a `unique_id`, so it gets a registry entry and can be renamed and placed in an area. VERIFIED that the key exists, `source/_integrations/template.markdown`. A Template helper gets its ID from the config entry, so do not carry `unique_id` into the helper form. UNVERIFIED.
2. Give a template entity an `availability` template, so a missing source shows `unavailable` instead of a wrong number. VERIFIED that the key exists, same file.
3. Set `device_class`, `unit_of_measurement` and, for a numeric sensor that needs history graphs and long-term statistics, `state_class`. UNVERIFIED for the statistics claim.
4. Use plural `triggers:` and `actions:` in a trigger-based template block, keep state-based entities of one type in one block, and give each trigger-based block its own entry. UNVERIFIED.
5. When the same Jinja logic appears in two or three templates, and a native trigger, condition or helper is already ruled out, put it once as a macro in a `.jinja` file under `config/custom_templates/` and import it with its full file name. VERIFIED, `source/_docs/templating/custom-templates.markdown`. After an edit, run `homeassistant.reload_custom_templates`. VERIFIED that the action exists, `source/_actions/homeassistant.reload_custom_templates.markdown`.
6. An imported macro does not see the caller's variables, such as `trigger`, `this` or a `{% set %}` value, so pass them as arguments. INFERRED, high confidence, because a Jinja import runs without the caller's context unless it says `with context`.
7. A macro returns text. A macro meant to return a number or a list returns a string of one. UNVERIFIED for the `as_function` filter the ha-mcp skill offers around this.

---

### Actions inside a sequence

1. After a wait, test `wait.completed` rather than assuming the trigger came. VERIFIED, `wait_for_trigger.markdown`: "To check whether a trigger reacted, use `wait.completed`."
2. Use `stop:` to end a sequence early instead of nesting the rest in a condition. Add `error: true` to mark the run as failed. UNVERIFIED.
3. Compute a value once with `variables:` and reuse it. `trigger_variables:` runs before the triggers and takes only limited templates without `states()`. VERIFIED for when it is set, `source/_docs/automation/yaml.markdown`, the template limit UNVERIFIED.
4. Set `continue_on_error: true` only on an action whose failure does not matter, such as an optional notification, because it hides the error. UNVERIFIED.
5. Some actions refuse a user who is not an administrator. An automation run carries no user and passes, a dashboard button pressed by a non-administrator fails with `Unauthorized`. UNVERIFIED.
6. Write the purpose of an automation or script in `description:`. UNVERIFIED for the per-step `note:` key the ha-mcp skill describes.

---

### Turning an automation off

1. `automation.turn_off` stops the triggers and, by default, the running actions. The state survives a restart only when the automation has an `id:`. UNVERIFIED.
2. Disabling the entity in its settings removes it from the state machine and survives restarts. UNVERIFIED.
3. `enabled: false` belongs on a single trigger, condition or action, never at the top level of an automation. VERIFIED for triggers, `source/_docs/automation/trigger.markdown`: "In YAML, add `enabled: false` to the trigger." The top-level failure is UNVERIFIED.
4. `automation.trigger` runs an automation even when it is turned off. VERIFIED, `source/_actions/automation.trigger.markdown`.
5. Give every YAML automation an `id:`. With it the name and entity ID can change in the UI and traces are stored. VERIFIED, `source/_docs/automation/yaml.markdown`.

---

### Putting devices back with a scene

To change devices for a moment and then put them back, call `scene.create` with `snapshot_entities` before the change and `scene.turn_on` on that scene afterwards. The snapshot keeps each entity's own state, including a light that was off. Do not copy states into `variables:`. VERIFIED for `snapshot_entities`, `source/_actions/scene.create.markdown`. A scene made this way disappears on a scene reload or a restart. VERIFIED, same file: "It disappears when you reload the scenes or restart Home Assistant."

---

### Blueprints

1. Every entity, device or area comes from an `!input` with a typed selector, never a hardcoded ID or free text. Use a `target` selector when the input goes into `target:`. UNVERIFIED.
2. Bind an input to `variables:` before using it in a template, because `!input` is a YAML tag, not a template value. UNVERIFIED.
3. Give tuning inputs a `default:`, and leave the controlled entity without one. UNVERIFIED.
4. Treat input keys as a public interface. Add new inputs with defaults and never rename or remove an old one, because existing automations name them. UNVERIFIED.
5. Set `homeassistant.min_version` when the blueprint uses a feature from a given release. VERIFIED, `source/_docs/blueprint/schema.markdown`.
6. Set `source_url` so the blueprint can be imported again from the same place. UNVERIFIED.

---

### Device actions

1. Entities go in `target:`, settings go in `data:`. `entity_id` inside `data:` is the old form. VERIFIED that every action page lists targets apart from data, for example `source/_actions/automation.trigger.markdown`. The old form claim is UNVERIFIED.
2. Target an area, a floor or a label where a whole room is meant, so the automation follows the area as devices come and go. `device_id` in a target breaks on a re-pair. UNVERIFIED for the floor and label part.
3. Light colour temperature is set with `color_temp_kelvin`. The page for `light.turn_on` lists no mired option. VERIFIED, `source/_actions/light.turn_on.markdown`. A mired value copied across is read as Kelvin, so convert it: Kelvin is 1,000,000 divided by mireds, 500 mireds is 2000 K.
4. A vacuum cleans rooms with `vacuum.clean_area` and Home Assistant area IDs, once its segments are mapped to areas in the entity settings, rather than `vacuum.send_command` with vendor room IDs. VERIFIED that the action exists, `source/_actions/vacuum.clean_area.markdown`, the mapping step UNVERIFIED.
