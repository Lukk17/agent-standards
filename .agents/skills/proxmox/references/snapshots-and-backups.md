# Snapshots and Backups

Read this before taking or rolling back a snapshot, running a backup, or planning a backup job. The rules live in [SKILL.md](../SKILL.md). Taking, rolling back and deleting a snapshot and running a backup all change the host, so the owner approves each one first. Every command here is UNVERIFIED.

Sources, fetched on 2026-10-23: the manual page https://pve.proxmox.com/pve-docs/qm.1.html at version 9.2.13, the backup chapter https://pve.proxmox.com/pve-docs/chapter-vzdump.html and its source `vzdump.adoc`, the snapshot section of `qm.adoc`, the LVM thin page https://pve.proxmox.com/wiki/Storage:_LVM_Thin, and the API schema of https://pve.proxmox.com/pve-docs/api-viewer/.

---

### Snapshot or backup

| | Snapshot | Backup |
|---|---|---|
| Where it lives | on the same storage as the disk | a separate backup storage, ideally another machine |
| Survives a lost disk or pool | no | yes, if stored elsewhere |
| Good for | going back after a risky change inside the guest, within hours | restoring after a loss, keeping history |
| Cost on a thin pool | grows as the guest writes, uses pool space | uses the backup storage |

A snapshot is a quick undo for the next change, never the only copy. The LVM thin page lists snapshots as supported for `lvmthin`, which is what `local-lvm` is on a default install, see [storage.md](storage.md).

---

### Read snapshots

Through the API with the agent's token, `/nodes/<node>/qemu/<vm-id>/snapshot`, which needs `VM.Audit`, see [api-access.md](api-access.md). On the host shell:

```bash
qm listsnapshot <vm-id>
```

---

### Take, roll back, delete

All three go to the owner, on the host shell as root or in the web page under the VM, Snapshots.

The snapshot section of `qm.adoc` says a snapshot stores the configuration "into a separate snapshot section within the same configuration file", and that "You can optionally save the memory of a running VM with the option `vmstate`". Without the memory the snapshot holds the disks as they were, like a power cut, so a running database may need its own recovery when rolled back.

```bash
qm snapshot <vm-id> <snapshot-name> --description "<why, and who asked>"
```

```bash
qm snapshot <vm-id> <snapshot-name> --vmstate 1 --description "<why, and who asked>"
```

A rollback throws away everything the guest wrote since the snapshot. State that in the request to the owner, every time:

```bash
qm rollback <vm-id> <snapshot-name>
```

Delete a snapshot once the change it guarded is confirmed good, because on a thin pool it keeps using space as the guest writes:

```bash
qm delsnapshot <vm-id> <snapshot-name>
```

Taking one through the API is `POST /nodes/<node>/qemu/<vm-id>/snapshot`, which needs `VM.Snapshot`. The admin token in [api-access.md](api-access.md) can do it, after the owner said yes to this one snapshot. Of the narrower alternatives there, the change token of Alternative 2 can as well, and the read-only token of Alternative 1 cannot.

---

### Back up one VM now

`vzdump` writes a backup archive to a backup storage. The backup chapter describes the modes for a VM:

1. `snapshot`: "This mode provides the lowest operation downtime, at the cost of a small inconsistency risk." The chapter adds: "If the guest agent is enabled (`agent: 1`) and running, it calls `guest-fsfreeze-freeze` and `guest-fsfreeze-thaw` to improve consistency."
2. `stop`: "This mode provides the highest consistency of the backup, at the cost of a short downtime in the VM operation."

A one-off backup of one VM to a named backup storage, by the owner on the host shell:

```bash
vzdump <vm-id> --storage <backup-storage> --mode snapshot
```

Or in the web page: the VM, Backup, Backup now.

---

### Backup jobs

The backup chapter: "You can manage the jobs in the UI under 'Datacenter' -> 'Backup' or via the `/cluster/backup` API endpoint. Both will generate job entries in `/etc/pve/jobs.cfg`, which are parsed and executed by the `pvescheduler` daemon." Every token in [api-access.md](api-access.md) can list them, because `GET /cluster/backup` needs `Sys.Audit`. Creating one needs `Sys.Modify`, so the owner does it.

Retention belongs on the job or the storage. The chapter's example is `--prune-backups keep-last=3,keep-daily=13,keep-yearly=9`, and it says "it is often more sensible to configure the setting on the storage level". It also warns that "scheduled backups miss their execution when the host was offline or the pvescheduler was disabled during the scheduled time", so read the job's last run, not only its schedule.

When reporting on backups, list for each VM: which job covers it, the target storage, the retention, and the date of the newest archive. A VM that no job covers is a finding.

---

### Restore

A restore overwrites or creates a VM, so it is the owner's decision every time. The backup chapter's example restores to a new VM ID, which keeps the original untouched:

```bash
qmrestore <path-to-archive> <new-vm-id>
```
