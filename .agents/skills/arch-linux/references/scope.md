# Scope

Companion reference for the [arch-linux](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

Package and system administration on Arch Linux and Arch-based distributions: pacman and the AUR, upgrades and mirror errors, .pacnew files, cleanup, snapper rollback, systemd and journal triage, crashes and audio.

- Any pacman, paru, yay or makepkg command, including a read-only query
- An upgrade, a downgrade, or a download error from a mirror
- A `.pacnew` or `.pacsave` file, or a change under `/etc`
- Disk space, orphans, caches, snapshots or a rollback
- A failed systemd unit, a journal question, a crash, a coredump
- Any audio problem on PipeWire, WirePlumber or ALSA
- Also covers pacman, the AUR with paru or yay, makepkg and PKGBUILD review, full upgrades and the pre-upgrade news check, partial upgrades and mirror 404s, .pacnew and .pacsave merging, orphans and cache cleanup, snapper snapshots and rollback, systemd units and journal triage, coredump crash diagnosis, PipeWire and WirePlumber audio, and editing configuration without touching packaged files
- The user says "pacman -Syu", "install this from the AUR", "what is this pacnew", "roll back the upgrade", "failed retrieving file", "unable to satisfy dependency", "No module named build", "free up disk space", "clean up leftovers", "this service failed", "the program crashed", "no sound" or "where do I override this config"

---

### When not to activate

- CachyOS kernels, the v3 repositories, `chwd`, the NVIDIA module packages, Limine or `cachyos-settings`, use `cachyos`
- Plasma panels, widgets, KWin, shortcuts, themes or konsave, use `kde-plasma`
- Writing an Ansible role that provisions Arch hosts, use `ansible`
- A shell script that happens to call pacman, use `bash` for the script itself

---

### Related skills

- `cachyos` owns everything a CachyOS host adds on top of Arch
- `kde-plasma` owns the Plasma desktop configuration
- `ansible` owns provisioning the same changes reproducibly
- `bash` owns scripts that wrap these commands
- The `security-auditor` agent owns judging whether an AUR package or a third party repository is trustworthy enough
