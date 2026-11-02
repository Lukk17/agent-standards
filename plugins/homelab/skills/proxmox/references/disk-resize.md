# Grow a VM Disk

Contents:

- [The three layers](#the-three-layers)
- [Before the host step](#before-the-host-step)
- [Ubuntu Server often has free space already](#ubuntu-server-often-has-free-space-already)
- [The host step](#the-host-step)
- [Linux guest: make the kernel see the new size](#linux-guest-make-the-kernel-see-the-new-size)
- [Linux guest: grow the partition](#linux-guest-grow-the-partition)
- [Linux guest with LVM: grow the volume and the file system](#linux-guest-with-lvm-grow-the-volume-and-the-file-system)
- [Linux guest without LVM: grow the file system](#linux-guest-without-lvm-grow-the-file-system)
- [Windows guest](#windows-guest)
- [After every resize](#after-every-resize)

Read this before growing the virtual disk of a VM, or when a guest still shows the old size after a resize. The rules live in [SKILL.md](../SKILL.md). Every step changes a VM, so the owner approves it first. Every command here is UNVERIFIED.

Sources: the wiki page https://pve.proxmox.com/wiki/Resize_disks, the manual page https://pve.proxmox.com/pve-docs/qm.1.html, `subiquity/common/storage/sizes.py`, `subiquity/server/controllers/storage.py` and `subiquity/common/types/storage.py` on the `main` branch of `canonical/subiquity`, `bin/growpart` in `canonical/cloud-utils`, the lvextend manual https://man7.org/linux/man-pages/man8/lvextend.8.html, `drivers/scsi/scsi_sysfs.c` in the Linux kernel, and the Microsoft pages https://learn.microsoft.com/en-us/powershell/module/storage/resize-partition and https://learn.microsoft.com/en-us/powershell/module/storage/update-hoststoragecache.

---

### The three layers

The wiki says it plainly: "If you enlarge the hard disk, once you have added the disk plate, your partition table and file system knows nothing about the new size, so you have to act inside the VM to fix it." A reboot does not change that. Growing a disk is three steps, and the guest only gains space after the last one:

1. The virtual disk, on the Proxmox host.
2. The partition, and on LVM the physical volume and the logical volume, inside the guest.
3. The file system, inside the guest.

---

### Before the host step

1. Check inside an Ubuntu guest whether the space is already there, see the next section. If it is, skip the host step entirely.
2. Read the thin pool's free data and metadata space, see [storage.md](storage.md). Growing a disk on a thin pool reserves nothing, so a pool can promise more than it holds.
3. A recent backup exists, see [snapshots-and-backups.md](snapshots-and-backups.md).
4. Read the VM's disks to get the exact slot name, such as `scsi0` or `virtio0`, from `/nodes/<node>/qemu/<vm-id>/config` in [api-access.md](api-access.md).

---

### Ubuntu Server often has free space already

The Ubuntu Server installer's guided LVM layout does not give the whole volume group to the root volume. In `subiquity`, the installer, the default sizing policy is `SCALED`, and `scaled_rootfs_size` in `sizes.py` decides the root volume size from the volume group size:

| Volume group size | Root logical volume |
|---|---|
| under 10 GiB | all of it |
| 10 to 20 GiB | 10 GiB |
| 20 to 200 GiB | half |
| 200 GiB and more | 100 GiB |

The code comment says this is done "to leave room for snapshots and such". The volume group is `ubuntu-vg` and the root volume `ubuntu-lv`, from `storage.py`. Read this in the subiquity source, so confidence is high for installs made with a recent installer and medium for older releases, which may have shipped a different version of this function. Check the guest before anything else. `VFree` is space that only needs `lvextend`:

```bash
sudo vgs
```

```bash
sudo lvs
```

If `VFree` is large enough, skip to "Grow the logical volume and the file system" below, with no host change at all.

---

### The host step

In the web page: select the VM, Hardware, select the Hard Disk, Disk Action, Resize, and enter the amount to add. The wiki shows this path.

On the host shell, as root. The manual page says the size is "The new size. With the + sign the value is added to the actual size of the volume and without it, the value is taken as an absolute one. Shrinking disk size is not supported." Always use the `+` form, so a typo cannot ask for a smaller disk:

```bash
qm disk resize <vm-id> scsi0 +<size>G
```

`qm resize` is "An alias for qm disk resize". The wiki says "You can resize your disks online or offline with command line". The same call through the API is `PUT /nodes/<node>/qemu/<vm-id>/resize`, which needs `VM.Config.Disk` on the VM and `Datastore.AllocateSpace` on the disk's storage. The admin token in [api-access.md](api-access.md) can do it, after the owner said yes to this one resize, and the call is under "Calls that change something" there. Of the narrower alternatives there, the change token of Alternative 2 can as well, and the read-only token of Alternative 1 cannot.

---

### Linux guest: make the kernel see the new size

The wiki says virtio disks show the new size online: "Linux should see the new size online without reboot with kernel >= 3.6". Check what the kernel sees:

```bash
lsblk
```

```bash
sudo dmesg | grep -i "capacity change"
```

A disk on a SCSI controller, `scsi0` with a guest name such as `sda`, may need a rescan first. The kernel creates a write-only `rescan` attribute for every SCSI device, `DEVICE_ATTR(rescan, S_IWUSR, NULL, store_rescan_field)` in `drivers/scsi/scsi_sysfs.c`, and writing to it rescans the device:

```bash
echo 1 | sudo tee /sys/class/block/<disk>/device/rescan
```

`<disk>` is the whole disk, such as `sda`, never a partition. Run `lsblk` again and check the disk size.

---

### Linux guest: grow the partition

`growpart` from the `cloud-guest-utils` package grows one partition into the free space after it. Its usage text says it will "rewrite partition table so that partition takes up all the space it can". The partition has to be the last one on the disk. The disk and the partition number are separate arguments:

```bash
sudo growpart /dev/<disk> <partition-number>
```

Where `growpart` is missing, the wiki uses `parted /dev/<disk>` and then `resizepart <partition-number> 100%`, after letting parted fix the GPT backup header when it asks.

---

### Linux guest with LVM: grow the volume and the file system

In Ubuntu's guided layout the LVM physical volume is usually the last partition, check with `lsblk`. Grow the physical volume into the bigger partition:

```bash
sudo pvresize /dev/<disk><partition-number>
```

Then grow the logical volume and its file system in one step. The lvextend manual says `-r|--resizefs` will "Resize underlying filesystem together with the LV using fsadm(8)", and the wiki says of the same step that "the file system can be mounted, works with ext4 and xfs":

```bash
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
```

Use `-L +<size>G` instead of `-l +100%FREE` to keep some of the volume group free, as the installer intended.

---

### Linux guest without LVM: grow the file system

After `growpart`, grow the file system on that partition. ext4:

```bash
sudo resize2fs /dev/<disk><partition-number>
```

XFS grows through its mount point, not the device:

```bash
sudo xfs_growfs /
```

Read the result:

```bash
df -h
```

---

### Windows guest

The wiki says Windows sees a virtio disk's new size online "with last virtio drivers". If it does not, the wiki adds that a full shutdown helps, `shutdown -s -t 0`, because the default shutdown on Windows 8 and later is the fast one.

In Disk Management: right-click the volume, Extend Volume, and accept the maximum. The same in an elevated `pwsh`, which goes to the owner. First make Windows re-read the disks: the Microsoft page says `Update-HostStorageCache` "is equivalent to a VDS Rescan":

```powershell
Update-HostStorageCache
```

```powershell
Get-Partition -DriveLetter C
```

```powershell
$size = Get-PartitionSupportedSize -DriveLetter C
```

```powershell
Resize-Partition -DriveLetter C -Size $size.SizeMax
```

The Microsoft page says `Resize-Partition` "resizes a partition and the underlying file system", so no second step is needed. When another partition, often the recovery partition, sits right after the volume, Extend Volume stays grey and `SizeMax` equals the current size. That is common knowledge, not checked against a vendor page here. Moving or removing that partition is a separate change the owner decides.

---

### After every resize

1. `df -h` or `Get-Volume` inside the guest shows the new size.
2. The thin pool use was read again, see [storage.md](storage.md).
3. The change is written in the owner's notes: the VM, the disk, the old and the new size.
