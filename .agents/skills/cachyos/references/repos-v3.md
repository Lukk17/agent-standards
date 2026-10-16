# Repositories and the ISA Level

Read this before editing `/etc/pacman.conf`, adding or removing a repository, changing mirrors, or when someone suggests v4, znver4 or "converting" the machine. The rules live in [SKILL.md](../SKILL.md).

---

### Discover what is configured

`pacman-conf --repo-list` prints the active repositories in order and is the way to check, never a pasted snippet. On a v3 install the order is:

```text
cachyos-v3
cachyos-extra-v3
cachyos-core-v3
cachyos
core
extra
multilib
```

1. The optimized repositories hold Arch packages rebuilt for one instruction set level. They must sit above `[core]` and `[extra]`, because pacman takes a package from the first repository that has it, and the order is what makes the optimized builds win.
2. `[cachyos]` holds CachyOS specific packages: kernels, `chwd`, the settings packages, the scx and Ananicy pieces, and a CachyOS build of pacman itself. Check with `pacman -Qi pacman | grep -E 'Version|Packager'`, and never replace it with the Arch build.
3. `[multilib]` is needed for Steam and Wine. Check whether it is enabled in the live file before touching anything.
4. Each set reads its own mirrorlist under `/etc/pacman.d/`, named in the `Include` lines of `pacman.conf`.

---

### The ISA question

The CachyOS wiki page "Optimized Repositories" (`https://wiki.cachyos.org/features/optimized_repos/`, fetched 2026-10-13) defines three sets:

| Set | Repositories | Detection |
|---|---|---|
| x86-64-v3 | `[cachyos-v3]`, `[cachyos-core-v3]`, `[cachyos-extra-v3]`, plus `[cachyos]` | `/lib/ld-linux-x86-64.so.2 --help \| grep supported` lists `x86-64-v3 (supported, searched)` |
| x86-64-v4 | `[cachyos-v4]`, `[cachyos-core-v4]`, `[cachyos-extra-v4]`, plus `[cachyos]` | the same command lists `x86-64-v4 (supported, searched)` |
| znver4 | `[cachyos-znver4]`, `[cachyos-core-znver4]`, `[cachyos-extra-znver4]` | AMD Zen 4 or Zen 5 only, `gcc -march=native -Q --help=target` reports `znver4` or `znver5` |

The same page warns that Intel 12th generation and newer may report v4 while being unable to run AVX-512: "these CPUs should be treated as x86-64-v3 only."

1. Record the detected level in `MACHINE.md`. A CPU that does not list a level cannot use that set.
2. A different level is a reinstall of every package, not a one-line switch. The wiki's own migration step is "Reinstall all packages to switch to the new architecture", using `pacman -Qqn | sudo pacman -S -`. Read the page live before planning it, including how it handles the database refresh, and never reproduce its steps from memory.
3. AUR and `-bin` packages are not ISA optimized, and foreign packages (`pacman -Qm`) are unaffected by the repository level.
4. An installed but unused mirrorlist for another level, and its `.pacnew`, are harmless clutter.

---

### Rules for edits to pacman.conf

1. Snapshot first, and keep a copy: the owner runs `sudo cp -a /etc/pacman.conf /etc/pacman.conf.bak.$(date +%s)`.
2. The `.pacnew` next to it is usually the stock Arch file and would remove the CachyOS repositories and multilib. Never move it over the live file. Port new options by hand, as the `arch-linux` skill describes.
3. Never put `[core]` above the CachyOS repositories. Keep `[cachyos]`, `[core]`, `[extra]` and, where enabled, `[multilib]`.
4. A change in the repository set is followed by the full upgrade rule: `sudo pacman -Syu`. Never `-Sy` alone.
5. Do not add third party repositories. A personal repository is a source of root-installed code, and signing its key locally with `pacman-key --lsign-key` makes pacman trust whatever that key signs. Reject suggestions to add one for convenience, including repositories that ship agent skill packages.
6. Do not run `cachyos-repo.sh` on a machine that already has the CachyOS repositories. It exists to add them to a plain Arch install, and running it again rewrites `pacman.conf`.

---

### Mirrors

Read the header of each mirrorlist to see whether a tool generated it. CachyOS ships `cachyos-rate-mirrors` (package `cachyos-rate-mirrors`) as its wrapper. Regenerate with the tool that wrote the file and read its `--help` first, rather than hand-editing. The `arch-linux` skill covers mirror 404s.

---

### Checks

1. Which repository a package comes from: `pacman -Si <pkg> | grep -E '^(Repository|Version)'`. A package can exist in both an optimized repository and `[cachyos]` at different versions, and pacman picks the first.
2. Keys: `pacman -Q cachyos-keyring archlinux-keyring`, updated by the normal `-Syu`.
