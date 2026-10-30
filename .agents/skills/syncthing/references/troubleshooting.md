# Troubleshooting

Contents:

- [Read the errors first](#read-the-errors-first)
- [A folder shows Stopped](#a-folder-shows-stopped)
- [insufficient space on disk for database](#insufficient-space-on-disk-for-database)
- [A peer shows 0 global files with sequence 0](#a-peer-shows-0-global-files-with-sequence-0)
- [Log lines and what they mean](#log-lines-and-what-they-mean)

Read this before explaining a folder that shows Stopped, a disk space error, a peer that shows 0 files, or a warning in the log. The rules live in [SKILL.md](../SKILL.md). Commands marked VERIFIED ran on Syncthing 2 in throwaway containers. Every other command here, every PowerShell command included, is UNVERIFIED.

Sources: https://docs.syncthing.net/rest/system-error-get.html, https://docs.syncthing.net/rest/folder-errors-get.html, https://docs.syncthing.net/rest/db-completion-get.html, https://docs.syncthing.net/users/config.html, and in `syncthing/syncthing`: `lib/model/folder.go`, `lib/config/size.go` and `gui/default/syncthing/core/syncthingController.js`.

---

### Read the errors first

The examples below keep the API key in `$st_key` and send it on standard input, as [cli-and-rest.md](cli-and-rest.md) shows.

The recent error list, the same data as `GET /rest/system/error`. VERIFIED:

```bash
syncthing cli errors show
```

The state of one folder: `state`, `error`, `globalFiles`, `localFiles`, `needFiles`, `sequence`. VERIFIED:

```bash
printf 'X-API-Key: %s\n' "$st_key" | curl -s -H @- "http://127.0.0.1:8384/rest/db/status?folder=<folder-id>"
```

```powershell
"X-API-Key: $stKey" | curl.exe -s -H '@-' "http://127.0.0.1:8384/rest/db/status?folder=<folder-id>"
```

Per file errors from scanning or pulling, which the folder errors page describes as "the list of errors encountered during scanning or pulling". VERIFIED:

```bash
printf 'X-API-Key: %s\n' "$st_key" | curl -s -H @- "http://127.0.0.1:8384/rest/folder/errors?folder=<folder-id>"
```

On Linux the log of the user unit, on macOS the Homebrew log:

```bash
journalctl -e --user-unit=syncthing.service
```

```bash
tail -n 100 "$(brew --prefix)/var/log/syncthing.log"
```

---

### A folder shows Stopped

The web page shows a folder in the `error` state as Stopped. The GUI code says it outright: `return 'stopped'; // legacy, the state is called "stopped" in the GUI`. So read `error` from `/rest/db/status`, which says why.

---

### insufficient space on disk for database

The full message, reproduced by raising the threshold above the free space in a container:

```text
insufficient space on disk for database (<config-dir>/index-v2): current 17.42 % < required 99.99 %
```

What it means, read in `lib/model/folder.go`: before a folder may work, Syncthing checks the free space of the disk that holds its database against `options.minHomeDiskFree`, and if it is below, the folder goes to the `error` state, which shows as Stopped. The configuration page defines `minHomeDiskFree` as "The minimum required free space that should be available on the partition holding the configuration and index", and its default is 1 %. Every folder on the device stops at once, because they share that database disk, even when the folders themselves live on another disk with plenty of space.

The fix is space on that disk, never a lower threshold. A disk at 1 % free is about to stop more than Syncthing.

1. Find the database directory from `syncthing paths`, or from the path in the message.
2. Measure the disk under it.

```bash
df -h ~/.local/state/syncthing
```

```powershell
Get-Volume -DriveLetter ($env:LOCALAPPDATA.Substring(0,1))
```

3. Free space on that disk, or grow it. For a Proxmox guest, growing the virtual disk and then the partition and file system inside the guest is in the `proxmox` skill.
4. Ask for a rescan, which re-runs the check, then read the folder state again. Measured: after the free space was above the threshold again, the folder went back to `idle` with an empty `error`. VERIFIED:

```bash
printf 'X-API-Key: %s\n' "$st_key" | curl -s -X POST -H @- "http://127.0.0.1:8384/rest/db/scan?folder=<folder-id>"
```

A folder's own `minDiskFree` is a second, separate check on the disk the folder lives on. The configuration page says: "The folder will be stopped when the value drops below the threshold." The same rule holds: free the disk, do not lower the value.

---

### A peer shows 0 global files with sequence 0

`/rest/db/status` on the receiving side reading `globalFiles` 0 and `sequence` 0 while the sending side has files means no index from the sender has arrived. The cause is on the other side or between the two, so check, in this order:

1. Both devices are connected, `syncthing cli show connections`, see [connections.md](connections.md).
2. The other side has the folder at all. On the other device, `syncthing cli show pending folders` lists a folder it was offered and never added, and its log says `Unexpected folder ID in ClusterConfig`.
3. The other side shares it back. From the sending side, ask for the receiving device's view. The completion page says `remoteState` is "`unknown` when the remote device is not connected. Otherwise it can be either `paused`, `notSharing`, or `valid` if the remote is sharing back."

```bash
printf 'X-API-Key: %s\n' "$st_key" | curl -s -H @- "http://127.0.0.1:8384/rest/db/completion?folder=<folder-id>&device=<device-id>"
```

4. The other side's folder is not stopped or paused. Read its `/rest/db/status` on that device: an `error` state there, a disk space error included, means it sends nothing.

---

### Log lines and what they mean

| Line | Meaning | Where it is handled |
|---|---|---|
| `Remote is an introducer to us, and we are to them` | both sides marked each other as introducer | [folders-and-devices.md](folders-and-devices.md) |
| `Failed to create path for auto-accepted folder` | auto accept is on and the default folder path is empty or not writable | [folders-and-devices.md](folders-and-devices.md) |
| `Connection rejected ... error="unknown device"` | the peer is not configured here yet, it sits under pending devices | [folders-and-devices.md](folders-and-devices.md) |
| `Unexpected folder ID in ClusterConfig` | the peer shares a folder that is not added or not shared back here | [folders-and-devices.md](folders-and-devices.md) |
| `insufficient space on disk for database` | the database disk is below `minHomeDiskFree` | this page |
| a relay listener `Service failed` with a DNS error | no internet access, harmless on a LAN-only device | [connections.md](connections.md) |

All six lines in that table appeared in the container logs.
