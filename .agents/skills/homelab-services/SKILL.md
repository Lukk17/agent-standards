---
name: homelab-services
description: 'Running a Docker Compose homelab on one VM, every change asked of the owner first: AdGuard Home, Uptime Kuma, Telegraf, Samba, File Browser, Plex, Homepage, Nginx Proxy Manager, a local CA for .internal names, and data disks. Use when the user says "add a .internal name", "https for the .internal names", "deploy the compose change" or "the VM disk is full". Not for the Proxmox host, use `proxmox`.'
---

# Homelab Services

How an agent runs and repairs a small self-hosted stack: one Ubuntu Server VM, one Compose file, and the services a home network leans on, DNS first. The Compose file and the files it mounts live in a git clone on the owner's machine, and the VM holds a plain copy. Every change to a server, a service or the router is proposed to the owner first, with what can go wrong and how to undo it, and nothing changes before a yes.

Written for AdGuard Home 0.107, Uptime Kuma 2, Telegraf 1, Samba 4, File Browser 2 (`gtstef/filebrowser`), Plex Media Server, Homepage 1 and Nginx Proxy Manager 2 as containers on an Ubuntu Server VM under Proxmox VE, with OpenSSL 3 in a throwaway container for the local CA. Facts marked VERIFIED were measured on the owner's homelab, or in throwaway containers where the mark says so. The AdGuard Home file edit and the Uptime Kuma database edit were also run end to end in throwaway containers of the same images, with no network. Each topic file names its sources. Everything else is UNVERIFIED.

| You are about to | Open |
|---|---|
| Copy a change to the VM, start a new service, create its folders, cap container logs, write a `$` into Compose | [deploy-and-logs.md](references/deploy-and-logs.md) |
| Add a DNS rewrite, set upstreams, change query log or statistics retention, ignore a domain, edit `AdGuardHome.yaml` | [adguard-home.md](references/adguard-home.md) |
| Set monitor intervals, read `/metrics` with the API key, stop the labelset log flood, edit monitors in the database | [uptime-kuma.md](references/uptime-kuma.md) |
| Run the ping, DNS, HTTP and speed probes, read or rotate the CSV files, judge the speed test traffic | [telegraf-network-watch.md](references/telegraf-network-watch.md) |
| Set up the Samba share and its login file | [samba.md](references/samba.md) |
| Set up File Browser, read its first admin password, reset it | [file-browser.md](references/file-browser.md) |
| Run Plex, claim it, mount the media read only, lay out the libraries | [plex.md](references/plex.md) |
| Configure the Homepage dashboard and its allowed hosts | [homepage.md](references/homepage.md) |
| Add a proxy host for a `.internal` name, forward to a host-network service or the Proxmox web UI, a proxy host that answers 500 | [nginx-proxy-manager.md](references/nginx-proxy-manager.md) |
| Give the `.internal` names `https`, make or replace the local CA, add a name to its certificate, renew it, trust the CA on a device, revoke it | [local-ca.md](references/local-ca.md) |
| Attach a USB or NTFS data disk to the VM, mount it, protect the mount point, clear a dirty NTFS volume | [data-disk.md](references/data-disk.md) |
| Explain a full disk, find what filled it, free space | [disk-full.md](references/disk-full.md) |

---

### Facts about one setup

