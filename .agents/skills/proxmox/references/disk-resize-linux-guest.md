# Grow a Disk Inside a Linux Guest

Contents:

- [Ubuntu Server often has free space already](#ubuntu-server-often-has-free-space-already)
- [Make the kernel see the new size](#make-the-kernel-see-the-new-size)
- [Grow the partition](#grow-the-partition)
- [With LVM: grow the volume and the file system](#with-lvm-grow-the-volume-and-the-file-system)
- [Without LVM: grow the file system](#without-lvm-grow-the-file-system)

Read this after the virtual disk of a Linux VM grew on the host, or before that step on an Ubuntu Server guest, which often has free space already. The host step and the checks around it are in [disk-resize.md](disk-resize.md). The rules live in [SKILL.md](../SKILL.md). Every step changes a VM, so the owner approves it first. Every command here is UNVERIFIED.

Sources: the wiki page https://pve.proxmox.com/wiki/Resize_disks, `subiquity/common/storage/sizes.py`, `subiquity/server/controllers/storage.py` and `subiquity/common/types/storage.py` on the `main` branch of `canonical/subiquity`, `bin/growpart` in `canonical/cloud-utils`, the lvextend manual https://man7.org/linux/man-pages/man8/lvextend.8.html, and `drivers/scsi/scsi_sysfs.c` in the Linux kernel.

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

If `VFree` is large enough, skip to [With LVM: grow the volume and the file system](#with-lvm-grow-the-volume-and-the-file-system) below, with no host change at all.

---

### Make the kernel see the new size

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

### Grow the partition

`growpart` from the `cloud-guest-utils` package grows one partition into the free space after it. Its usage text says it will "rewrite partition table so that partition takes up all the space it can". The partition has to be the last one on the disk. The disk and the partition number are separate arguments:

```bash
sudo growpart /dev/<disk> <partition-number>
```

Where `growpart` is missing, the wiki uses `parted /dev/<disk>` and then `resizepart <partition-number> 100%`, after letting parted fix the GPT backup header when it asks.

---

### With LVM: grow the volume and the file system

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

### Without LVM: grow the file system

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
