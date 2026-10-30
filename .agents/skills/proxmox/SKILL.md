---
name: proxmox
description: 'Working with a Proxmox VE 8 or 9 host from an agent, every change asked of the owner first: API tokens, listing VMs and storage, creating and deleting VMs, growing a guest disk, snapshots, vzdump backups and thin pools. Use when the user says "give the agent access to Proxmox", "grow the disk of this VM" or "snapshot this VM first". Not for containers inside a guest, use `docker-patterns`.'
---

# Proxmox VE Administration

How an agent works on a Proxmox VE host through the API, and how a change the owner approved is done in the right order. The main option is an admin token for a user of its own. It can create, change and delete VMs and storage content, manage storages and SDN, create users and groups but not grant permissions, and download ISO files. Narrower tokens are described as alternatives in [api-access.md](references/api-access.md). Whatever the token, anything that changes a VM, a storage or the host is proposed to the owner first, with what can go wrong and how to undo it.

Written for Proxmox VE 8 and 9, from the `qm` and `pveum` manual pages, the admin guide sources, the wiki and the API schema. No agent executed a Proxmox command for this skill, because no Proxmox host may be touched for a test. The owner ran the admin token commands in [api-access.md](references/api-access.md) on a Proxmox VE 8 host and measured what the token holds. Every other command is UNVERIFIED unless a topic file says otherwise. API paths and the permission each one needs were checked against the API schema of the API viewer. The tokens, roles and API calls in [api-access.md](references/api-access.md) were also checked against the Proxmox VE 8 sources, and that file lists what differs between 8 and 9. The other topic files were checked against 9 only.

| You are about to | Open |
|---|---|
| Give an agent the admin token or a narrower one, create a token, store the secret, call the API with curl, read nodes, VMs and storage, resize, snapshot, start or stop through the API, create or delete a VM, upload or download an ISO | [api-access.md](references/api-access.md) |
| Grow a VM disk, then the partition and the file system in a Linux or Windows guest | [disk-resize.md](references/disk-resize.md) |
| Take or roll back a snapshot, run a backup, read or plan a backup job | [snapshots-and-backups.md](references/snapshots-and-backups.md) |
| Read storage use, thin pool data and metadata, judge whether a pool is too full | [storage.md](references/storage.md) |

---

### Facts about one setup

Host names, node names, VM IDs, storage names beyond the installer defaults, and LAN addresses of a real setup belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md`, never in this skill and never in a shared repository. Every example uses placeholders in angle brackets: `<proxmox-host>`, `<node>`, `<vm-id>`, `<storage>`, `<user>@<realm>`, `<token-id>`.

---

### When to activate

- Giving an agent or a script access to a Proxmox VE host
- Listing nodes, VMs, a VM's hardware, or storage use
- A guest that runs out of disk space, or a resize that the guest does not show
- Snapshotting or backing up a Proxmox VM before a risky change inside the guest
- Letting the agent create or delete VMs
- Judging whether `local-lvm` or another thin pool is close to full
- Also covers the main access option, an admin token for a user of its own, PVEAdmin on / and a custom Sys.AccessNetwork role on the node for ISO downloads, made with pveum or in the web page, narrower tokens as alternatives, the secret in an env file outside any repository, curl with a pinned certificate, listing nodes, VMs and storage use, creating and deleting VMs, growing a VM disk and the partition and file system in a Linux or Windows guest, the free space Ubuntu Server leaves in its volume group, snapshots, vzdump backups and backup jobs, and LVM thin pool data and metadata use
- The user says "let the agent manage my VMs", "list my VMs", "the guest still shows the old size", "snapshot this VM first", "back up this VM" or "how full is local-lvm"

---

### When not to activate

- Software inside a guest, use the skill for that guest's operating system or application, such as `syncthing`, `docker-patterns` or `home-assistant`
- Provisioning many VMs reproducibly, use `ansible`
- Writing a script that wraps these calls, use `bash` or `powershell`
- Judging whether a token, an exposed port or a firewall rule is acceptable, use the `security-auditor` agent

---

### Hard rules

1. The agent works through the API with a token on a user of its own: the admin token in [api-access.md](references/api-access.md), or one of the narrower alternatives there when the owner chose one. The agent never gets a password, never logs in to the web page, and never uses `root@pam`.
2. Each token secret lives in an env file the owner fills, outside every repository, readable only by the owner, mode 600 on Linux and macOS. It is never printed, never written into the session, and never passed as a command line argument. With an alternative that keeps a separate change token, that token's file is loaded only for a change the owner approved, and only for that call.
3. TLS stays verified: `--cacert` with the cluster CA, or `-k` only together with `--pinnedpubkey`. Never `-k` alone.
4. Ask before anything that changes a VM, a storage or the host: resize, snapshot, rollback, backup, start, stop, creating a VM, uploading or downloading an ISO, a configuration change, a permission change, a package update. Say what changes, the worst case, and how to undo it, then wait for a yes. This holds with the admin token too: the token makes a change possible, it is not permission to make one, and one yes covers one change.
5. Never shrink a disk. `qm disk resize` refuses, and doing it by hand destroys the file system.
6. Before a disk change, a recent backup exists or the owner takes one. A snapshot on the same storage is not a backup.
7. Read the thin pool's data and metadata use before anything that writes to it. A full thin pool returns write errors to every guest on it.
8. A resize on the host is half the job. The partition and the file system inside the guest have to grow too, and a reboot alone does not do it.
9. Ask before every delete, one VM per yes. Name the VM by ID and name, its node, and its newest backup with the date, then wait. Deleting a VM removes its disks, and the only way back is a backup.

---

### Related skills

- `syncthing` owns Syncthing inside a guest, including its disk space error, which often leads here
- `home-assistant` owns Home Assistant OS once it runs in a VM
- `docker-patterns` owns containers inside a guest
- `windows` owns the Windows guest beyond Disk Management and `Resize-Partition`
- The `security-auditor` agent owns judging tokens, roles and exposed ports
- `bash` and `powershell` own scripts that wrap these calls

---

### Checklist

- [ ] The agent uses a token on a user of its own, the admin token or a chosen alternative, never a password or `root@pam`
- [ ] The token's permissions were checked with `pveum user token permissions` before it was handed over
- [ ] With an alternative, a change token belongs to its own user and was used only for the one change the owner approved
- [ ] Every delete had its own yes after the VM's newest backup was named
- [ ] The env file sits outside every repository, readable only by the owner
- [ ] Every curl call verifies TLS by CA file or by pinned public key, never `-k` alone
- [ ] Every change was approved by the owner after the worst case and the undo were stated
- [ ] A backup exists before a disk change, and the thin pool has room for the growth
- [ ] After a resize, the guest's partition and file system were grown and checked with `lsblk` and `df -h` or `Get-Volume`
- [ ] On an Ubuntu guest, `vgs` checked for free space before asking for a bigger virtual disk
- [ ] Thin pool data and metadata use read and reported after the change
