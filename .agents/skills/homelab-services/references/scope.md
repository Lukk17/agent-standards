# Scope

Companion reference for the [homelab-services](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Adding a service, or copying a changed Compose file or Telegraf config to the VM
- A `.internal` name that does not resolve, or does not reach its service
- Changing how long AdGuard Home keeps its query log or statistics
- Changing monitors in Uptime Kuma, or a container log that grows by gigabytes
- Reading the network watch files after an internet drop
- Attaching a data disk, sharing it over Samba and File Browser, or pointing Plex at it
- A VM whose root file system is full, or services that stopped writing
- The user says "add a .internal name", "https for the .internal names", "deploy the compose change", "the VM disk is full", "keep 30 days of query log", "change the monitor interval", "Added label is not included in initial labelset" or "mount the NTFS disk"

---

### When not to activate

- The Proxmox host, its API token, or growing the VM's virtual disk and its LVM volume, use `proxmox`
- Syncthing itself, its folders, devices and its disk space error, use `syncthing`
- The router, its DHCP DNS setting, its log and WAN drops, use `asus-router`
- Writing a Dockerfile, choosing a base image or designing a Compose stack in general, use `docker-patterns`
- Judging an exposed port, a token or a password policy, use the `security-auditor` agent
- Checking the health of the owner's own computer, use `machine-health`

---

### Related skills

- `proxmox` owns the host, attaching a disk to the VM, and growing the VM's disk, partition and LVM volume
- `syncthing` owns Syncthing in its container, including the folder that carries the network watch files
- `asus-router` owns the router's DHCP DNS server setting and reading WAN drops from its log
- `docker-patterns` owns Compose and image design in general
- The `security-auditor` agent owns judging exposed ports, tokens and passwords
- `bash` owns scripts that wrap these commands