Addresses, host names, user names, the path of the stack folder on the VM, and the names of real monitors and shares belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md` or the repository that holds the Compose file, never in this skill. Every example uses placeholders in angle brackets: `<vm-ip>`, `<user>`, `<stack-dir>`, `<clone-dir>` for the folder of the clone that holds the Compose file, `<uuid>`, `<disk-id>`. Container names are the usual service names, `adguard-home`, `uptime-kuma`, `telegraf`, `samba`, `filebrowser`, `plex`, `homepage` and `nginx-proxy-manager`. Read the real ones with `docker ps --format '{{.Names}}'` and use those.

---

### When to activate

- Adding a service to the stack, or copying a changed Compose file or Telegraf config to the VM
- A `.internal` name that does not resolve, or does not reach its service
- Changing how long AdGuard Home keeps its query log or statistics
- Changing monitors in Uptime Kuma, or a container log that grows by gigabytes
- Reading the network watch files after an internet drop
- Attaching a data disk, sharing it over Samba and File Browser, or pointing Plex at it
- A VM whose root file system is full, or services that stopped writing
- Also covers AdGuard Home rewrites like a *.internal wildcard, upstreams, query log and statistics retention, ignored domains, an AdGuardHome.yaml edit, Uptime Kuma 2 monitors, its metrics key, the labelset log flood, a database edit, a Telegraf network watch of ping, DNS, HTTP and speed, Samba, File Browser, Plex, Homepage, Nginx Proxy Manager, a local CA for https on .internal names, deploying from a local clone, log limits, a USB or NTFS data disk, and a full disk
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

1. Ask before every change on the VM, a service, the Proxmox host or the router: a file edit, a restart, a stop, a `docker compose up -d`, a mount, an `fstab` line, a package. Say what changes, the worst case and how to undo it, then wait for a yes. One yes covers one change. Reading is free.
2. The git clone is the source of truth. A change to the Compose file or a file it mounts goes into the clone first, then is copied to the VM with `scp`. Never change only the copy on the VM, and never fetch from a GitHub raw link, which gives only what was pushed.
3. Every service carries a `json-file` log limit, `max-size` and `max-file`. A container created before the limit was added keeps an unlimited log until it is recreated.
4. Create every folder a container mounts as the login user before the first start. A data disk mount uses `create_host_path: false`, and its empty mount point carries `chattr +i`, so a missing disk stops a service instead of filling the system disk.
5. Back up a configuration file or a database before editing it, in the order the topic file gives: AdGuard Home is edited, then restarted, and Uptime Kuma is stopped, then edited.
6. Lowering the AdGuard Home query log interval deletes old queries at the next start or hourly check, for good. Say so, offer a copy of both log files first, and wait for a yes.
7. After creating a tag in Uptime Kuma, restart it before the tag stays on a monitor, or every heartbeat writes a stack trace into its log.
8. Secrets live in `.env` next to the Compose file, mode 600, written with hidden input and checked by length, never printed, never in the Compose file and never in a repository. The agent's own credentials live in an env file outside every repository, mode 600, read one key at a time with `grep` and `cut`, never sourced and never printed.
9. Never mount NTFS with the `force` option. A dirty volume is cleared with `ntfsfix -d` after the owner says yes, or checked in Windows when its files matter more than the time.
10. Probes and monitors target an address and port, never a `.internal` name, so a red result names one service rather than DNS, the proxy and the service at once.
11. The local CA carries a critical name constraint permitting only `DNS:internal`, and its key lives only on the owner's computer and in `.env` on the VM. Once its include serves `https`, the SSL tab of every proxy host stays on None, because a picked certificate adds a second `listen 443` and takes that host Offline.

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

- [ ] The change was made in the clone first and copied with `scp`, then `docker compose pull`, `docker compose up -d` and `docker compose ps`
- [ ] A container whose mounted file changed was restarted, Telegraf above all
- [ ] Every service in the Compose file carries `max-size` and `max-file`, and the containers were recreated once after the limit was added
- [ ] Every mounted folder existed before the first start and belongs to the login user
- [ ] A configuration file or database was backed up before the edit, and the value was read back afterwards
- [ ] A lower query log interval was approved after the owner heard that old queries go for good
- [ ] Uptime Kuma was restarted after a new tag, and `docker logs --since 1m uptime-kuma 2>&1 | grep -c PROMETHEUS` printed 0
- [ ] `.env` is mode 600, every value was checked by length, and nothing secret was printed
- [ ] The data disk is mounted by UUID with `nofail`, the empty mount point carries `chattr +i`, and `findmnt` showed the disk
- [ ] `df -h /` read after any change that writes data, and the largest container logs checked when it climbs
- [ ] The local CA was read back and shows `CA:TRUE, pathlen:0`, `Permitted: DNS:internal` and both excluded addresses, and `ca.key` is in no repository
- [ ] Every `.internal` name with a proxy host is in `INTERNAL_DNS_NAMES`, the SSL tab of every proxy host is on None, and the proxy was restarted after the job logged `issuing a new certificate`
- [ ] The certificate end date on the `notAfter=` line of `docker logs --tail 2 internal-ca` is more than 30 days away, or the job ran again
