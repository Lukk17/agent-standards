# pacman Discipline

Read this before installing, removing, upgrading or downgrading anything with pacman, paru or yay. The rules live in [SKILL.md](../SKILL.md).

---

### The one rule

Arch supports only full upgrades. The repository databases and the installed system must move together.

1. `pacman -Syu` upgrades everything. Run it, then install.
2. `pacman -Sy <pkg>` refreshes the database and installs one package against an old system. Libraries the new package needs may be newer than the ones installed. Never do it.
3. `pacman -Sy` alone is the same mistake with the install postponed. Never do it.
4. `pacman -S <pkg>` without `-y` is fine only right after a `-Syu` in the same sitting. A database older than a few hours is a reason to upgrade first.

A derivative's own repositories are part of the same sync, so one `-Syu` covers them. Never upgrade only part of the repository set. List the active repositories with `pacman-conf --repo-list`.

The agent never runs these. Print the line for the owner, `! sudo pacman -Syu` in Claude Code, and do [upgrade-preflight.md](upgrade-preflight.md) first. If `snap-pac` is installed, every pacman transaction gets a pre and post snapshot on its own. Check with `pacman -Q snap-pac`.

---

### Install flow

1. Search: `pacman -Ss <term>` for the repositories, `paru -Ss <term>` to include the AUR. `pacman -Si <pkg>` shows the repository version, `pacman -Qi <pkg>` what is installed.
2. Run the preflight and the full upgrade above.
3. Install: `sudo pacman -S <pkg>`, run by the owner. Name every package. No `--noconfirm` unless the owner approved the exact package set.
4. Read the output for warnings, hook messages and `.pacnew` notices, see [pacnew.md](pacnew.md).
5. Verify with `pacman -Q <pkg>`, `pacman -Ql <pkg>`, and by running the program. Add a change log entry to `MACHINE.md`.

Mark packages correctly, because orphan cleanup relies on it. A library installed only to satisfy another package is a dependency: `pacman -D --asdeps <pkg>`. Something the owner wants is explicit: `pacman -D --asexplicit <pkg>`.

---

### Query cheat sheet

All read-only, none needs root.

| Question | Command |
|---|---|
| Which package owns this file? | `pacman -Qo /path` |
| What does the package contain? | `pacman -Ql <pkg>` |
| What does it depend on, and what needs it? | `pacman -Qi <pkg>`, fields Depends On and Required By |
| Which package provides this file, installed or not? | `pacman -F <file>`, needs a files database from `sudo pacman -Fy`, which does not touch the package database |
| Which packages are not from a repository? | `pacman -Qm` |
| Which packages were installed explicitly? | `pacman -Qe` |
| Are the installed files intact? | `pacman -Qk <pkg>` |
| What changed recently? | `grep -a -E '\[ALPM\] (installed\|upgraded\|removed)' /var/log/pacman.log \| tail -40` |
| When did the last full upgrade start? | `grep -a 'starting full system upgrade' /var/log/pacman.log \| tail -3` |
| Which repository does a package come from? | `pacman -Si <pkg>`, field Repository |
| What is pending, without root and without touching the real database? | `checkupdates` from `pacman-contrib`. `pacman -Qu` only reflects the last sync |

The line "starting full system upgrade" is written when an upgrade starts, so a cancelled or failed run leaves it too. Confirm with an `[ALPM] upgraded` line after it.

---

### Removing

1. `pacman -Rns <pkg>` removes the package, its unneeded dependencies and its configuration. Prefer `-Rs`, which keeps configuration, when unsure. Read the dependency list pacman prints before confirming.
2. Never `pacman -Rdd`, which ignores dependencies, unless the package is being replaced in the same step and the reason is stated.
3. Never remove the running kernel, its headers or its module packages outside a kernel procedure, and never remove `base`, `systemd`, `pacman` or `glibc`.

---

### Downgrading

Prefer a snapshot rollback, see [snapper-rollback.md](snapper-rollback.md).

For one package, the owner runs `sudo pacman -U /var/cache/pacman/pkg/<pkg>-<oldversion>-<arch>.pkg.tar.zst`. The old file exists only if the cache was not pruned. List candidates with `ls /var/cache/pacman/pkg | grep '^<pkg>-'`. The next `-Syu` upgrades a downgraded package again, and holding it with `IgnorePkg` produces a partial upgrade that grows worse each week. A downgrade needed for longer than a day goes into the `MACHINE.md` change log with the reason and a date to revisit.

---

### Locks and parallel runs

`error: failed to init transaction (unable to lock database)` means `/var/lib/pacman/db.lck` exists. Check `pgrep -a 'pacman|paru|yay'` first. Only when nothing runs is the lock stale, and removing it needs root and the owner's approval. A graphical software centre or a `paru` left open in another terminal are the usual holders.

---

### Pitfalls

1. `--overwrite '*'` hides file conflicts and can corrupt a package's files. Use a specific glob, and only when an Arch News item says so.
2. `--noconfirm` on a removal, or on a list built from a command substitution, removes a wrong list without a question.
3. Alternating between `yay` and `paru` leaves two caches and two review habits. Pick one.
4. Snaps and Flatpaks are updated by their own tools, not by pacman, and a pacman rollback does not touch them.
