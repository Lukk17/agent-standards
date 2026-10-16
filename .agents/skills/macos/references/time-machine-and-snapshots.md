# Time Machine and APFS Local Snapshots

Read this before a risky change, to make sure there is a way back, and when the owner wants to restore. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Sources: the `tmutil(8)` man page as shipped with Xcode 27.2 beta 2, read through `https://keith.github.io/xcode-man-pages/tmutil.8.html`, and Apple Support "About Time Machine local snapshots", both fetched on 2026-10-13.

---

### What exists

1. Time Machine backs up to a destination disk or network volume. Read its configuration with `tmutil destinationinfo` and the latest backup with `tmutil latestbackup`.
2. Local snapshots are APFS snapshots of the startup volume kept on the Mac itself. Apple Support: "Time Machine saves one snapshot of your startup disk approximately every hour, and keeps it for 24 hours", and "Time Machine automatically deletes snapshots as they age or as space is needed for other things."
3. A local snapshot lives on the same disk it protects, so it is a short term undo, not a backup. Confirm a real backup exists before a change that could cost data.

The man page: "Several, but not all, verbs require root and Full Disk Access privileges. Full Disk Access privileges can be granted to the Terminal". The owner grants that, see [gatekeeper-and-tcc.md](gatekeeper-and-tcc.md).

---

### Read

```bash
tmutil listlocalsnapshots /
```

```bash
tmutil listlocalsnapshotdates /
```

```bash
diskutil apfs listSnapshots /
```

`listlocalsnapshotdates` prints dates "formatted YYYY-MM-DD-HHMMSS", which is the form `deletelocalsnapshots` takes.

---

### Take a snapshot before a change

From the man page, `localsnapshot` will "Create new local Time Machine snapshots of all APFS volumes included in the Time Machine backup."

```bash
tmutil localsnapshot
```

Read the snapshot list back afterwards and name the new snapshot in the `MACHINE.md` change log. Start a full backup when one is configured and the change is large, run by the owner:

```bash
tmutil startbackup --block
```

---

### Free space held by snapshots

Deleting a local snapshot removes a restore point, so it is the owner's decision.

```bash
tmutil deletelocalsnapshots <YYYY-MM-DD-HHMMSS>
```

`thinlocalsnapshots <mount_point> [purge_amount] [urgency]` asks the system to reclaim space by thinning snapshots. macOS also thins them on its own when space runs low, so a full disk is rarely a reason to delete them by hand.

---

### Restore

Restoring individual files is done in the Time Machine browser or by copying out of a mounted backup. Restoring the whole system is done from macOS Recovery, which the owner starts at boot. An agent does not drive either.
