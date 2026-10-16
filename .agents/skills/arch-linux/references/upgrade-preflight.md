# Pre-upgrade Check

Read this before the owner runs `pacman -Syu`, and before you recommend it. Some upgrades need a manual step that Arch News announces first, and the check takes two minutes. The rules live in [SKILL.md](../SKILL.md).

---

### Steps

1. Read the news since the last full upgrade. The feed is plain RSS at `https://archlinux.org/feeds/news/`. The script in this skill's `scripts/` folder filters it by date and flags titles that look like they need action. Run it from the skill folder:

```bash
python3 -I scripts/arch-news-since.py
```

2. Pass a date to look further back, for example `python3 -I scripts/arch-news-since.py 2026-09-01`. The feed holds only the most recent items, so for a gap of many months read the archive at `https://archlinux.org/news/`.
3. List what is pending without root and without touching the real database: `checkupdates`. Count the packages, and look for names that match a news item, such as the kernel, systemd, mkinitcpio, glibc, a GPU driver, Plasma, Python, the bootloader, openssl or pacman.
4. Open every item flagged `ACTION`, read it fully, and decide whether it applies to this machine using `MACHINE.md` and live queries. A title match is not an answer. State one line per item: applies, does not apply, or cannot tell and why.
5. If something looks suspicious, search the forum board "Pacman & Package Upgrade Issues" at `https://bbs.archlinux.org/viewforum.php?id=44` for the package name, newest replies first.
6. On a derivative, also read its own news, which the Arch feed does not cover. The `cachyos` skill names the CachyOS sources.
7. Make sure there is room: `df -h /`, and on btrfs `sudo btrfs filesystem usage /` run by the owner, because btrfs `df` can mislead, see [orphans-and-cleanup.md](orphans-and-cleanup.md).
8. Only then give the owner `sudo pacman -Syu`, or `paru -Syu` to include the AUR after reading [aur-and-makepkg.md](aur-and-makepkg.md).
9. Afterwards, read the tail of the output for `.pacnew` messages, see [pacnew.md](pacnew.md), check `systemctl --failed`, and note whether a reboot is needed. A new kernel, systemd, glibc or GPU kernel module takes effect only after a reboot. Compare `uname -r` with the installed kernel package version.
10. Add one change log entry to `MACHINE.md`.

---

### When the last upgrade was long ago

A gap of many months is where upgrades fail: expired keys, replaced packages, and several manual interventions at once. Do not refresh only the keyring with `pacman -Sy`, which is a partial upgrade. If signature errors appear, read the Arch Wiki page on package signing (`wiki-search "pacman/package signing"`) and follow it. For a gap of over a year the cautious route is to upgrade in steps from dated snapshots of the Arch Linux Archive, `https://archive.archlinux.org/`. That route is UNVERIFIED here. Take a snapshot first and ask the owner before choosing it.

---

### What this check does not cover

1. News is written by hand, and breakage can happen with no news item. The check lowers risk, which is why the pre-transaction snapshot matters more.
2. AUR packages are outside the Arch news. They break on their own schedule, usually after a library changes its soname. Expect to rebuild them after a large Qt, KDE Frameworks, Python, ICU or Boost upgrade.
3. Mirror state is outside the news. A mirror caught mid-sync is the commonest real failure, see [partial-upgrade-and-404.md](partial-upgrade-and-404.md).
