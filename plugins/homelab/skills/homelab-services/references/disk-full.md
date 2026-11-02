# A full disk on the VM

Read this before explaining services that stopped writing, a Syncthing folder that stopped, or a root file system near 100 percent. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab. Every other command here is UNVERIFIED.

---

### The symptoms

A full root file system on the VM shows first in the services that write, not as one clear error. VERIFIED:

1. Syncthing stopped every folder with `insufficient space on disk for database (/config/index-v2): current 0.00 % < required 1 %`, and failed to save its configuration with `no space left on device`. The `syncthing` skill owns that error.
2. Telegraf wrote no network watch rows, and the rows of that time are lost.
3. Growing the LVM volume inside the VM failed, because `pvresize` writes a metadata backup under `/etc/lvm` first: `/etc/lvm/archive/...: write error failed: No space left on device`.

Two causes together filled it: a root logical volume that the Ubuntu Server installer had left at half the volume group, and one container log of 24.7 GB with no limit, see [deploy-and-logs.md](deploy-and-logs.md#log-limits-on-every-service).

---

### Find what filled it

How full, and how much of the volume group is unused:

```bash
df -h /
```

```bash
sudo vgs
```

What Docker holds, images, containers and volumes:

```bash
docker system df
```

The ten largest container logs:

```bash
sudo sh -c 'du -h /var/lib/docker/containers/*/*-json.log' | sort -h | tail -n 10
```

The folder of a log is the full container ID. Match it to a name:

```bash
docker ps -a --no-trunc --format '{{.ID}} {{.Names}}'
```

The AdGuard Home query log, which held 4.0 GB at the 90 day default, VERIFIED:

```bash
docker exec adguard-home du -sh /opt/adguardhome/work/data
```

---

### Free space now, then fix the cause

With the file system completely full, free a little first, so the tools that fix it can write. VERIFIED: these two freed about 64 MB, enough for `pvresize` to succeed:

```bash
sudo apt clean
```

```bash
sudo journalctl --vacuum-size=100M
```

Then the lasting fixes, each with the owner's yes:

1. A container log that floods: stop the cause, for Uptime Kuma the restart in [uptime-kuma.md](uptime-kuma.md#the-labelset-log-flood), and give every service a log limit, then recreate the containers with `docker compose up -d`, which removes their old logs. VERIFIED: 44G used before and 20G after.
2. A root volume smaller than its volume group: grow it. The `proxmox` skill owns the virtual disk, the partition and the LVM steps.
3. A query log that is too large: a shorter interval, after the warning in [adguard-home.md](adguard-home.md#query-log-and-statistics-retention).
4. A data path that wrote to the system disk because the data disk was not mounted: the mount point protection in [data-disk.md](data-disk.md#protect-the-empty-mount-point).

Nothing on the VM warns before the disk fills. Read `df -h /` after any change that writes data, and check the largest logs when it climbs.
