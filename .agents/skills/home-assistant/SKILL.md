---
name: home-assistant
description: Home Assistant automation standards covering YAML conventions, entity naming, event-driven design, MCP server rules, backup, and notification routing.
origin: project-standards
---

# Home Assistant Standards

## Core Execution Directives

- Treat all LLM generated YAML, entity IDs, and state management logic as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every HA architectural decision.
- Append a Zero-Trust directive demanding mandatory web searches for current HA documentation, specifically regarding MCP integration, Assist API limits, and YAML schemas.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official HA documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every YAML node, automation mode, and service call provided.
- Mandate direct, working links to the official HA documentation used to ground the code.

---

## YAML Configuration Syntax

- Enforce strict 2-space indentation.
- Use exclusively lowercase `true` and `false` for booleans. Strictly prohibit the use of `True`, `False`, `yes`, `no`, `on`, or `off` to maintain YAML 1.2 compliance and prevent parsing errors.
  - Ref: https://developers.home-assistant.io/docs/documenting/yaml-style-guide/
- Mandate block-style sequences and mappings. Do not use flow-style (JSON-like) syntax such as `[1, 2]` or `{key: value}` in YAML files.
- Wrap all string values in double quotes (`"string"`). Implicitly mark null values instead of using `~` or `null`.
- Prohibit generating raw YAML manually for core configurations if a UI-managed Template Helper or Config Entry is available. Always prefer UI-configured Helpers over raw `template:` YAML to ensure syntax validation and reliable backups.

---

## State Management and Automations

- Use `entity_id` exclusively over `device_id` in all triggers, conditions, and actions. Device IDs break silently if a device is removed and re-added to the Zigbee/Z-Wave/Wi-Fi network.
- Use native conditions (e.g., `numeric_state`) instead of template conditions. Native conditions are validated at load time rather than runtime, preventing silent failures.
- Build event-driven automations. Use `wait_for_trigger` with state triggers instead of polling the state bus with `wait_template`.
- Strictly prohibit direct modification of internal state files within the `.storage/` directory. Use the HA REST or WebSocket API to interact with internal states to prevent database corruption.
- Use `mode: restart` for motion-triggered automations rather than `mode: single` to ensure lighting timers reset properly upon continuous movement.

---

## MCP (Model Context Protocol) Integration

- Restrict MCP LLM access strictly to explicitly exposed entities via the Home Assistant Assist API. Do not expose administrative or security entities (locks, garage doors, alarm panels) to the MCP client to prevent unauthorized autonomous actuation.
  - Ref: https://www.home-assistant.io/integrations/mcp_server/
- Secure the MCP server endpoint (`/api/mcp`) using a Long-Lived Access Token (LLAT) scoped specifically for the LLM agent, or use OAuth if the client supports it.
- If the MCP client (like Cursor or Claude Code local CLI) only supports `stdio` transport, explicitly define the architecture to route through an `mcp-proxy`, as HA natively implements the Streamable HTTP (SSE) protocol for its MCP server.

---

## API Rate Limits and Polling Constraints

- Respect local integration and external cloud API rate limits. Group state updates and avoid aggressive, high-frequency polling from the LLM.
- Implement conservative rate limits for external notifications matching the HA Companion App's limit of 150 notifications per 24 hours to prevent the AI from spamming user devices.
- Handle `HTTP 429 Too Many Requests` gracefully in any external scripts or MCP clients querying the HA REST API by implementing exponential backoff.

---

## Entity Naming Conventions

- Use the pattern `domain.location_device_property` for entity IDs (e.g., `sensor.living_room_temperature`, `light.bedroom_ceiling`).
- Never abbreviate entity names; prefer clarity over brevity (`binary_sensor.front_door_contact` not `binary_sensor.fd_c`).
- Use lowercase with underscores only; no spaces, hyphens, or capital letters in entity IDs.
- Group related entities using the `area` registry rather than encoding the area in the entity ID multiple times.

---

## Secrets Management

- Store all long-lived access tokens, API keys, and passwords in `secrets.yaml`; reference them in configuration with `!secret key_name`.
  - Ref: https://www.home-assistant.io/docs/configuration/secrets/
- Never commit `secrets.yaml` to version control; add it to `.gitignore`.
- Rotate long-lived access tokens for MCP and external integrations at least every 90 days.

---

## Backup and Restore

- Use the **Home Assistant Backup** integration (built-in since HA 2024.11) or the **Google Drive Backup** add-on to take daily automated backups.
- Store at least 7 days of daily backups and 4 weeks of weekly backups in an offsite location (cloud storage separate from the HA host).
- Perform a test restore to a clean HA instance at least quarterly to validate backup integrity.
- Include the backup retention policy in the project README so other household members can restore the system.

---

## Integration Management

- Prefer **native HA integrations** (configured via the UI at Settings → Devices & Services) over YAML-configured custom integrations.
- For HACS (Home Assistant Community Store) add-ons: document every installed custom integration in `docs/INTEGRATIONS.md` with purpose, version, and the reason a native integration was insufficient.
- Audit and remove unused integrations and devices at least quarterly to reduce attack surface and complexity.

---

## Blueprint vs Automation vs Script

| Type | When to Use |
|---|---|
| **Blueprint** | Reusable automation template that non-developers can instantiate with parameters (e.g., motion-triggered light with configurable timeout). |
| **Automation** | Single-use, complex automation with specific device targets that does not need to be reused. |
| **Script** | Reusable sequence of actions called by multiple automations or triggered manually via the dashboard. |

- Extract any automation logic used in more than two automations into a **Script** or **Blueprint**.
- Store Blueprint YAML files in `config/blueprints/automation/` and version-control them.

---

## Testing Automations

- Use Developer Tools → **Automation Trace** after every automation change to verify the execution path and confirm conditions behaved as expected.
- Use Developer Tools → **Template** editor to validate Jinja2 template expressions before embedding them in automations.
- Test motion-triggered and time-triggered automations by firing test events from Developer Tools → Events before relying on real hardware triggers.
- Document the expected behaviour and test scenarios for complex automations in a comment block at the top of the automation YAML.

---

## Notification Routing

Define a notification priority taxonomy and route accordingly:

| Priority | Trigger Example | Delivery Method |
|---|---|---|
| Critical | Smoke alarm, CO alarm, intrusion | Phone call + push + persistent notification |
| High | Door left open, unusual energy spike | Push notification + persistent notification |
| Normal | Arriving home, daily summary | Push notification |
| Low | Device status update, routine event | Persistent notification only |

- Implement notification routing as a HA Script with a `priority` input parameter; call it from all automations instead of hardcoding `notify.*` targets.
- Respect quiet hours: suppress non-critical notifications between 23:00 and 07:00 using a time condition.

---

## HA Version Compatibility

- Document the minimum supported Home Assistant version for any automation or integration that uses features introduced in a specific release (e.g., `# Requires HA 2024.10+`).
- Subscribe to the HA release notes and Breaking Changes blog; review before every HA core update.
- Test all automations in a development HA instance (a secondary VM or container) before applying a major HA update to the production instance.
