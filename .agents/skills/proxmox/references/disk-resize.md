# Grow a VM Disk

Read this before growing the virtual disk of a VM, or when a guest still shows the old size after a resize. This file holds the steps on the Proxmox host, and the steps inside the guest are in [disk-resize-linux-guest.md](disk-resize-linux-guest.md) and [disk-resize-windows-guest.md](disk-resize-windows-guest.md). The rules live in [SKILL.md](../SKILL.md). Every step changes a VM, so the owner approves it first. Every command here is UNVERIFIED.

Sources: the wiki page https://pve.proxmox.com/wiki/Resize_disks and the manual page https://pve.proxmox.com/pve-docs/qm.1.html.

---

### The three layers

The wiki says it plainly: "If you enlarge the hard disk, once you have added the disk plate, your partition table and file system knows nothing about the new size, so you have to act inside the VM to fix it." A reboot does not change that. Growing a disk is three steps, and the guest only gains space after the last one:

1. The virtual disk, on the Proxmox host.
2. The partition, and on LVM the physical volume and the logical volume, inside the guest.
3. The file system, inside the guest.

---

### Before the host step

1. Check inside an Ubuntu guest whether the space is already there, see [disk-resize-linux-guest.md](disk-resize-linux-guest.md#ubuntu-server-often-has-free-space-already). If it is, skip the host step entirely.
2. Read the thin pool's free data and metadata space, see [storage.md](storage.md). Growing a disk on a thin pool reserves nothing, so a pool can promise more than it holds.
3. A recent backup exists, see [snapshots-and-backups.md](snapshots-and-backups.md).
4. Read the VM's disks to get the exact slot name, such as `scsi0` or `virtio0`, from `/nodes/<node>/qemu/<vm-id>/config` in [api-calls.md](api-calls.md#reading).

---

### The host step

In the web page: select the VM, Hardware, select the Hard Disk, Disk Action, Resize, and enter the amount to add. The wiki shows this path.

On the host shell, as root. The manual page says the size is "The new size. With the + sign the value is added to the actual size of the volume and without it, the value is taken as an absolute one. Shrinking disk size is not supported." Always use the `+` form, so a typo cannot ask for a smaller disk:

```bash
qm disk resize <vm-id> scsi0 +<size>G
```

`qm resize` is "An alias for qm disk resize". The wiki says "You can resize your disks online or offline with command line". The same call through the API is `PUT /nodes/<node>/qemu/<vm-id>/resize`, which needs `VM.Config.Disk` on the VM and `Datastore.AllocateSpace` on the disk's storage. The admin token in [admin-token.md](admin-token.md) can do it, after the owner said yes to this one resize, and the call is under "Calls that change something" in [api-calls.md](api-calls.md#calls-that-change-something). Of the narrower alternatives in [narrower-tokens.md](narrower-tokens.md), the change token of Alternative 2 can as well, and the read-only token of Alternative 1 cannot.

---

### After every resize

1. `df -h` or `Get-Volume` inside the guest shows the new size.
2. The thin pool use was read again, see [storage.md](storage.md).
3. The change is written in the owner's notes: the VM, the disk, the old and the new size.
