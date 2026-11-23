# Scope

Companion reference for the [asus-router](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Giving an agent SSH access to an ASUS router, or taking it back
- Reading the router's system log, its WAN state or its uptime
- An internet connection that drops now and then, and the question of whose fault it is
- An ISP optical terminal or modem whose web page cannot be reached from the LAN
- A change on the router that the owner asked for, such as a persistent ONT route on Merlin
- Also covers stock Asuswrt on Wi-Fi 6 and 6E models such as the GT-AX6000, and Asuswrt-Merlin where it differs. SSH on the LAN only with an ed25519 key and no password login, the env file keys ASUS_ROUTER_SSH, ASUS_ROUTER_SSH_PORT and HOMELAB_SSH_KEY, taking the key back, the system log in /tmp/syslog.log or /jffs/syslog.log, WAN link, PPPoE and DHCP lines in the log, nvram get for the WAN type and interfaces, the WAN port link, ping from the router, reaching the ONT page from the LAN while the WAN runs PPPoE, and telling a WAN link drop from an ISP outage
- The user says "let the agent into my router", "read the router log", "why does the internet drop", "is the WAN PPPoE or DHCP", "I cannot open the ONT page" or "was it the cable or the ISP"

---

### When not to activate

- A Proxmox host or a virtual machine behind the router, use `proxmox`
- A service inside the home lab, such as Home Assistant or Syncthing, use `home-assistant` or `syncthing`
- The network settings of one client machine, use `windows`, `macos`, `arch-linux` or `cachyos`
- Judging whether an open port, a key or a firewall rule is acceptable, use the `security-auditor` agent
- A script that wraps these commands on the agent's own machine, use `bash` or `powershell`

---

### Related skills

- `proxmox` owns the Proxmox host and its virtual machines behind the router
- `home-assistant` owns Home Assistant, which can also watch the router
- The `security-auditor` agent owns judging an exposed port, a key or a firewall rule
- `bash` and `powershell` own scripts on the agent's machine that wrap these commands
- `windows`, `macos`, `arch-linux` and `cachyos` own the client machines on the LAN
