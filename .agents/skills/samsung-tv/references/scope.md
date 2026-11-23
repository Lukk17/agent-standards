# Scope

Companion reference for the [samsung-tv](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

The skill controls a Samsung Tizen smart TV from 2016 on through Home Assistant, with read-only checks against its local REST API: launching apps with a Home Assistant REST command, confirming app IDs, turning it on with a guarded power key, voice assistant scripts and casting a dashboard.

- Launching an app on the TV from Home Assistant, a script or an automation
- Finding or confirming the app ID of Netflix, YouTube, Disney+, Spotify or any other TV app
- Turning the TV on or off from Home Assistant, or a TV entity that offers no turn on
- Writing a voice assistant script that opens a TV app
- Casting a Home Assistant dashboard view to the TV
- Reading the TV's network type, MAC address or Frame support without touching its settings
- The user says "open Netflix on the TV", "find the Disney+ app ID", "the TV does not turn on from Home Assistant", "show a dashboard on the TV", "which Netflix ID works on my TV", "the app script runs but nothing opens", "Wake on LAN stopped working after the update" or "can Ambient Mode show my dashboard"

---

### When not to activate

- Home Assistant YAML style, automation modes, secrets and backups in general, use `home-assistant`
- The Docker VM, its Compose stack and its services, use `homelab-services`
- The router, its DHCP leases and its Wi-Fi, use `asus-router`
- SmartThings appliances such as a washer or a fridge, which this skill does not cover
- Judging whether the TV's open ports or the token are acceptable, use the `security-auditor` agent

---

### Related skills

- `home-assistant` owns automation and script style, modes, secrets and backups
- `homelab-services` owns the VM and the services that run beside Home Assistant
- `asus-router` owns the router that hands the TV its address
- The `home-assistant-engineer` agent owns building and changing the Home Assistant configuration
- The `security-auditor` agent owns judging exposed ports and tokens
