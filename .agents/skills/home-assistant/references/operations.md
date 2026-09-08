# Home Assistant operations

Running the instance rather than writing automations for it: backups, integration hygiene, notification routing, and
upgrade discipline. The automation and YAML rules live in [SKILL.md](../SKILL.md).

---

### Backup and restore

Use the built-in Backup integration or the Google Drive Backup add-on to take daily automated backups.

- Keep at least 7 daily backups and 4 weekly backups offsite, on storage separate from the Home Assistant host. A
  backup on the same SD card as the instance protects against nothing that actually happens to these boxes.
- Perform a test restore to a clean instance at least quarterly. An untested backup is a hypothesis.
- Write the retention policy into the project README, so another member of the household can restore the system
  without reverse-engineering it.

---

### Integration management

Prefer a native integration configured through Settings, Devices and Services over a YAML-configured custom one. A
config entry is validated on save and travels in the backup, a YAML block is neither.

For every HACS custom integration, record in `docs/INTEGRATIONS.md`:

| Field | Why it is there |
|---|---|
| Purpose | What breaks if it is removed |
| Version | What a restore has to reinstall |
| Why not native | Whether a later core release has made it redundant |

Audit and remove unused integrations and devices at least quarterly. Every integration is a code path that runs on
every restart and a surface that can break an upgrade.

---

### Notification routing

Define a priority taxonomy once and route through it, so an automation never hardcodes a `notify.*` target.

| Priority | Trigger example | Delivery |
|---|---|---|
| Critical | Smoke alarm, CO alarm, intrusion | Phone call plus push plus persistent notification |
| High | Door left open, unusual energy spike | Push plus persistent notification |
| Normal | Arriving home, daily summary | Push notification |
| Low | Device status update, routine event | Persistent notification only |

Implement the taxonomy as a script taking a `priority` input, and call that script from every automation. Suppress
non-critical notifications between 23:00 and 07:00 with a time condition inside the script, so quiet hours are
enforced in one place rather than remembered in twenty.

Respect the Companion App limit of 150 notifications per 24 hours. Handle `HTTP 429` from the REST API with
exponential backoff in any external script or MCP client.

---

### Blueprint, automation, or script

| Type | When to use |
|---|---|
| Blueprint | A reusable template someone non-technical instantiates with parameters, for example motion light with a configurable timeout |
| Automation | A single-use trigger-condition-action with specific targets that will not be reused |
| Script | A reusable action sequence called by several automations or run from a dashboard |

Anything used in more than two automations becomes a script or a blueprint. Store blueprints in
`config/blueprints/automation/` and keep them in version control.

---

### Test before you trust

Open Developer Tools, Automation Trace after every change and confirm the execution path and each condition result.
Validate Jinja2 in the Template editor before embedding it. Fire the trigger from Developer Tools, Events rather
than waiting for real hardware, and record the expected behaviour and the test scenarios at the top of any complex
automation file.

Pass:

```yaml
service: automation.trigger
target:
  entity_id: automation.hallway_light_on_motion
data:
  skip_condition: false
```

Fail, `skip_condition` defaults to true, so this proves the actions run and nothing about the conditions:

```yaml
service: automation.trigger
target:
  entity_id: automation.hallway_light_on_motion
```

---

### Upgrade discipline

- Document the minimum supported core version for any automation using a feature from a specific release, as a
  comment at the top of the automation file.
- Read the release notes and the breaking changes list before every core update. The monthly train ships breaking
  changes regularly and they are always listed.
- Test automations on a development instance, a secondary VM or container, before applying a major update to the
  production instance.
- Take a backup immediately before the upgrade, not on the previous night's schedule.
