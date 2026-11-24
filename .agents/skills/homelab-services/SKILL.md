---
name: homelab-services
description: 'A Docker Compose homelab on one VM, each change asked of the owner first: DNS, shares, a proxy, a CA. Use when the user says "add a .internal name" or "the VM disk is full". Not for the Proxmox host, use `proxmox`.'
metadata:
  version: "1.1.0"
---

# Homelab Services

How an agent runs and repairs a small self-hosted stack: one Ubuntu Server VM, one Compose file, and the services a home network leans on, DNS first. Every change to a server, a service or the router is proposed to the owner first, with what can go wrong and how to undo it, and nothing changes before a yes. The rules here hold for every service unless a rule names one, and any other rule for one service is in that service's reference. Setup facts live in the owner's notes, and examples use `<placeholders>`.

---

### When not to activate

- The Proxmox host, its API token, or growing the VM's virtual disk and its LVM volume, use `proxmox`
- Syncthing itself, its folders, devices and its disk space error, use `syncthing`
- The router, its DHCP DNS setting, its log and WAN drops, use `asus-router`

---

### Hard rules

1. Ask before every change on the VM, a service, the Proxmox host or the router: a file edit, a restart, a stop, a `docker compose up -d`, a mount, an `fstab` line, a package. Say what changes, the worst case and how to undo it, then wait for a yes. One yes covers one change. Reading is free.
2. The git clone is the source of truth: change it first, copy to the VM with `scp`. Never change only the VM copy, never fetch from a GitHub raw link.
3. Every service carries a `json-file` log limit.
4. Create every mounted folder as the login user before the first start.
5. Back up a configuration file or database before editing it, in the topic file's order.
6. Lowering the AdGuard Home query log interval deletes old queries at the next start or hourly check, for good. Say so, offer a copy of both log files first, and wait for a yes.
7. Secrets live in `.env` beside the Compose file, mode 600, entered hidden, checked by length, never printed or committed. The agent's own credentials live in an env file outside every repository, mode 600, read one key at a time with `grep` and `cut`, never sourced or printed. The local CA key stays only on the owner's computer and in the VM's `.env`.
8. Never mount NTFS with `force`. Clear a dirty volume with `ntfsfix -d` after the owner says yes, or check it in Windows.
9. Probes and monitors target an address and port, never a `.internal` name.

---

### Reference files

| You are about to | Open |
|---|---|
| Name a host, user, folder or container, judge a VERIFIED mark, or need the reason behind a hard rule | [conventions.md](references/conventions.md) |
| Copy a change to the VM, start a service, create its folders, cap container logs, write a `$` into Compose | [deploy-and-logs.md](references/deploy-and-logs.md) |
| Change AdGuard Home rewrites, upstreams, retention or `AdGuardHome.yaml` | [adguard-home.md](references/adguard-home.md) |
| Change Uptime Kuma monitors, `/metrics`, a tag, the labelset log flood, or its database | [uptime-kuma.md](references/uptime-kuma.md) |
| Run or read the Telegraf network probes and their CSV files | [telegraf-network-watch.md](references/telegraf-network-watch.md) |
| Set up the Samba share and its login file | [samba.md](references/samba.md) |
| Set up File Browser or reset its admin password | [file-browser.md](references/file-browser.md) |
| Run, claim and lay out Plex with read-only media | [plex.md](references/plex.md) |
| Configure the Homepage dashboard and its allowed hosts | [homepage.md](references/homepage.md) |
| Add a proxy host for a `.internal` name, or fix one that answers 500 | [nginx-proxy-manager.md](references/nginx-proxy-manager.md) |
| Give `.internal` names `https`: make, extend, renew, trust or revoke the local CA | [local-ca.md](references/local-ca.md) |
| Attach, mount and protect a data disk, or clear a dirty NTFS volume | [data-disk.md](references/data-disk.md) |
| Explain a full disk and free space | [disk-full.md](references/disk-full.md) |
| Before calling the work done | [checklist.md](references/checklist.md) |
