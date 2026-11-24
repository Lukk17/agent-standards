---
name: proxmox
description: 'Proxmox VE, each change asked of the owner first: tokens, VMs, disks, backups. Use when the user says "give the agent access to Proxmox" or "grow the disk of this VM". Not for services in a VM, use `homelab-services`.'
metadata:
  version: "1.1.0"
---

# Proxmox VE Administration

How an agent works on a Proxmox VE host through the API, and how a change the owner approved is done in the right order. Written for Proxmox VE 8 and 9. Setup facts belong in the owner's notes, never here, and examples use `<placeholders>`.

---

### When not to activate

- The services running inside a VM, such as the proxy, the dashboard, DNS or monitoring, use `homelab-services`
- Software inside a guest, use the skill for that guest's operating system or application, such as `syncthing`, `docker-patterns` or `home-assistant`
- Provisioning many VMs reproducibly, use `ansible`

---

### Hard rules

1. The agent works through the API with a token on a user of its own: the admin token in [admin-token.md](references/admin-token.md), or one of the narrower alternatives in [narrower-tokens.md](references/narrower-tokens.md) when the owner chose one. The agent never gets a password, never logs in to the web page, and never uses `root@pam`.
2. Each token secret lives in an env file the owner fills, outside every repository, readable only by the owner, mode 600 on Linux and macOS. It is never printed, never written into the session, and never passed as a command line argument. With an alternative that keeps a separate change token, that token's file is loaded only for a change the owner approved, and only for that call.
3. TLS stays verified: `--cacert` with the cluster CA, or `-k` only together with `--pinnedpubkey`. Never `-k` alone.
4. Ask before anything that changes a VM, a storage or the host: resize, snapshot, rollback, backup, start, stop, creating a VM, uploading or downloading an ISO, a configuration change, a permission change, a package update. Say what changes, the worst case, and how to undo it, then wait for a yes. This holds with the admin token too: the token makes a change possible, it is not permission to make one, and one yes covers one change.
5. Never shrink a disk. `qm disk resize` refuses, and doing it by hand destroys the file system.
6. Before a disk change, a recent backup exists or the owner takes one. A snapshot on the same storage is not a backup.
7. Read the thin pool's data and metadata use before anything that writes to it. A full thin pool returns write errors to every guest on it.
8. A resize on the host is half the job. The partition and the file system inside the guest have to grow too, and a reboot alone does not do it.
9. Ask before every delete, one VM per yes. Name the VM by ID and name, its node, and its newest backup with the date, then wait. Deleting a VM removes its disks, and the only way back is a backup.

---

### Reference files

| You are about to | Open |
|---|---|
| Give an agent the admin token, check it or take it away, or a command differs between Proxmox VE 8 and 9 | [admin-token.md](references/admin-token.md) |
| Fill the env file, verify the certificate, call the API with curl for any read or change | [api-calls.md](references/api-calls.md) |
| Set up a narrower token the owner chose | [narrower-tokens.md](references/narrower-tokens.md) |
| Grow a VM disk on the host | [disk-resize.md](references/disk-resize.md) |
| Grow the partition and the file system in a Linux guest, or use the free space Ubuntu Server leaves | [disk-resize-linux-guest.md](references/disk-resize-linux-guest.md) |
| Extend the volume in a Windows guest | [disk-resize-windows-guest.md](references/disk-resize-windows-guest.md) |
| Take or roll back a snapshot, run a backup, read or plan a backup job | [snapshots-and-backups.md](references/snapshots-and-backups.md) |
| Read storage use, thin pool data and metadata, judge whether a pool is too full | [storage.md](references/storage.md) |
| Name a host, node, VM or storage, or judge how verified a command is | [conventions.md](references/conventions.md) |
| Before calling the work done | [checklist.md](references/checklist.md) |
