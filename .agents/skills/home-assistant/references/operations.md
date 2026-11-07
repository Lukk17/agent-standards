# Home Assistant operations

Contents:

- [Backup and restore](#backup-and-restore)
- [Which recovery path](#which-recovery-path)
- [What needs the owner's yes every time](#what-needs-the-owners-yes-every-time)
- [What an archive holds](#what-an-archive-holds)
- [Integration management](#integration-management)
- [YAML-only integrations](#yaml-only-integrations)
- [Notification routing](#notification-routing)
- [Blueprint, automation, or script](#blueprint-automation-or-script)
- [Test before you trust](#test-before-you-trust)
- [Upgrade discipline](#upgrade-discipline)

Running the instance rather than writing automations for it: backups and recovery, integration hygiene, notification routing, and upgrade discipline. The automation and YAML rules live in [SKILL.md](../SKILL.md).

VERIFIED means read in the Home Assistant documentation source, github.com/home-assistant/home-assistant.io on branch `current`, or in Core source, home-assistant/core on branch `dev`, in the file named. UNVERIFIED means taken from the best-practices skill that the ha-mcp server ships, `home-assistant-best-practices` in homeassistant-ai/skills, and not checked against a primary source.

---

### Backup and restore

Use the built-in Backup integration for automatic backups. Run them weekly and keep 4 copies. A home install does not need daily backups.

- Before every update (Core, OS, apps, firmware), every integration removal, every device or entity deletion, and any other change that writing the old value back cannot undo, take a manual full backup first.
- Download that manual backup to the owner's computer as a second copy. Keep it encrypted as stored, set the file to mode 600, and confirm the file size and that `backup.json` inside the archive says `protected`. A backup that exists only on the Home Assistant host protects against nothing that happens to that host, such as a failed disk. The download call decrypts the archive on the way out when the caller passes the backup password, and sends it as stored otherwise. VERIFIED, `homeassistant/components/backup/http.py`, which reads a `password` query and decrypts only when one is given for a protected backup. Whether a given UI download passes it is UNVERIFIED, which is why the `protected` check stays. A decrypted copy holds `.storage` in clear text, with every token and key in it.
- An encrypted backup restores only with its encryption key from the backup emergency kit, so an archive whose key is lost is not a recovery point. Keep the archive and the emergency kit apart, as two separate secrets. VERIFIED that the emergency kit exists, `source/_integrations/backup.markdown`.
- An automatic off-machine copy, to a network share or Home Assistant Cloud, is the owner's choice, not a requirement.
- Perform a test restore to a clean instance at least quarterly. An untested backup is a hypothesis.
- Write the retention policy into the project README, so another member of the household can restore the system without reverse-engineering it.
- A backup taken after the destructive step holds the damage. With a weekly schedule the newest scheduled backup can be almost a week old, so it never stands in for the manual one taken right before.
- A `/config` folder kept in git is no backup. It leaves out the recorder database, `.storage` and `secrets.yaml`, which hold exactly what a registry deletion, an integration removal or an upgrade destroys. A repository that does track `.storage` carries clear-text tokens into every clone. UNVERIFIED for what such a repository usually leaves out.

---

### Which recovery path

Pick the narrowest path that undoes the fault. UNVERIFIED, from the ha-mcp skill's backup reference.

| What went wrong | Undo it with |
|---|---|
| One automation, script, scene, dashboard or helper edit | Write back the definition read before the edit, through the same config API. No restart, nothing else touched |
| Several such edits in one session | The same, one object at a time |
| A device, entity or area deleted from the registry | A full restore, because registry IDs, areas, labels and the references to them do not come back by writing a definition |
| An integration or config entry removed | A full restore, its entities went with it |
| An app update or removal broke something | A partial restore of that app and its data, on Home Assistant OS or Supervised only |
| A Core or OS upgrade broke the instance, or it no longer starts | A full restore |

1. Read the current definition of every object before editing it. That copy is the cheapest undo there is, and it is what makes the first two rows possible.
2. A partial restore needs the Supervisor, so it exists only on Home Assistant OS and Supervised. A Container or Core install has object rollback and a full restore only. Check the install type before offering it.
3. A partial restore that includes the Home Assistant settings still restarts Home Assistant.
4. After any restore, check that entities are not `unavailable`, that the log shows no startup failures, and that cloud integrations do not need to sign in again, because the restore replays tokens that may have been rotated since.

---

### What needs the owner's yes every time

Restoring a backup, deleting a backup, and upgrading Core or the OS each wait for the owner's yes, every time, even when a backup exists. A backup lowers the risk, it does not give permission. When asking, say which one it is and what it does. UNVERIFIED as a vendor rule, and in line with the global rule to ask before anything destructive.

1. A restore throws away every change since that archive, in every part it holds, and restarts Home Assistant.
2. Deleting a backup destroys a recovery point. The retention cleanup of a schedule keeps a count of copies, but deleting one named backup by hand has no last-copy guard. UNVERIFIED for the missing guard. Name the backup and its age, keep at least one recent backup whose key is at hand, and delete the oldest first.
3. An upgrade can break integrations and custom components, and its way back is the backup taken right before it.
4. Before an action that has no inverse, such as a `*.press`, `vacuum.send_command` or a notification, or one whose inverse does not undo the effect, such as `lock.unlock` followed by `lock.lock`, treat it as irreversible and ask first. A `light.turn_on` with brightness or colour is undone only by a `scene.create` snapshot taken before it.

---

### What an archive holds

1. What a backup holds is chosen per backup: the Home Assistant settings (the config folder, including `.storage`), the recorder database, apps with their data, and the folders `share`, `addons/local`, `ssl` and `media`. A restore overwrites only the parts that backup holds. UNVERIFIED for the folder list.
2. The recorder database is in by default. VERIFIED, `homeassistant/components/backup/config.py`, `include_database: bool = True`. It can still be left out of one backup, excluded by default on a Supervisor install, or live in an external database outside the archive, so check before telling the owner that history comes back.
3. Home Assistant calls the add-ons apps now: "Apps are separate applications that run alongside Home Assistant", under Settings, Apps. VERIFIED, `source/_docs/apps-and-integrations.markdown`. Use the word apps with the owner.

---

### Integration management

Prefer a native integration configured through Settings, Devices and Services over a YAML-configured custom one. A config entry is validated on save and travels in the backup, a YAML block is neither.

For every HACS custom integration, record in `docs/INTEGRATIONS.md`:

| Field | Why it is there |
|---|---|
| Purpose | What breaks if it is removed |
| Version | What a restore has to reinstall |
| Why not native | Whether a later core release has made it redundant |

Audit and remove unused integrations and devices at least quarterly. Every integration is a code path that runs on every restart and a surface that can break an upgrade. Removing one is irreversible, so it follows the backup and the yes above.

Point the owner to Settings, Devices and services for an integration that has a config flow, never to `configuration.yaml`. Most integrations are set up in the UI. UNVERIFIED as a count, VERIFIED that the UI path is the standard one, `source/_docs/apps-and-integrations.markdown`.

---

### YAML-only integrations

Some integrations still have no config flow, such as `command_line`, `rest`, `shell_command`, platform-style `mqtt`, YAML `group:` blocks and trigger-based `template:` entities. Edit their YAML this way. UNVERIFIED for the list.

1. Keep a copy of the file before the edit, so writing it back is the undo.
2. Run `homeassistant.check_config` before applying anything. VERIFIED that the action exists, `source/_actions/homeassistant.check_config.markdown`.
3. Apply with the integration's own reload action, such as `template.reload` or `command_line.reload`, which touches only that integration.
4. Platform-style YAML with no reload action needs `homeassistant.restart`, which interrupts every automation and integration, so it needs the owner's yes first.
5. Automations, scripts, scenes and helpers are never written this way. They go through the config API, which validates them, and `.storage/` is never written at all.

---

### Notification routing

Define a priority taxonomy once and route through it, so an automation never hardcodes a `notify.*` target.

| Priority | Trigger example | Delivery |
|---|---|---|
| Critical | Smoke alarm, CO alarm, intrusion | Phone call plus push plus persistent notification |
| High | Door left open, unusual energy spike | Push plus persistent notification |
| Normal | Arriving home, daily summary | Push notification |
| Low | Device status update, routine event | Persistent notification only |

Implement the taxonomy as a script taking a `priority` input, and call that script from every automation. Suppress non-critical notifications between 23:00 and 07:00 with a time condition inside the script, so quiet hours are enforced in one place rather than remembered in twenty.

Respect the Companion App push limit of 500 notifications per day per device, which resets at midnight UTC and does not count critical alerts or notification commands. VERIFIED, home-assistant/companion.home-assistant, `docs/notifications/details.md`, section "Rate limiting". Handle `HTTP 429` from the REST API with exponential backoff in any external script or MCP client.

---

### Blueprint, automation, or script

| Type | When to use |
|---|---|
| Blueprint | A reusable template someone non-technical instantiates with parameters, for example motion light with a configurable timeout |
| Automation | A single-use trigger-condition-action with specific targets that will not be reused |
| Script | A reusable action sequence called by several automations or run from a dashboard |

Anything used in more than two automations becomes a script or a blueprint. Store blueprints in `config/blueprints/automation/` and keep them in version control.

---

### Test before you trust

Open the automation's trace in the automation editor after every change and confirm the execution path and each condition result. Validate Jinja2 in the Template tab of Settings, Tools before embedding it. Fire the trigger from the Events tab of the same page rather than waiting for real hardware, and record the expected behaviour and the test scenarios at the top of any complex automation file, or in its `description:` when the automation is kept in the UI editor. VERIFIED that the page is Settings, Tools, `source/_docs/tools/dev-tools.markdown`: "To open Tools, go to Settings > Tools." Older releases call it Developer Tools.

Pass:

```yaml
action: automation.trigger
target:
  entity_id: automation.hallway_light_on_motion
data:
  skip_condition: false
```

Fail, `skip_condition` defaults to true, so this proves the actions run and nothing about the conditions. VERIFIED, `source/_actions/automation.trigger.markdown`, `default: true`:

```yaml
action: automation.trigger
target:
  entity_id: automation.hallway_light_on_motion
```

---

### Upgrade discipline

- Read the instance version before choosing a feature that arrived in a given release: `version` in `GET /api/config`, or Settings, About. VERIFIED, `src/content/docs/core/internals/rest-api.md` in home-assistant/contributors.home-assistant.io, published at https://contributors.home-assistant.io/core/internals/rest-api/, section "GET /api/config": "Returns the core configuration: location, units, time zone, version, loaded components, and more." When the instance has the feature, use it and do not offer the older way as an equal choice. When the version cannot be read, name the release the feature needs.
- Document the minimum supported core version for any automation using a feature from a specific release, as a comment at the top of the automation file.
- Read the release notes and the breaking changes list before every core update. The monthly train ships breaking changes regularly and they are always listed.
- Test automations on a development instance, a secondary VM or container, before applying a major update to the production instance.
- Take a manual full backup immediately before the upgrade, as "Backup and restore" describes, rather than relying on the last scheduled one.
