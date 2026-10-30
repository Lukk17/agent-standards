# Orphans, Caches and Freeing Disk Space

Contents:

- [Real leftovers only](#real-leftovers-only)
- [Phase 1: scan](#phase-1-scan)
- [Btrfs and snapshots change the arithmetic](#btrfs-and-snapshots-change-the-arithmetic)
- [Phase 2: report](#phase-2-report)
- [Phase 3 and 4: confirm, then clean](#phase-3-and-4-confirm-then-clean)
- [Orphans](#orphans)
- [Docker](#docker)

Read this before removing orphan packages, pruning the pacman cache, deleting caches, or when the disk looks full. The rules live in [SKILL.md](../SKILL.md).

The order of work: scan without deleting, report sizes, get confirmation per group, delete only what was confirmed, then measure again.

---

### Real leftovers only

The default cleanup removes only what nothing on the machine uses any more. Caches of tools in use are not leftovers: JetBrains caches of installed IDEs, Gradle, npm, Cargo and browser caches stay, and this procedure does not touch them. Stopped Docker containers, named images and volumes stay too. The phases further down this page are for when the owner asks for more than leftovers.

| Group | What counts as a leftover | How it is removed |
|---|---|---|
| a | Pacman cache files of packages no longer installed, and old versions beyond the last 2 | `sudo paccache -ruk0` and `sudo paccache -rk2` |
| b | Orphans from `pacman -Qtdq`, without anything matching `linux*`, `*-ucode`, `linux-firmware*`, `nvidia*`, `mkinitcpio*`, `limine*`, `plymouth*`, `systemd*` or `snap*`, which are listed as kept | `sudo pacman -Rns <names>`, no `--noconfirm` |
| c | AUR build folders in `~/.cache/paru/clone` whose package is no longer installed. The `pkgbase` and every `pkgname` in the folder's `.SRCINFO` are matched against `pacman -Qq`, so a split package folder stays while any of its packages is installed. A folder without `.SRCINFO` stays. The group is skipped while a `makepkg` or `paru` process runs | the folder is deleted |
| d | Docker dangling images that no container uses, and the build cache | `docker image prune` without `-a`, and `docker builder prune` |
| e | Flatpak runtimes no app needs | `flatpak uninstall --unused`, which lists and asks itself |
| f | JetBrains version folders such as `~/.cache/JetBrains/IntelliJIdea2025.3`, also under `~/.local/share/JetBrains` and `~/.config/JetBrains`, of an IDE version that is no longer installed. Installed versions are the `dataDirectoryName` values in `product-info.json` under the Toolbox install location from `~/.local/share/JetBrains/Toolbox/.settings.json`, `/opt`, `/usr/share`, `/usr/lib` and `/snap`. Toolbox and every other folder stay, and the group is skipped when no installed IDE is found | each folder is asked one by one |
| g | Trash in `~/.local/share/Trash` only, not the trash folders on other drives | the content of `files`, `info` and `expunged` in that folder is deleted, never `gio trash --empty`, which also empties the trash on other drives |
| h | Thumbnails in `~/.cache/thumbnails` whose original file no longer exists, read from the `Thumb::URI` text chunk (`tEXt` or `zTXt`), `file://` only. A file on a drive that is not mounted counts as missing, and its thumbnail is made again on the next view | the thumbnail files are deleted |

The script [scripts/cleanup-leftovers.sh](../scripts/cleanup-leftovers.sh) does all eight groups. A group whose tool is missing is skipped with one line saying so.

1. Scan first. It prints one line per group with what was found and its size, and removes nothing. Flatpak has no dry run, so the scan only counts its runtimes.

```bash
bash scripts/cleanup-leftovers.sh
```

2. The owner runs the clean himself, as his own user. Each group with something in it shows its items and the size, asks `Remove? [y/N]`, and removes only on `y`. Steps that need root call `sudo` after the `y`, so the password prompt appears in the owner's terminal.

```bash
bash scripts/cleanup-leftovers.sh --clean
```

3. The agent runs only the scan. It never runs `--clean` and never runs `sudo`.
4. Run the scan again afterwards and report what changed.

The tests run in throwaway containers with no network and no host folder mounted, and need Docker:

```bash
bash scripts/tests/run-tests.sh
```

---

### Phase 1: scan

Read-only, no root. Run these and report the numbers.

```bash
df -h / /home
```

```bash
paccache -d
```

```bash
paccache -d -k1
```

```bash
paccache -d -u -k0
```

```bash
pacman -Qtdq
```

```bash
journalctl --disk-usage
```

```bash
coredumpctl list --no-pager
```

```bash
du -sh ~/.cache/* 2>/dev/null | sort -rh | head -15
```

Also measure `~/.npm`, `~/.gradle`, `~/.cargo`, `~/.m2` and `~/.local/share/Trash` with `du -sh`, and run `docker system df` and `flatpak list --runtime` where those tools exist. IDE caches under `~/.cache` are often the largest single item on a developer machine.

---

### Btrfs and snapshots change the arithmetic

On btrfs with snapshots, deleting a file that a snapshot still references frees no space, and `df` shows the filesystem as a whole without explaining it. Check the filesystem type with `findmnt -no FSTYPE /`.

1. Real usage: `sudo btrfs filesystem usage /`, run by the owner.
2. Snapshots: `sudo snapper list-configs` and `sudo snapper -c <config> list`, run by the owner where listing needs root. Old snapshots are removed by the cleanup timer, or by `sudo snapper -c <config> delete <number>` after the owner agrees. Deleting a snapshot removes a rollback point, which is why it is the owner's decision.
3. After deleting snapshots, space returns gradually while btrfs frees extents in the background.
4. A subvolume without a snapper config, often `/home`, frees space immediately. `MACHINE.md` records which subvolumes have snapshots.
5. Root snapshots keep old Docker data in `/var/lib/docker` and `/var/lib/containerd`, so pruning Docker frees space only after those snapshots go.

---

### Phase 2: report

Group the findings and give a size per group, so the owner can choose:

1. System and packages: pacman cache, orphans, journal, coredumps.
2. User and application caches: `~/.cache`, Trash, browser caches.
3. Developer caches: Gradle, npm, Cargo, Go build cache, Maven, IDE caches.
4. Containers: Docker, Flatpak, snaps.
5. Large personal files, listed and never recommended for deletion.

---

### Phase 3 and 4: confirm, then clean

Delete only what the owner confirmed, by exact path. Root actions go to the owner.

| Target | Command | Notes |
|---|---|---|
| Old package versions | `sudo paccache -r` keeps three, `sudo paccache -rk2` keeps two | Keep at least two for downgrades. Never `pacman -Scc`, which empties the whole cache |
| Uninstalled packages | `sudo paccache -ruk0` | |
| Orphans | see below | never automatic |
| Journal | `sudo journalctl --vacuum-size=200M` | measure first, it is often small |
| Coredumps | `sudo rm -- /var/lib/systemd/coredump/<named file>` | `coredumpctl` has no delete verb, old dumps age out through systemd-tmpfiles, and a dump can hold secrets, see [crash-diagnosis.md](crash-diagnosis.md) |
| JetBrains caches | the IDE's Invalidate Caches, or JetBrains Toolbox | deleting `~/.cache/JetBrains` under a running IDE corrupts its indexes, close the IDE first |
| Gradle | `rm -rf ~/.gradle/caches/build-cache-*`, or `~/.gradle/caches/modules-2` with no Gradle daemon running (`pgrep -a java`) | re-downloads on the next build |
| npm | `npm cache clean --force` | |
| Cargo | `rm -rf ~/.cargo/registry/cache ~/.cargo/registry/src ~/.cargo/git` | |
| Go | `go clean -cache`, `go clean -modcache` | |
| Browsers | only the cache directories under `~/.cache`, with the browser closed | never a profile directory under `~/.config` or `~/.mozilla` |
| Trash | `rm -rf -- ~/.local/share/Trash/files/* ~/.local/share/Trash/info/*` | show the content first, Trash is the last chance to recover |
| Flatpak | `flatpak uninstall --unused` | lists first, asks |
| AUR helper build state | `~/.cache/paru` or `~/.cache/yay` | only when no build is running |

Rules for every deletion: quote paths, put `--` before them, never use a glob that could expand to `~` or `/`, and check the path exists and is the expected type first. If one deletion fails, report it and continue with the rest of the confirmed list.

---

### Orphans

`pacman -Qtdq` lists packages installed as dependencies that nothing requires any more.

1. Show the list with sizes before anything is removed: `pacman -Qi $(pacman -Qtdq) | grep -E '^(Name|Installed Size)'`. An empty list must not be passed on, pacman prints an error.
2. Check each one for a reason to be there: AUR makedepends (see [aur-and-makepkg.md](aur-and-makepkg.md)), a package the owner installed with `--asdeps` by mistake, a kernel module or driver pair.
3. Never remove anything named `linux*`, `*-ucode`, `linux-firmware*`, a GPU driver or its utilities, `mkinitcpio*`, the bootloader's packages, `snap*`, `plymouth*` or `systemd*` as an orphan.
4. Keep a package the owner may want by marking it explicit: `pacman -D --asexplicit <pkg>`.
5. Remove with `sudo pacman -Rns <names>` and no `--noconfirm`, so pacman shows the dependents before acting.

---

### Docker

A development stack under Docker keeps its data in named volumes and recreates stopped containers empty. Safe and narrow, after showing sizes with `docker system df`: `docker image prune` for dangling images only, and `docker builder prune`.

Stopped containers always stay. `docker container prune` and `docker system prune` are never used, and `docker volume prune` only when the owner names exactly what goes.

With the containerd image store, images live in `/var/lib/containerd`, not in `/var/lib/docker`, and `docker info` shows `driver-type: io.containerd.snapshotter.v1`. Measure with `docker system df`, and the owner runs `sudo du -xsh /var/lib/containerd`.
