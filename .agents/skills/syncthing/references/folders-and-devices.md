# Folders and Devices

Read this before setting the folder layout, pairing a device, adding or sharing a folder, or moving one. The rules live in [SKILL.md](../SKILL.md). Commands marked VERIFIED ran on Syncthing 2.1.7 between two throwaway containers on an isolated Docker network on 2026-10-23. Every other command here, every PowerShell command included, is UNVERIFIED.

Sources, fetched on 2026-10-23: https://docs.syncthing.net/users/config.html, https://docs.syncthing.net/users/foldertypes.html, https://docs.syncthing.net/advanced/folder-ignoredelete.html, https://docs.syncthing.net/users/introducer.html, https://docs.syncthing.net/users/faq.html, the 2.0.0 release notes at https://github.com/syncthing/syncthing/releases/tag/v2.0.0, and `lib/model/model.go` at tag v2.1.7.

---

### The layout

Every synced folder gets its own directory under one base, never the home folder itself:

| Platform | Base | One folder |
|---|---|---|
| Linux and macOS | `~/Documents/sync` | `~/Documents/sync/<folder-label>` |
| Windows | `%USERPROFILE%\Documents\sync` | `%USERPROFILE%\Documents\sync\<folder-label>` |

Point the default folder path at the base, so a folder accepted later lands there too. Syncthing expands a leading `~` to the home folder of the user it runs as: a folder added with the path `~/Documents/sync/<folder-label>` was created under the container user's home. VERIFIED, and in the measured 2.1.7 container the default path was empty before this:

```bash
syncthing cli config defaults folder path set '~/Documents/sync'
```

```powershell
syncthing cli config defaults folder path set "$env:USERPROFILE\Documents\sync"
```

```bash
syncthing cli config defaults folder path get
```

---

### The Default Folder from 1.x

The 2.0.0 release notes say: "A "default folder" is no longer created on first startup." A device that started on 1.x and was upgraded may still carry the folder with ID `default`, label `Default Folder`, at `~/Sync`. List the folders first. VERIFIED:

```bash
syncthing cli config folders list
```

When `default` is listed and the owner agrees, remove it from the configuration. This leaves the files on disk. The `delete` action was VERIFIED on another folder:

```bash
syncthing cli config folders default delete
```

Then delete `~/Sync` only when it holds nothing but the `.stfolder` marker. Each command below prints the other entries and prints nothing when the directory is safe to remove:

```bash
find ~/Sync -mindepth 1 -maxdepth 1 ! -name .stfolder
```

```powershell
Get-ChildItem -Force "$env:USERPROFILE\Sync" | Where-Object Name -ne '.stfolder'
```

Anything listed means the directory holds data. Stop and ask the owner what it is.

---

### Pair two devices

Both sides must add each other. Read this device's ID and give it to the other side. VERIFIED:

```bash
syncthing device-id
```

Add the other device. Without `--addresses` the address list is `dynamic`, which means discovery, and introducer and auto accept are false, VERIFIED by reading the new entry back:

```bash
syncthing cli config devices add --device-id <device-id> --name <device-name>
```

If the other side added this device first, it shows up here as a pending device, and the other side's log says `Connection rejected ... error="unknown device"` until this side adds it. VERIFIED:

```bash
syncthing cli show pending devices
```

Check that they connected. `connected` is true and `type` names the connection, see [connections.md](connections.md):

```bash
syncthing cli show connections
```

---

### Introducer and autoAcceptFolders stay off

An introducer hands its own device list to you. The introducer page says: "It is not a good idea to set two devices as introducers to each other. While this will work for adding devices, removing a device may present a problem, as the two devices will be constantly "re-introducing" the removed device to each other."

When both sides mark each other as introducer, both logs print this error. Read in `lib/model/model.go` and reproduced in the containers, where it appeared once the devices reconnected after a restart:

```text
Remote is an introducer to us, and we are to them - only one should be introducer to the other, see https://docs.syncthing.net/users/introducer.html
```

autoAcceptFolders lets a peer create folders here. The configuration page says such folders are "automatically added and synced locally under the default path", named after the remote label and then the folder ID. When the default path is empty, the path is that bare name, relative to the working directory of the Syncthing process. Measured in a container whose working directory was `/`, with the default path empty:

```text
Failed to create path for auto-accepted folder (folder.label=<folder-label> folder.id=<folder-id> path=<folder-label> error="mkdir /<folder-label>: permission denied" log.pkg=model)
```

Under a systemd user unit the working directory is the home folder, so the same accept succeeds and drops `<folder-label>` or `<folder-id>` straight into `~`. That is the mess the layout above prevents.

Read both settings, then set them to false on both sides. VERIFIED:

```bash
syncthing cli config devices <device-id> introducer get
```

