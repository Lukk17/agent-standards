---
name: homelab-services
description: 'Running a Docker Compose homelab on one VM, every change asked of the owner first: AdGuard Home, Uptime Kuma, Telegraf, Samba, File Browser, Plex, Homepage, Nginx Proxy Manager, a local CA for .internal names, and data disks. Use when the user says "add a .internal name", "https for the .internal names", "deploy the compose change" or "the VM disk is full". Not for the Proxmox host, use `proxmox`.'
---

# Homelab Services

How an agent runs and repairs a small self-hosted stack: one Ubuntu Server VM, one Compose file, and the services a home network leans on, DNS first. The Compose file and the files it mounts live in a git clone on the owner's machine, and the VM holds a plain copy. Every change to a server, a service or the router is proposed to the owner first, with what can go wrong and how to undo it, and nothing changes before a yes.

Written for AdGuard Home 0.107, Uptime Kuma 2, Telegraf 1, Samba 4, File Browser 2 (`gtstef/filebrowser`), Plex Media Server, Homepage 1 and Nginx Proxy Manager 2 as containers on an Ubuntu Server VM under Proxmox VE, with OpenSSL 3 in a throwaway container for the local CA. Facts carry a VERIFIED or UNVERIFIED mark, explained in [conventions.md](references/conventions.md#verification-marks).

| You are about to | Open |
|---|---|
| Name a host, user, folder or container: setup facts live in the owner's notes, examples use `<placeholders>`. Or judge a VERIFIED mark | [conventions.md](references/conventions.md) |
| Copy a change to the VM, start a service, create its folders, cap container logs, write a `$` into Compose | [deploy-and-logs.md](references/deploy-and-logs.md) |
| Change AdGuard Home rewrites, upstreams, retention, ignored domains, or `AdGuardHome.yaml` | [adguard-home.md](references/adguard-home.md) |
| Change Uptime Kuma monitors, `/metrics`, the labelset log flood, or its database | [uptime-kuma.md](references/uptime-kuma.md) |
| Run or read the Telegraf ping, DNS, HTTP and speed probes and their CSV files | [telegraf-network-watch.md](references/telegraf-network-watch.md) |
| Set up the Samba share and its login file | [samba.md](references/samba.md) |
| Set up File Browser, read or reset its admin password | [file-browser.md](references/file-browser.md) |
| Run, claim and lay out Plex with read-only media | [plex.md](references/plex.md) |
| Configure the Homepage dashboard and its allowed hosts | [homepage.md](references/homepage.md) |
| Add a proxy host for a `.internal` name, or fix one that answers 500 | [nginx-proxy-manager.md](references/nginx-proxy-manager.md) |
| Give `.internal` names `https`: make, extend, renew, trust or revoke the local CA | [local-ca.md](references/local-ca.md) |
| Attach, mount and protect a USB or NTFS data disk, or clear a dirty NTFS volume | [data-disk.md](references/data-disk.md) |
| Explain a full disk, find what filled it, free space | [disk-full.md](references/disk-full.md) |

---

### When to activate

- Adding a service to the stack, or copying a changed Compose file or Telegraf config to the VM
- A `.internal` name that does not resolve, or does not reach its service
- Changing how long AdGuard Home keeps its query log or statistics
- Changing monitors in Uptime Kuma, or a container log that grows by gigabytes
- Reading the network watch files after an internet drop
- Attaching a data disk, sharing it over Samba and File Browser, or pointing Plex at it
- A VM whose root file system is full, or services that stopped writing
- The user says "keep 30 days of query log", "change the monitor interval", "Added label is not included in initial labelset" or "mount the NTFS disk"

---

### When not to activate

- The Proxmox host, its API token, or growing the VM's virtual disk and its LVM volume, use `proxmox`
- Syncthing itself, its folders, devices and its disk space error, use `syncthing`
- The router, its DHCP DNS setting, its log and WAN drops, use `asus-router`
- Writing a Dockerfile, choosing a base image or designing a Compose stack in general, use `docker-patterns`
- Judging an exposed port, a token or a password policy, use the `security-auditor` agent
- Checking the health of the owner's own computer, use `machine-health`

---

### Hard rules

The reason behind each rule is in [conventions.md](references/conventions.md#hard-rules-with-their-reasons).

1. Ask before every change on the VM, a service, the Proxmox host or the router: a file edit, a restart, a stop, a `docker compose up -d`, a mount, an `fstab` line, a package. Say what changes, the worst case and how to undo it, then wait for a yes. One yes covers one change. Reading is free.
2. The git clone is the source of truth: change it first, copy to the VM with `scp`. Never change only the VM copy, never fetch from a GitHub raw link.
3. Every service carries a `json-file` log limit, `max-size` and `max-file`, and older containers are recreated to pick it up.
4. Create every mounted folder as the login user before the first start. A data disk mount uses `create_host_path: false` and an empty mount point with `chattr +i`.
5. Back up a configuration file or database before editing it, in the topic file's order: AdGuard Home edit then restart, Uptime Kuma stop then edit.
6. Lowering the AdGuard Home query log interval deletes old queries at the next start or hourly check, for good. Say so, offer a copy of both log files first, and wait for a yes.
7. Restart Uptime Kuma after creating a tag.
8. Secrets live in `.env` beside the Compose file, mode 600, entered hidden, checked by length, never printed or committed. The agent's own credentials live in an env file outside every repository, mode 600, read one key at a time with `grep` and `cut`, never sourced or printed.
9. Never mount NTFS with `force`. Clear a dirty volume with `ntfsfix -d` after the owner says yes, or check it in Windows.
10. Probes and monitors target an address and port, never a `.internal` name.
11. The local CA is name-constrained to `DNS:internal`, its key only on the owner's computer and in the VM's `.env`. Once its include serves `https`, every proxy host's SSL tab stays on None.

---

### Related skills

- `proxmox` owns the host, attaching a disk to the VM, and growing the VM's disk, partition and LVM volume
- `syncthing` owns Syncthing in its container, including the folder that carries the network watch files
- `asus-router` owns the router's DHCP DNS server setting and reading WAN drops from its log
- `docker-patterns` owns Compose and image design in general
- The `security-auditor` agent owns judging exposed ports, tokens and passwords
- `bash` owns scripts that wrap these commands

---

### Checklist

The commands behind each item are in [conventions.md](references/conventions.md#checklist-with-its-commands).

- [ ] Changed in the clone, copied with `scp`, then `docker compose pull`, `up -d` and `ps`
- [ ] A container whose mounted file changed was restarted, Telegraf above all
- [ ] Every service has `max-size` and `max-file`, containers recreated once after
- [ ] Every mounted folder existed before the first start, owned by the login user
- [ ] Config or database backed up before the edit, value read back after
- [ ] A lower query log interval approved after the owner heard old queries go for good
- [ ] Uptime Kuma restarted after a new tag, and its log shows no `PROMETHEUS` lines
- [ ] `.env` is mode 600, values checked by length, nothing secret printed
- [ ] Data disk mounted by UUID with `nofail`, mount point `chattr +i`, `findmnt` shows it
- [ ] `df -h /` read after any change that writes data, largest container logs checked
- [ ] Local CA read back with `CA:TRUE, pathlen:0`, `Permitted: DNS:internal`, both exclusions, and `ca.key` in no repository
- [ ] Every proxied `.internal` name in `INTERNAL_DNS_NAMES`, every SSL tab on None, proxy restarted after a new certificate
- [ ] The certificate `notAfter=` date is more than 30 days away, or the job ran again
