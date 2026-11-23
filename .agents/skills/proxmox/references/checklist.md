# Proxmox Checklist

Run it before calling work on a Proxmox VE host done. The rules behind the items are in [SKILL.md](../SKILL.md).

- [ ] The agent uses a token on a user of its own, the admin token or a chosen alternative, never a password or `root@pam`
- [ ] The token's permissions were checked with `pveum user token permissions` before it was handed over
- [ ] With an alternative, a change token belongs to its own user and was used only for the one change the owner approved
- [ ] Every delete had its own yes after the VM's newest backup was named
- [ ] The env file sits outside every repository, readable only by the owner
- [ ] Every curl call verifies TLS by CA file or by pinned public key, never `-k` alone
- [ ] Every change was approved by the owner after the worst case and the undo were stated
- [ ] A backup exists before a disk change, and the thin pool has room for the growth
- [ ] After a resize, the guest's partition and file system were grown and checked with `lsblk` and `df -h` or `Get-Volume`
- [ ] On an Ubuntu guest, `vgs` checked for free space before asking for a bigger virtual disk
- [ ] Thin pool data and metadata use read and reported after the change
