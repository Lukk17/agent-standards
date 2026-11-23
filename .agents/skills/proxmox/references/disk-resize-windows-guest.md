# Grow a Disk Inside a Windows Guest

Read this after the virtual disk of a Windows VM grew on the host. The host step and the checks around it are in [disk-resize.md](disk-resize.md). The rules live in [SKILL.md](../SKILL.md). Every step changes a VM, so the owner approves it first. Every command here is UNVERIFIED.

Sources: the wiki page https://pve.proxmox.com/wiki/Resize_disks, and the Microsoft pages https://learn.microsoft.com/en-us/powershell/module/storage/resize-partition and https://learn.microsoft.com/en-us/powershell/module/storage/update-hoststoragecache.

---

### Extend the volume

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
