# Arch Linux Administration Checklist

Run it before calling an Arch system change done.

- [ ] `MACHINE.md` read before the first change
- [ ] News checked and pending updates listed before any full upgrade
- [ ] No `-Sy` without `u`, no `--overwrite '*'`, no `-Rdd`, no `IgnorePkg` used to dodge an error
- [ ] Every root command handed to the owner, never run by the agent
- [ ] Snapshot taken before kernel, bootloader, initramfs, fstab or bulk removal work
- [ ] No packaged file edited, every override placed in a drop-in
- [ ] Every PKGBUILD read before building
- [ ] The change and its undo recorded in the `MACHINE.md` change log
