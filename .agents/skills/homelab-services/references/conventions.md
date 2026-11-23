# Conventions

Contents:

- [Facts about one setup](#facts-about-one-setup)
- [Verification marks](#verification-marks)
- [Topics covered](#topics-covered)
- [Hard rules with their reasons](#hard-rules-with-their-reasons)

Companion reference for the [homelab-services](../SKILL.md) skill. Load it before writing a command or a note that names a host, a user, a folder or a container, and when judging how far to trust a fact in the topic files.

---

### Facts about one setup

Addresses, host names, user names, the path of the stack folder on the VM, and the names of real monitors and shares belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md` or the repository that holds the Compose file, never in this skill. Every example uses placeholders in angle brackets: `<vm-ip>`, `<user>`, `<stack-dir>`, `<clone-dir>` for the folder of the clone that holds the Compose file, `<uuid>`, `<disk-id>`. Container names are the usual service names, `adguard-home`, `uptime-kuma`, `telegraf`, `samba`, `filebrowser`, `plex`, `homepage` and `nginx-proxy-manager`. Read the real ones with `docker ps --format '{{.Names}}'` and use those.

---

### Verification marks

The skill is written for AdGuard Home 0.107, Uptime Kuma 2, Telegraf 1, Samba 4, File Browser 2 (`gtstef/filebrowser`), Plex Media Server, Homepage 1 and Nginx Proxy Manager 2 as containers on an Ubuntu Server VM under Proxmox VE, with OpenSSL 3 in a throwaway container for the local CA. Facts carry a VERIFIED or UNVERIFIED mark. Facts marked VERIFIED were measured on a test homelab, or in throwaway containers where the mark says so. The AdGuard Home file edit and the Uptime Kuma database edit were also run end to end in throwaway containers of the same images, with no network. Each topic file names its sources. Everything else is UNVERIFIED.

---

### Topics covered

The skill also covers AdGuard Home rewrites like a *.internal wildcard, upstreams, query log and statistics retention, ignored domains, an AdGuardHome.yaml edit, Uptime Kuma 2 monitors, its metrics key, the labelset log flood, a database edit, a Telegraf network watch of ping, DNS, HTTP and speed, Samba, File Browser, Plex, Homepage, Nginx Proxy Manager, a local CA for https on .internal names, deploying from a local clone, log limits, a USB or NTFS data disk, and a full disk.

---

### Hard rules with their reasons

The rules of [SKILL.md](../SKILL.md), each with its reason. A rule that holds for one service only is in that service's reference: the tag rule in [uptime-kuma.md](uptime-kuma.md), and the local CA rule in [local-ca.md](local-ca.md).

1. Ask before every change on the VM, a service, the Proxmox host or the router: a file edit, a restart, a stop, a `docker compose up -d`, a mount, an `fstab` line, a package. Say what changes, the worst case and how to undo it, then wait for a yes. One yes covers one change. Reading is free.
2. The git clone is the source of truth. A change to the Compose file or a file it mounts goes into the clone first, then is copied to the VM with `scp`. Never change only the copy on the VM, and never fetch from a GitHub raw link, which gives only what was pushed.
3. Every service carries a `json-file` log limit, `max-size` and `max-file`. A container created before the limit was added keeps an unlimited log until it is recreated.
4. Create every folder a container mounts as the login user before the first start. A data disk mount uses `create_host_path: false`, and its empty mount point carries `chattr +i`, so a missing disk stops a service instead of filling the system disk.
5. Back up a configuration file or a database before editing it, in the order the topic file gives: AdGuard Home is edited, then restarted, and Uptime Kuma is stopped, then edited.
6. Lowering the AdGuard Home query log interval deletes old queries at the next start or hourly check, for good. Say so, offer a copy of both log files first, and wait for a yes.
7. Secrets live in `.env` next to the Compose file, mode 600, written with hidden input and checked by length, never printed, never in the Compose file and never in a repository. The agent's own credentials live in an env file outside every repository, mode 600, read one key at a time with `grep` and `cut`, never sourced and never printed. The local CA key stays only on the owner's computer and in the VM's `.env`.
8. Never mount NTFS with the `force` option. A dirty volume is cleared with `ntfsfix -d` after the owner says yes, or checked in Windows when its files matter more than the time.
9. Probes and monitors target an address and port, never a `.internal` name, so a red result names one service rather than DNS, the proxy and the service at once.