```bash
syncthing cli config devices <device-id> introducer set false
```

```bash
syncthing cli config devices <device-id> auto-accept-folders set false
```

The introducer page says introductions are applied "when a device connects to an introducer", so a changed flag takes effect on the next connection. Restart when it has to apply now:

```bash
syncthing cli operations restart
```

---

### Add a folder by its folder ID

The folder ID is what makes two folders the same folder. The label is only shown locally and may differ, for example `photos` here and `photos-archive` on the peer, which was VERIFIED to sync. Copy the ID from the other side's `syncthing cli config folders list`, or let the side that creates the folder first choose one.

Add the folder with its type. Without `--type` it is `sendreceive`. VERIFIED:

```bash
syncthing cli config folders add --id <folder-id> --label <folder-label> --path '~/Documents/sync/<folder-label>' --type receiveonly
```

`syncthing cli config folders add` leaves the folder's free space check off: a folder added that way read back `minDiskFree` with value 0, while a folder created with `POST /rest/config/folders` on the same instance read back 1 %, the default. Both measured. Set it after every `add`. VERIFIED:

```bash
syncthing cli config folders <folder-id> min-disk-free value set 1
```

```bash
syncthing cli config folders <folder-id> min-disk-free unit set %
```

Share it with the device. This is needed on both sides, each naming the other. VERIFIED:

```bash
syncthing cli config folders <folder-id> devices add --device-id <device-id>
```

A folder the peer shared and this side has not added yet waits here, and the log says `Unexpected folder ID in ClusterConfig`. VERIFIED:

```bash
syncthing cli show pending folders
```

---

### Choose the folder type

The folder types page and the configuration page define three types:

| Type | Use it for | What the page says |
|---|---|---|
| `sendreceive` | two-way sync, the default | "Sending local and accepting remote changes" |
| `sendonly` | the source of a one-way copy | "it will not be modified by Syncthing on this device" |
| `receiveonly` | the target of a one-way pull, a mirror or an archive | "Local changes are however not distributed to other devices" |

For a one-way pull set `sendonly` on the source and `receiveonly` on the target. VERIFIED:

```bash
syncthing cli config folders <folder-id> type set receiveonly
```

---

### Keep files that the sender deletes

ignoreDelete makes this side ignore delete instructions from the others. The configuration page warns: "Enabling this is highly discouraged - use at your own risk." Its own page explains that both sides then consider each other out of date, and that "Bob may continue to see Alice as up to date until the next time Syncthing is restarted on his device."

Use it for exactly one case: a `receiveonly` archive that must keep what the sender rotates away. Measured: with ignoreDelete on the `receiveonly` side, a file deleted on the `sendonly` side stayed on the receiving side. VERIFIED:

```bash
syncthing cli config folders <folder-id> ignore-delete set true
```

```bash
syncthing cli config folders <folder-id> ignore-delete get
```

Deleted items are not kept in the database forever either. The 2.0.0 release notes say they are "forgotten after six months".

---

### Move a folder to a new path

The web page offers no way to change the path of an existing folder: in 2.1.7 the Folder Path field carries `ng-readonly="editingFolderExisting()"`, read in `gui/default/syncthing/folder/editFolderModalView.html`. The FAQ says "Syncthing doesn't have a direct way to do this" and describes the manual route: stop Syncthing, move the folder "including the `.stfolder` marker", edit the path in `config.xml`, start again. It also says to do it "when the folder is already in sync between your devices".

The command line does the same without stopping Syncthing: pause the folder, move the directory with its `.stfolder` marker, set the new path, resume. Measured on a `receiveonly` folder: after resuming it was `idle` with all files and nothing needed. VERIFIED:

```bash
syncthing cli config folders <folder-id> paused set true
```

```bash
mv ~/Documents/sync/<old-name> ~/Documents/sync/<folder-label>
```

```powershell
Move-Item "$env:USERPROFILE\Documents\sync\<old-name>" "$env:USERPROFILE\Documents\sync\<folder-label>"
```

```bash
syncthing cli config folders <folder-id> path set '~/Documents/sync/<folder-label>'
```

```bash
syncthing cli config folders <folder-id> paused set false
```

Then read the folder state and the need counts, as [troubleshooting.md](troubleshooting.md) shows. When the contents were moved but the old directory stayed behind, delete it only when it holds nothing but `.stfolder`, checked the same way as `~/Sync` above. Never move a folder that is still syncing, and never move it without its marker, because the marker is how Syncthing tells a missing folder from an empty one.

---

### Remove a device or a folder

Both remove only the configuration entry and leave files on disk. Ask the owner first.

```bash
syncthing cli config folders <folder-id> delete
```

```bash
syncthing cli config devices <device-id> delete
```
