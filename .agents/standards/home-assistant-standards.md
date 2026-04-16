### AI Home Assistant MCP Development Standards

---

### Core Execution Directives

- Treat all LLM generated YAML, entity IDs, and state management logic as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every HA architectural decision.
- Append a Zero-Trust directive demanding mandatory web searches for current HA documentation, specifically regarding MCP integration, Assist API limits, and YAML schemas.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official HA documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every YAML node, automation mode, and service call provided.
- Mandate direct, working links to the official HA documentation used to ground the code.

---

### YAML Configuration Syntax

- Enforce strict 2-space indentation. [Confidence: 100%]
- Use exclusively lowercase `true` and `false` for booleans. Strictly prohibit the use of `True`, `False`, `yes`, `no`, `on`, or `off` to maintain YAML 1.2 compliance and prevent parsing errors. [Confidence: 100%]
  - Link: https://developers.home-assistant.io/docs/documenting/yaml-style-guide/
  - Quote: "avoid"
- Mandate block-style sequences and mappings. Do not use flow-style (JSON-like) syntax such as `[1, 2]` or `{key: value}` in YAML files. [Confidence: 100%]
- Wrap all string values in double quotes (`"string"`). Implicitly mark null values instead of using `~` or `null`. [Confidence: 100%]
- Prohibit generating raw YAML manually for core configurations if a UI-managed Template Helper or Config Entry is available. Always prefer UI-configured Helpers over raw `template:` YAML to ensure syntax validation and reliable backups. [Confidence: 100%]

---

### State Management and Automations

- Use `entity_id` exclusively over `device_id` in all triggers, conditions, and actions. Device IDs break silently if a device is removed and re-added to the Zigbee/Z-Wave/Wi-Fi network. [Confidence: 100%]
- Use native conditions (e.g., `numeric_state`) instead of template conditions. Native conditions are validated at load time rather than runtime, preventing silent failures. [Confidence: 100%]
- Build event-driven automations. Use `wait_for_trigger` with state triggers instead of polling the state bus with `wait_template`. [Confidence: 100%]
- Strictly prohibit direct modification of internal state files within the `.storage/` directory. The AI must use the HA REST or WebSocket API to interact with internal states to prevent database corruption. [Confidence: 100%]
- Use `mode: restart` for motion-triggered automations rather than `mode: single` to ensure lighting timers reset properly upon continuous movement. [Confidence: 100%]

---

### MCP (Model Context Protocol) Integration

- Restrict MCP LLM access strictly to explicitly exposed entities via the Home Assistant Assist API. Do not expose administrative or security entities (like locks, garage doors, or alarm panels) to the MCP client to prevent unauthorized autonomous actuation. [Confidence: 100%]
  - Link: https://www.home-assistant.io/integrations/mcp_server/
  - Quote: "Model"
- Secure the MCP server endpoint (`/api/mcp`) using a Long-Lived Access Token scoped specifically for the LLM agent, or use OAuth if the client supports it. [Confidence: 100%]
- If the MCP client (like Cursor or Claude Code local CLI) only supports `stdio` transport, explicitly define the architecture to route through an `mcp-proxy`, as HA natively implements the Streamable HTTP (SSE) protocol for its MCP server. [Confidence: 100%]

---

### API Rate Limits and Polling Constraints

- Respect local integration and external cloud API rate limits. Group state updates and avoid aggressive, high-frequency polling from the LLM. [Confidence: 100%]
- Implement conservative rate limits for external notifications (matching the HA Companion App's limit of 150 notifications per 24 hours) to prevent the AI from spamming user devices. [Confidence: 100%]
- Handle `HTTP 429 Too Many Requests` gracefully in any external scripts or MCP clients querying the HA REST API by implementing exponential backoff. [Confidence: 100%]