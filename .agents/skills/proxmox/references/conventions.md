# Conventions

Contents:

- [Facts about one setup](#facts-about-one-setup)
- [Verification](#verification)
- [Topics covered](#topics-covered)

Companion reference for the [proxmox](../SKILL.md) skill. Load it before writing a command or a note that names a host, a node, a VM or a storage, and when judging how far to trust a command in the topic files.

---

### Facts about one setup

Host names, node names, VM IDs, storage names beyond the installer defaults, and LAN addresses of a real setup belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md`, never in this skill and never in a shared repository. Every example uses placeholders in angle brackets: `<proxmox-host>`, `<node>`, `<vm-id>`, `<storage>`, `<user>@<realm>`, `<token-id>`.

---

### Verification

The skill is written for Proxmox VE 8 and 9, from the `qm` and `pveum` manual pages, the admin guide sources, the wiki and the API schema. No agent executed a Proxmox command for this skill, because no Proxmox host may be touched for a test. The owner ran the admin token commands in [api-access.md](api-access.md) on a Proxmox VE 8 host and measured what the token holds. Every other command is UNVERIFIED unless a topic file says otherwise. API paths and the permission each one needs were checked against the API schema of the API viewer. The tokens, roles and API calls in [api-access.md](api-access.md) were also checked against the Proxmox VE 8 sources, and that file lists what differs between 8 and 9. The other topic files were checked against 9 only.

---

### Topics covered

The skill also covers the main access option, an admin token for a user of its own, PVEAdmin on / and a custom Sys.AccessNetwork role on the node for ISO downloads, made with pveum or in the web page, narrower tokens as alternatives, the secret in an env file outside any repository, curl with a pinned certificate, listing nodes, VMs and storage use, creating and deleting VMs, growing a VM disk and the partition and file system in a Linux or Windows guest, the free space Ubuntu Server leaves in its volume group, snapshots, vzdump backups and backup jobs, and LVM thin pool data and metadata use.
