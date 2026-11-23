---
name: arch-linux
description: 'Arch Linux administration: pacman, the AUR, upgrades, .pacnew files, cleanup, rollback, journal and audio. Use when the user says "pacman -Syu" or "what is this pacnew". Not for CachyOS kernels, use `cachyos`.'
metadata:
  version: "1.1.0"
---

# Arch Linux Administration

How to change an Arch based system without leaving it half upgraded, without editing what a package owns, and without losing the way back. Generic Arch knowledge applies everywhere. Derivatives add their own layer, so check which one the machine runs before applying a recipe.

Written for Arch Linux rolling, pacman 7, PipeWire 1 with WirePlumber 0.5.

The commands that ran were run on one CachyOS host, and commands that were not executed are marked UNVERIFIED in the topic files.

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
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Call a change done | [checklist.md](references/checklist.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`. Read it before acting. This skill holds no facts about any single machine.

For this skill they are the disks and mounts, volumes that must never be touched, the bootloader, the snapshot setup, custom fixes, and the change log. Where a topic file says to discover something, run the command, compare the answer with `MACHINE.md`, and report a disagreement rather than picking one silently.

---

### When not to activate

- CachyOS kernels, the v3 repositories, `chwd`, the NVIDIA module packages, Limine or `cachyos-settings`, use `cachyos`
- Plasma panels, widgets, KWin, shortcuts, themes or konsave, use `kde-plasma`
- A shell script that happens to call pacman, use `bash` for the script itself

---

### Hard rules

1. Upgrade the whole system, then install. Never `pacman -Sy <pkg>` and never `pacman -Sy` alone.
2. The agent does not run `sudo`. Print the command with what it changes, and the owner runs it.
3. Snapshot before a risky change, using the snapshot tool `MACHINE.md` names.
4. Never edit a file a package owns. Override in `/etc` drop-ins or under `~`.
5. Read every PKGBUILD and `.install` file before building from the AUR.
6. Record every system change in the change log of `MACHINE.md`, with how to undo it.
7. Measure the live system before answering. Use `pacman -Qi`, `pacman -Ql`, `man`, and the offline Arch Wiki through `wiki-search` where `arch-wiki-lite` is installed, rather than memory.
