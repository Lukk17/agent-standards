# A USB or NTFS data disk in the VM

Contents:

- [Attach it by its stable name](#attach-it-by-its-stable-name)
- [Protect the empty mount point](#protect-the-empty-mount-point)
- [Mount an NTFS disk as it is](#mount-an-ntfs-disk-as-it-is)
- [A dirty NTFS volume](#a-dirty-ntfs-volume)
- [When the disk is missing](#when-the-disk-is-missing)

Read this before attaching a data disk to the VM, mounting it, sharing it, or clearing a dirty NTFS volume. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab, on an Ubuntu Server VM whose kernel has `ntfs3` and with `ntfs-3g` installed. Every other command here is UNVERIFIED. Attaching the disk on the Proxmox host is the `proxmox` skill's ground, and it is here only as the one command the VM side depends on.

Sources: the kernel's ntfs3 documentation, `Documentation/filesystems/ntfs3.rst`, and `fs/namei.c`, both on the `master` branch of https://github.com/torvalds/linux, and the chattr manual page at https://man7.org/linux/man-pages/man1/chattr.1.html. Quoted from the owner's notes and not fetched again: the mount manual page at https://man7.org/linux/man-pages/man8/mount.8.html, the ntfsfix manual page at https://man.archlinux.org/man/ntfsfix.8, and the Proxmox wiki page on passing a physical disk to a VM.

---

### Attach it by its stable name

On the Proxmox host, find the disk's stable name, the line for the whole disk and not a `-part` one:

```bash
ls -l /dev/disk/by-id/ | grep usb-
```

The Proxmox wiki says "device names like /dev/sdc should never be used, as this can change between reboots. Use the stable /dev/disk/by-id paths instead." Hand the whole disk to the VM as a second SCSI disk, kept out of the VM's backups:

```bash
qm set <vm-id> -scsi1 /dev/disk/by-id/<disk-id>,backup=0
```

VERIFIED on the homelab. Without `backup=0` every backup of the VM would copy the whole data disk.

---

### Protect the empty mount point

The mount point is an empty folder on the VM's system disk. When the data disk is not mounted, after a boot without it or a failed mount, a container that mounts that folder writes into it, onto the system disk, until it is full. The immutable flag stops that: a folder with the flag refuses every new file, root included. While the disk is mounted, the folder underneath is hidden, and writes go to the disk.

```bash
sudo mkdir -p /mnt/data
```

Make sure nothing is mounted there yet. This must print nothing:

```bash
findmnt /mnt/data
```

```bash
sudo chattr +i /mnt/data
```

Read the flag back. The letters before the path include an `i`:

```bash
lsattr -d /mnt/data
```

VERIFIED on the homelab with the disk unmounted: `lsattr -d /mnt/data` printed `----i---------e-------`, and mounting the NTFS disk over the flagged folder afterwards worked.

Prove the refusal while the disk is still not mounted. This must fail with `Operation not permitted`:

```bash
sudo touch /mnt/data/test
```

UNVERIFIED: the refused write was not measured on the homelab, so run the check above on every VM. It rests on two sources. The chattr manual: "A file with the 'i' attribute cannot be modified: it cannot be deleted or renamed, no link can be created to this file [...] Only the superuser or a process possessing the CAP_LINUX_IMMUTABLE capability can set or clear this attribute." The kernel's `fs/namei.c`: the comment above `may_create_dentry` lists "We can't do it if dir is immutable (done in permission())", and `inode_permission` returns `-EPERM` for a write under the comment "Nobody gets write access to an immutable file.", before it looks at who asks, so root is refused too. The mount manual: "The previous contents (if any) and owner and mode of dir become invisible", which is why the flag does not stand in the way of the mounted disk. The flag needs a system file system that keeps it, ext4 does. To remove the folder one day, clear the flag first, with the disk unmounted, using `sudo chattr -i /mnt/data`.

---

### Mount an NTFS disk as it is

The kernel's own `ntfs3` driver mounts NTFS read and write without formatting it. NTFS has no Linux owners, so `uid` and `gid` give every file to the user the containers run as. Read the UUID:

```bash
sudo blkid /dev/<partition>
```

Add one line to `/etc/fstab`. Run it once, because every run adds another line:

```bash
echo 'UUID=<uuid> /mnt/data ntfs3 defaults,nofail,uid=1000,gid=1000,x-systemd.device-timeout=10s 0 0' | sudo tee -a /etc/fstab
```

`UUID=` follows the file system, not the device name. `nofail` lets the VM finish booting without the disk, so DNS keeps answering. `x-systemd.device-timeout=10s` stops the boot from waiting 90 seconds for it. The last field is 0, since there is no Linux check of NTFS at boot. A new empty disk is formatted ext4 instead and needs a `chown -R 1000:1000` of its top folder, since ext4 keeps owners.

```bash
sudo systemctl daemon-reload
```

```bash
sudo mount -a
```

```bash
findmnt /mnt/data
```

VERIFIED: `findmnt` printed `/mnt/data /dev/sdb1 ntfs3 rw,relatime,uid=1000,gid=1000,acl,iocharset=utf8,prealloc`.

---

### A dirty NTFS volume

Windows marks a volume dirty while it is in use and clears the mark at safe removal. A disk pulled out without safe removal keeps it, and `ntfs3` refuses to mount it. VERIFIED: `mount -a` failed with `wrong fs type, bad option, bad superblock`, and the kernel log said why:

```bash
sudo dmesg | grep ntfs3
```

```text
ntfs3(sdb1): volume is dirty and "force" flag is not set!
```

The ntfs3 documentation says of `force`: "Forces the driver to mount partitions even if volume is marked dirty. Not recommended for use." So clear the mark instead, with the owner's yes:

```bash
sudo ntfsfix -d /dev/<partition>
```

```bash
sudo mount -a
```

VERIFIED: the mount worked at once after `ntfsfix -d`. Its manual says "ntfsfix is NOT a Linux version of chkdsk" and, for `-d`, "Clear the volume dirty flag if the volume can be fixed and mounted." When the files matter more than the time, check the disk in Windows and remove it safely there instead. The mark comes back after every unsafe removal. With `nofail` the VM still boots, the disk is simply not mounted, and the flag on the mount point keeps the containers off the system disk.

---

### When the disk is missing

QEMU opens every disk in the VM's configuration at start, so a missing disk can keep the VM from starting, and the VM may be the network's DNS server. Inferred from how a missing device path behaves, not measured, confidence high. Detach it on the host, start the VM, and attach it again once it is back:

```bash
qm set <vm-id> --delete scsi1
```

```bash
qm start <vm-id>
```

A Plex mount of `/mnt/data/media` with `create_host_path: false` refuses to start while the disk is not mounted, which is the intended failure. File Browser and Samba mount `/mnt/data` itself, which always exists, so the immutable flag is their only protection.
