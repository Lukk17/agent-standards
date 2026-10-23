---
name: arch-linux
description: 'Package and system administration on Arch Linux and Arch based distributions: pacman, the AUR with paru or yay, makepkg and PKGBUILD review, full upgrades and the pre-upgrade news check, partial upgrades and mirror 404s, .pacnew and .pacsave merging, orphans and cache cleanup, snapper snapshots and rollback, systemd units and journal triage, coredump crash diagnosis, PipeWire and WirePlumber audio, and editing configuration without touching packaged files. Use when you say "pacman -Syu", "install this from the AUR", "failed retrieving file", "unable to satisfy dependency", "No module named build", "what is this pacnew", "free up disk space", "clean up leftovers", "roll back the upgrade", "this service failed", "the program crashed", "no sound", or "where do I override this config". Not for CachyOS kernels, v3 repositories, chwd or Limine, use `cachyos`, and not for Plasma panels, widgets or themes, use `kde-plasma`.'
---

# Arch Linux Administration

How to change an Arch based system without leaving it half upgraded, without editing what a package owns, and without losing the way back. Generic Arch knowledge applies everywhere. Derivatives add their own layer, so check which one the machine runs before applying a recipe.

Baseline: Arch Linux rolling, pacman 7, PipeWire 1.6 with WirePlumber 0.5, verified on one CachyOS host on 2026-10-13. Commands that were not executed are marked UNVERIFIED in the topic files.

| You are about to | Open |
|---|---|
| Install, remove, upgrade, downgrade or query a package | [pacman-discipline.md](references/pacman-discipline.md) |
| Run `pacman -Syu`, or tell the owner to | [upgrade-preflight.md](references/upgrade-preflight.md) |
| See a 404, "failed retrieving file", "unable to satisfy dependency", a missing `.so` | [partial-upgrade-and-404.md](references/partial-upgrade-and-404.md) |
| Find `.pacnew` or `.pacsave` files, or an upgrade printed one | [pacnew.md](references/pacnew.md) |
| Use paru, yay or makepkg, read a PKGBUILD, see "No module named build" | [aur-and-makepkg.md](references/aur-and-makepkg.md) |
| Free disk space, clean up leftovers with `scripts/cleanup-leftovers.sh`, remove orphans, prune the pacman cache | [orphans-and-cleanup.md](references/orphans-and-cleanup.md) |
| Take a snapshot, undo a change, roll back a bad upgrade | [snapper-rollback.md](references/snapper-rollback.md) |
| Read a failed service, a slow boot, the journal, change a unit | [systemd-journal-triage.md](references/systemd-journal-triage.md) |
| Explain a crash, a segfault, a coredump | [crash-diagnosis.md](references/crash-diagnosis.md) |
| Fix no sound, the wrong output, a volume that resets | [pipewire-wireplumber.md](references/pipewire-wireplumber.md) |
| Edit any configuration file, use root, write a pacman hook | [config-safety.md](references/config-safety.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`: disks and mounts, volumes that must never be touched, the bootloader, the snapshot setup, custom fixes, and the change log. Read it before acting. This skill carries no facts about any single machine. Where a topic file says to discover something, run the command, compare the answer with `MACHINE.md`, and report a disagreement rather than picking one silently.

---

### When to activate

- Any pacman, paru, yay or makepkg command, including a read-only query
- An upgrade, a downgrade, or a download error from a mirror
- A `.pacnew` or `.pacsave` file, or a change under `/etc`
- Disk space, orphans, caches, snapshots or a rollback
- A failed systemd unit, a journal question, a crash, a coredump
- Any audio problem on PipeWire, WirePlumber or ALSA

---

### When not to activate

- CachyOS kernels, the v3 repositories, `chwd`, the NVIDIA module packages, Limine or `cachyos-settings`, use `cachyos`
- Plasma panels, widgets, KWin, shortcuts, themes or konsave, use `kde-plasma`
- Writing an Ansible role that provisions Arch hosts, use `ansible`
- A shell script that happens to call pacman, use `bash` for the script itself

---

### Hard rules

1. Upgrade the whole system, then install. Never `pacman -Sy <pkg>` and never `pacman -Sy` alone.
2. The agent does not run `sudo`. Print the command with what it changes, and the owner runs it. In Claude Code the `!` prefix runs a command in the owner's session, where the password prompt works.
3. Snapshot before a risky change, using the snapshot tool `MACHINE.md` names.
4. Never edit a file a package owns. Override in `/etc` drop-ins or under `~`.
5. Read every PKGBUILD and `.install` file before building from the AUR.
6. Record every system change in the change log of `MACHINE.md`, with how to undo it.
7. Measure the live system before answering. Use `pacman -Qi`, `pacman -Ql`, `man`, and the offline Arch Wiki through `wiki-search` where `arch-wiki-lite` is installed, rather than memory.

---

### Related skills

- `cachyos` owns everything a CachyOS host adds on top of Arch
- `kde-plasma` owns the Plasma desktop configuration
- `ansible` owns provisioning the same changes reproducibly
- `bash` owns scripts that wrap these commands
- `security-review` owns judging whether an AUR package or a third party repository is trustworthy enough

---

### Checklist

- [ ] `MACHINE.md` read before the first change
- [ ] News checked and pending updates listed before any full upgrade
- [ ] No `-Sy` without `u`, no `--overwrite '*'`, no `-Rdd`, no `IgnorePkg` used to dodge an error
- [ ] Every root command handed to the owner, never run by the agent
- [ ] Snapshot taken before kernel, bootloader, initramfs, fstab or bulk removal work
- [ ] No packaged file edited, every override placed in a drop-in
- [ ] Every PKGBUILD read before building
- [ ] The change and its undo recorded in the `MACHINE.md` change log
