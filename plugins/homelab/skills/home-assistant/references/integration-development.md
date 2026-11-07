# Integration development

Contents:

- [Where the code lives](#where-the-code-lives)
- [Design rules](#design-rules)
- [Config flow](#config-flow)
- [Entities](#entities)
- [Actions](#actions)
- [Quality scale](#quality-scale)
- [Tests](#tests)
- [Diagnostics](#diagnostics)
- [Repairs](#repairs)
- [Replacing a legacy device tracker](#replacing-a-legacy-device-tracker)

Companion reference for the [home-assistant](../SKILL.md) skill. Load it to build, test or review a Home Assistant integration in Python, in Home Assistant Core or as a custom integration. General Python style and pytest habits stay with the `python-patterns` skill, and this file adds only what Home Assistant asks for on top.

Source of the ideas: home-assistant/core, `.claude/skills/ha-integration-knowledge` on branch `dev`, Apache-2.0, rewritten here in our own words.

VERIFIED means checked against the Home Assistant developer documentation, read in its source repository home-assistant/contributors.home-assistant.io under `src/content/docs/`, in the file named, and published at https://contributors.home-assistant.io. UNVERIFIED means read only in the upstream skill above, a third-party skill file, and not checked against that documentation or Core source.

---

### Where the code lives

1. In Core, the code sits in `homeassistant/components/<domain>/` and its tests in `tests/components/<domain>/`. UNVERIFIED, from the upstream skill.
2. A custom integration sits in `<config directory>/custom_components/<domain>/`. A custom integration with the domain of a built-in one replaces it, and the user then stops getting updates for that integration. VERIFIED, `core/integrations/file-structure.md`, https://contributors.home-assistant.io/core/integrations/file-structure/: "A custom integration with the same domain as a built-in one overrides it."
3. A custom integration must carry a `version` key in `manifest.json` that AwesomeVersion understands, and that key is valid only in a custom integration. VERIFIED, `core/integrations/manifest.md`, section "Custom integrations only", https://contributors.home-assistant.io/core/integrations/manifest/.

---

### Design rules

1. Copy patterns from integrations at the platinum or gold quality scale level before lower ones. UNVERIFIED, from the upstream skill.
2. Keep the integration a thin layer. Protocol handling, parsing and device state machines belong in a separate library published on PyPI. When it is not clear whether some logic belongs in the library, ask before writing it into the integration. UNVERIFIED, from the upstream skill.
3. When the library cannot do something, fix the library and bump it. Do not add a workaround for the library inside the integration. UNVERIFIED, from the upstream skill.
4. The polling interval is a choice the developer makes, never a field in the config flow. A user who needs another interval polls with an automation. VERIFIED, `core/quality-scale/appropriate-polling.md`: "It is not a field in the config flow."
5. A config flow does not ask the user for the entry name. Home Assistant generates it and the user can rename it later. A helper integration is the exception. UNVERIFIED, from the upstream skill.
6. Data that Home Assistant hands out only through an action gets no entity of its own. Weather forecasts are the example: they come from `weather.get_forecasts`. UNVERIFIED, from the upstream skill.
7. A dependency bump is its own change, holding only what the new version forces. A feature that needs the new version comes in a later change. UNVERIFIED, from the upstream skill.

---

### Config flow

1. Map every known failure to the standard error key, such as `invalid_auth` or `cannot_connect`, and do not log it. VERIFIED that `cannot_connect` is set as `errors["base"]` for a connection error, `core/integrations/config-flow.md`. Not logging it is UNVERIFIED, from the upstream skill.
2. Catch an unexpected exception only to log it with `_LOGGER.exception()` and show the `unknown` error. UNVERIFIED, from the upstream skill.
3. An error the user sees is either fully translated or not at all. Never join a translated string with raw text. UNVERIFIED, from the upstream skill.

---

### Entities

1. `async_added_to_hass()` and `async_will_remove_from_hass()` mirror each other: what the first sets up, the second tears down. UNVERIFIED, from the upstream skill.
2. Register the cleanup of anything set up in `async_added_to_hass()` with `async_on_remove`, because `async_will_remove_from_hass()` does not run when adding the entity is aborted or fails. Keep `async_will_remove_from_hass()` for what `async_on_remove` cannot undo, such as a connection that belongs to this entity only. VERIFIED, `core/entities/lifecycle.md`.
3. A value that never changes goes in an `_attr_*` attribute, not a property. Put it on the class only when every instance shares it. UNVERIFIED, from the upstream skill.
4. An `available` override combines its own test with the parent: `return super().available and <own test>`. UNVERIFIED, from the upstream skill.
5. Trust the entity base class, such as `SensorEntity`. Do not declare again what it already provides, and do not guard against it changing. UNVERIFIED, from the upstream skill.

---

### Actions

The upstream skill is the only source for the rules in this section, so each one is UNVERIFIED, from the upstream skill. The developer documentation, `core/integrations/actions.md`, confirms only that actions are still called services in code and are described in `services.yaml`. VERIFIED.

1. Name the actions and their fields in two `StrEnum` classes, `<Prefix>Service` and `<Prefix>ServiceArgument`, with the prefix the integration already uses for its classes. An integration keeps them in `services.py`, or in `const.py` when other modules need them. An entity platform keeps them in `const.py` and exports them.
2. The members match the actions that are really registered and their fields in `services.yaml`, nothing more. A stale entry in `services.yaml` gets no member.
3. Use the members to register the action, to build the schema and to read `call.data`, instead of plain strings or `SERVICE_*`, `ATTR_*` or `CONF_*` constants. The shared selector fields `config_entry_id`, `device_id` and `entity_id` keep the constants from `homeassistant.const`.
4. In a review, ask for these enums as a blocking change only when the change adds the first actions of an integration, that is a new `services.yaml`.
5. Do not ask for checks of a field that the validation schema or the entity filter already enforces. Add a guard only where a value skips validation or is transformed in an unsafe way.
6. When validation guarantees that a key exists, read it as `data["key"]`, not `data.get("key")`, so a wrong assumption fails at once.

---

### Quality scale

1. The tiers are Bronze, Silver, Gold and Platinum, and an integration earns a tier by following every rule of that tier and of the tiers below it. A new Core integration must reach Bronze. VERIFIED, `core/quality-scale/index.md`. The rules per tier are at https://contributors.home-assistant.io/core/quality-scale/rules/.
2. The `quality_scale` key in `manifest.json` names the tier. An integration with a tier has a `quality_scale.yaml` that gives each rule as `done`, `todo`, or `exempt` with a reason, and hassfest fails when a rule the tier needs is neither `done` nor `exempt`. VERIFIED, same file.
3. The starting file is `script/scaffold/templates/integration/integration/quality_scale.yaml`. UNVERIFIED, from the upstream skill.
4. A custom integration gets no quality scale review, but the Bronze rules still make a good checklist for one. INFERRED, high confidence, because the rules describe behaviour rather than Core process.

---

### Tests

1. Test through Home Assistant's public interfaces, never by poking at the integration's internals, so the tests survive a refactor. VERIFIED, `core/development/tests.md`, section "Test through Home Assistant", https://contributors.home-assistant.io/core/development/tests/#test-through-home-assistant.
2. Put shared setup in fixtures in the `conftest.py` of the integration's tests, typically one for the config entry, one that mocks the library and one that sets it all up. VERIFIED, same file. Give the mock config entry a `unique_id` when the real entries have one. UNVERIFIED, from the upstream skill.
3. Keep sample data in the `fixtures/` folder and load it with `load_json_object_fixture` or `load_json_array_fixture` from `pytest_homeassistant.common`, or their `async_` forms in async code, instead of building it inline with `json.dumps()`. VERIFIED, same file, section "Fixtures and mocking". For a custom integration the same helpers ship in the `common` module of `pytest-homeassistant-custom-component`. VERIFIED, `src/pytest_homeassistant_custom_component/common.py` in MatthewFlamm/pytest-homeassistant-custom-component.
4. Mock the library, not Home Assistant, and patch the library's client class where the integration imports it. VERIFIED, same file.
5. Use `@pytest.mark.parametrize` when several tests do the same thing with different inputs, and avoid `if` statements in tests. VERIFIED, same file. To give one test other mock data, parametrize the fixture that supplies it, with `indirect=True` when the fixture reads `request.param`, instead of patching again inside the test. UNVERIFIED, from the upstream skill.
6. Do not assert by hand what a snapshot test already covers. UNVERIFIED, from the upstream skill. Core takes snapshots with Syrupy. VERIFIED, same file.
7. Use the `Platform` member or the `ATTR_*` constant where one exists, not a string literal. UNVERIFIED, from the upstream skill.

---

### Diagnostics

Diagnostics are a Gold rule, not a Bronze one, so they are required only for an integration that aims for Gold or above. The platform lives in `diagnostics.py` with `async_get_config_entry_diagnostics`, `async_get_device_diagnostics`, or both, and it never returns a password, a token or coordinates. VERIFIED, `core/quality-scale/diagnostics.md`: "This is a Gold rule."

---

### Repairs

1. An issue is raised with `ir.async_create_issue`, with `is_fixable` saying whether a repair flow can fix it. An issue that only explains what to do needs no `repairs.py`. A fixable issue whose fix is only a confirmation needs none either, because Home Assistant falls back to `ConfirmRepairFlow`. Only a fix that needs more than a confirmation goes in `repairs.py`, with `async_create_fix_flow`. VERIFIED, `core/integrations/repairs.md`, section "Fix an issue with a repair flow".
2. Severity: `CRITICAL` only for true panic, `ERROR` when something is broken now and needs attention at once, `WARNING` when something will break later, such as an API shutting down. VERIFIED, same file.
3. Delete an issue only when the problem is gone, because a user who ignored it keeps it ignored until it is deleted and created again. VERIFIED, same file.
4. Raise an issue only for a problem the user can fix. The text says what is wrong, why it matters, the exact steps to fix it (numbered when there are several) and what the user sees afterwards, naming the device and the error involved, in friendly words. Never give a vague step such as "update the firmware". UNVERIFIED, from the upstream skill.

---

### Replacing a legacy device tracker

The upstream skill's `platform-device-tracker.md` is the only source for this section, so each statement here is UNVERIFIED, from the upstream skill.

A legacy device tracker platform defines `get_scanner`, `async_get_scanner`, `setup_scanner` or `async_setup_scanner`, uses `DeviceScanner` or the `see` and `async_see` callbacks, and keeps its devices in `known_devices.yaml`. These are deprecated, with removal planned for 2027.5.

1. Add no new legacy platform and no feature to an existing one.
2. When config entry based `ScannerEntity` or `TrackerEntity` entities replace a legacy platform, do not migrate the legacy trackers. A tracker from `known_devices.yaml` has no entity registry entry and keeps holding `device_tracker.<dev_id>` until the legacy code is removed, so a new entity with that ID is dropped at startup or gets a `_2` suffix, while the old one keeps writing stale states.
3. In a review of such a change, flag: an import of the tracker YAML through a `SOURCE_IMPORT` flow, any read or write of `known_devices.yaml`, reuse of the legacy entity IDs, removal of legacy states with `hass.states.async_remove`, and enabling entities from the `track` flag.
4. Instead, keep the legacy platform working until it goes away, and raise a repair issue from its setup with `breaks_in_ha_version="2027.5.0"` and a translation key of the integration's own, because the core `deprecated_yaml` issue says the configuration was imported. Raise it only for platforms that have a config entry replacement.
5. The issue and the breaking change notes give the user these steps in this order:
   a) Remove the tracker platform from `configuration.yaml`, which otherwise keeps adding devices to `known_devices.yaml`.
   b) Remove the tracked devices from `known_devices.yaml` and restart, because the old entity IDs stay taken until the restart.
   c) Set up the integration in the UI. `ScannerEntity` entities with a MAC address start disabled unless another integration already knows that MAC address, so enable the ones you need.
   d) Rename the new trackers to the old entity IDs if needed.
