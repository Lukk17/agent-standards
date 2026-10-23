# Storage Use and Thin Pools

Read this before judging whether a storage has room, before growing a disk or taking a snapshot on a thin pool, and when a guest reports write errors. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Sources, fetched on 2026-10-23: the storage chapter https://pve.proxmox.com/pve-docs/chapter-pvesm.html and the LVM thin page https://pve.proxmox.com/wiki/Storage:_LVM_Thin with its source `pve-storage-lvmthin.adoc`, the local LVM section of https://pve.proxmox.com/pve-docs/chapter-sysadmin.html from `local-lvm.adoc`, the installer options in `pve-installation.adoc`, the API schema of https://pve.proxmox.com/pve-docs/api-viewer/, and the lvmthin manual https://man7.org/linux/man-pages/man7/lvmthin.7.html.

---

### What local-lvm is

On a default install with LVM, the volume group `pve` holds `root`, `swap` and `data`. The local LVM section says: "data: This volume uses LVM-thin, and is used to store VM images", and the storage that points at it is `local-lvm`. The LVM thin page explains thin provisioning: "LVM thin pools instead allocates blocks when they are written. This behaviour is called thin-provisioning, because volumes can be much larger than physically available space."

So the sum of all VM disk sizes on `local-lvm` can be larger than the pool. Nothing stops that, and nothing warns until the pool fills.

---

### Read the use

Through the API with the agent's token, see [api-access.md](api-access.md):

| Path | What it returns, from the API schema |
|---|---|
| `/nodes/<node>/storage` | per storage `total`, `used`, `avail` in bytes |
| `/nodes/<node>/storage/<storage>/status` | the same for one storage |
| `/nodes/<node>/disks/lvmthin` | per thin pool `lv`, `vg`, `lv_size`, `used`, `metadata_size`, `metadata_used` in bytes |

The thin pool call is the one that matters, because it is the only one that shows metadata. Divide `used` by `lv_size` and `metadata_used` by `metadata_size` and report both as percentages.

On the host shell the owner gets the same from LVM. The lvmthin manual shows `Data%` and `Meta%` columns:

```bash
lvs -o name,lv_size,data_percent,metadata_percent pve
```

```bash
vgs pve
```

`VFree` of the volume group is the room left to grow the pool and its metadata. The installer leaves some on purpose: its `minfree` option "Defines the amount of free space that should be left in the LVM volume group `pve`. With more than 128GB storage available, the default is 16GB, otherwise `hdsize/8` will be used."

---

### Why an overfull thin pool is dangerous

The lvmthin manual, section "Thin Pool Data Exhaustion": by default a full pool queues writes, and "If data space has not been extended after this time, the queued writes will return an error to the caller, e.g. the file system. This can result in file system damage that requires repair. When a thin pool returns errors for writes to a thin LV, any file system is subject to losing unsynced user data." The default wait is "up to 60 seconds".

Section "Thin Pool Metadata Exhaustion": "Metadata space exhaustion can lead to inconsistent thin pool metadata and inconsistent file systems, so the response requires offline checking and repair."

Every VM on the pool is hit at once, not only the one that wrote the last block. When several guests on the same pool report write errors or read-only file systems at the same time, read the pool use first. That pattern is inferred from the manual text above, not measured.

---

### What to do with the numbers

These thresholds are this skill's rule, not a vendor figure:

1. Report any pool whose data or metadata use is above 80 %.
2. Above 90 % data or metadata, stop and ask before anything that writes to the pool: a disk resize, a snapshot, a restore, a new VM.
3. Before growing a VM disk, compare the growth with the pool's free space. A resize itself allocates nothing, but the guest will fill what it was given.

Ways out, each an owner decision:

1. Delete snapshots that are no longer needed, see [snapshots-and-backups.md](snapshots-and-backups.md).
2. Inside the guests, delete data, then let the guest pass freed blocks back with discard. Whether discard reaches the pool depends on the disk's `discard` option and the guest, so measure the pool use before and after.
3. Grow the pool into `VFree` of the volume group. The local LVM section gives the command and the warning that goes with it: "When extending the data pool, the metadata pool must also be extended."

```bash
lvresize --size +<size>G --poolmetadatasize +<size>G pve/data
```

4. Move a VM disk to another storage, or add a disk to the volume group. Both are larger changes the owner plans.
