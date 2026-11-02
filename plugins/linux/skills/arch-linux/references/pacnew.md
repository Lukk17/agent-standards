# .pacnew and .pacsave Files

Read this when pacman prints "installed as /etc/...pacnew", when `pacdiff -o` lists files, or before any change to `/etc/pacman.conf` or a mirrorlist. The rules live in [SKILL.md](../SKILL.md).

---

### What they are

1. `file.pacnew`: the package ships a new default of a configuration file you changed. Pacman keeps your version and writes the new default beside it.
2. `file.pacsave`: you removed a package whose configuration you had changed. Pacman saved your copy.
3. Neither is applied automatically. A `.pacnew` nobody merges leaves a live file that lacks new options, and sometimes breaks after a major version change.

---

### Find them

Read-only, no root needed:

```bash
pacdiff -o
```

For one pair: `diff -u /etc/<file> /etc/<file>.pacnew`. Read the pacman output right after an upgrade as well, which is where new ones are announced.

---

### Check whether the live file was ever changed

`pacman -Qii <pkg>` ends with a "Backup Files" list that marks each file `[modified]` or `[unmodified]`. An unmodified live file can simply take the new default. A modified one carries the owner's deliberate changes and is merged by hand. Find the owning package with `pacman -Qo /etc/<file>`.

---

### Merge procedure

1. Snapshot first, see [snapper-rollback.md](snapper-rollback.md).
2. Diff the pair and decide per hunk. The live file carries the owner's changes, the `.pacnew` carries new defaults and new options.
3. Keep a copy of the live file, then port the wanted new options into it by hand, with the owner's approval. The owner runs `sudo cp -a /etc/<file> /etc/<file>.bak.$(date +%s)` and the edit.
4. Delete the `.pacnew` after merging, so the next listing means something: `sudo rm /etc/<file>.pacnew`.
5. `pacdiff` merges interactively, with `-s` to use sudo and `-b` to keep a backup. Its default diff program opens an editor an agent cannot drive, so it runs only in the owner's terminal.

Never overwrite a modified live file with its `.pacnew`.

---

### Files that are dangerous to replace

Discover which of these exist on the machine and record the decision in `MACHINE.md`.

| File | Why the live version usually stays |
|---|---|
| `/etc/pacman.conf` | On a derivative, the `.pacnew` is often the stock Arch file. Replacing the live file drops the derivative's repositories and any enabled `multilib`, silently moving the system to different packages. Port new options only |
| `/etc/pacman.d/*mirrorlist` | A ranked or generated list is better than the shipped static one. Read the header: if a tool wrote it, delete the `.pacnew` and keep the live list |
| `/etc/resolv.conf` | Usually written by NetworkManager or systemd-resolved. The `.pacnew` is a blank template, delete it |
| `/etc/fstab`, `/etc/crypttab`, `/etc/mkinitcpio.conf` | Boot depends on them. Merge with a snapshot and a recovery route ready |
