# Scope

Companion reference for the [proxmox](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Giving an agent or a script access to a Proxmox VE host
- Listing nodes, VMs, a VM's hardware, or storage use
- A guest that runs out of disk space, or a resize that the guest does not show
- Snapshotting or backing up a Proxmox VM before a risky change inside the guest
- Letting the agent create or delete VMs
- Judging whether `local-lvm` or another thin pool is close to full
- The user says "give the agent access to Proxmox", "let the agent manage my VMs", "list my VMs", "grow the disk of this VM", "the guest still shows the old size", "snapshot this VM first", "back up this VM" or "how full is local-lvm"

---

### When not to activate

- Software inside a guest, use the skill for that guest's operating system or application, such as `syncthing`, `docker-patterns` or `home-assistant`
- The services running inside a VM, such as the proxy, the dashboard, DNS or monitoring, use `homelab-services`
- Provisioning many VMs reproducibly, use `ansible`
- Writing a script that wraps these calls, use `bash` or `powershell`
- Judging whether a token, an exposed port or a firewall rule is acceptable, use the `security-auditor` agent

---

### Related skills

- `syncthing` owns Syncthing inside a guest, including its disk space error, which often leads here
- `home-assistant` owns Home Assistant OS once it runs in a VM
- `docker-patterns` owns containers inside a guest
- `windows` owns the Windows guest beyond Disk Management and `Resize-Partition`
- The `security-auditor` agent owns judging tokens, roles and exposed ports
- `bash` and `powershell` own scripts that wrap these calls
