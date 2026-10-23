---
name: syncthing
description: 'Running Syncthing 2.x from an agent on Linux, Windows and macOS without the web page: start it as the user (systemd user unit, logon task, brew services), syncthing cli and the REST API with the API key, the folder layout under ~/Documents/sync, pairing, adding a folder by its folder ID, the folder types sendreceive, sendonly and receiveonly, ignoreDelete, introducer and autoAcceptFolders, moving a folder, a direct connection instead of a relay, a peer in Docker, the database disk space error, a peer that shows 0 files, and the linuxserver/syncthing image. Use when you say "pair this device", "share this folder one way", "keep the files when the sender deletes them", "the folder shows Stopped", "insufficient space on disk for database", "is it going through a relay", "move this synced folder", or "Remote is an introducer to us". Not for compose and image design in general, use `docker-patterns`, and not for services, firewalls and packages of one machine, use `windows`, `macos` or `arch-linux`.'
---

# Syncthing Administration

How to set up and repair Syncthing from a terminal so that nothing waits for a click in the web page. Every change goes through `syncthing cli` or the REST API, every synced folder lives under one base folder, and no device may add folders or devices on its own. Syncthing changed a lot between 1.x and 2.x, so check `syncthing --version` before you apply a recipe.

Baseline: Syncthing 2.1.7, released on 2026-10-21, with the documentation and the source fetched on 2026-10-23. Commands marked VERIFIED were executed on 2026-10-23 against 2.1.7 in throwaway containers built from `syncthing/syncthing:2.1.7` and `lscr.io/linuxserver/syncthing:v2.1.7-ls233` on an isolated Docker network. Every other command, every Windows and every macOS command included, is UNVERIFIED.

| You are about to | Open |
|---|---|
| Install Syncthing, start it at login, find its configuration, open the firewall | [install-and-start.md](references/install-and-start.md) |
| Read the API key or the GUI address, drive `syncthing cli` or the REST API, set a GUI password | [cli-and-rest.md](references/cli-and-rest.md) |
| Set the folder layout, pair a device, add or share a folder, set its type, ignoreDelete, introducer, auto accept, move a folder | [folders-and-devices.md](references/folders-and-devices.md) |
| Check whether a connection is direct or relayed, give a peer a fixed address, reach a peer in Docker | [connections.md](references/connections.md) |
| Explain a folder that shows Stopped, a disk space error, a peer with 0 files, or a warning in the log | [troubleshooting.md](references/troubleshooting.md) |
| Run Syncthing in a container with the linuxserver image | [docker.md](references/docker.md) |

---

### Facts about one setup

Device IDs, folder IDs, host names and LAN addresses of a real setup belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md`, never in this skill and never in a shared repository. Discover them with the read commands in the topic files. Every example here uses placeholders in angle brackets: `<device-id>`, `<folder-id>`, `<folder-label>`, `<peer-lan-ip>`.

---

### When to activate

- Installing Syncthing, or making it start at login or at boot
- Pairing two devices, or sharing a folder between them
- Choosing a folder type, or keeping files on one side after the other side deletes them
- A folder that shows Stopped, Out of Sync, or 0 files on one side
- A slow transfer that may run through a relay, or a peer inside a Docker container
- Moving a synced folder to a new path, or cleaning up folders that appeared by themselves

---

### When not to activate

- Designing a Compose stack, an image or a container network in general, use `docker-patterns`
- Service, firewall, package or disk work on one machine beyond the Syncthing steps here, use `windows`, `macos`, `arch-linux` or `cachyos`
- Growing the virtual disk of a Proxmox guest that holds the Syncthing database, use `proxmox`
- Backups with history and point in time restore, which Syncthing does not provide, use a backup tool

---

### Hard rules

1. Syncthing runs as the owner's own user, never as root and never as SYSTEM. The upstream page on autostart says a GUI that is not secured lets any process "read/write any file on your filesystem" through Syncthing.
2. Change the configuration through `syncthing cli` or the REST API. Edit `config.xml` only while Syncthing is stopped, and never use the web page for a step a command can do.
3. The folder ID links a folder between devices. The label is only a local name and may differ on each side.
4. Synced folders live under `~/Documents/sync/<folder-label>`, on Windows `%USERPROFILE%\Documents\sync\<folder-label>`, never directly in the home folder, and the default folder path points at that base.
5. Introducer and autoAcceptFolders stay off on both sides of every pair of devices.
6. Never lower `minHomeDiskFree` or a folder `minDiskFree` to get past a disk space error. Free or grow the disk.
7. Use ignoreDelete only on the receiving side of an archive, together with receiveonly, and only when the owner asked for an archive that outlives the sender.
8. A GUI that listens on anything but `127.0.0.1` gets a GUI user and password before it is exposed.
9. Never print the API key or a GUI password into the session, a log or a file in a repository. Read the key into a shell variable and pass it to curl on standard input.
10. Ask before removing a device or a folder, before `folder-override`, and before deleting any directory. A firewall rule, a package install and `loginctl enable-linger` need root or administrator rights, so they go to the owner with what they change.

---

### Related skills

- `docker-patterns` owns Compose, images and container networks around a Syncthing container
- `windows`, `macos`, `arch-linux` and `cachyos` own services, firewalls and packages on each kind of machine
- `proxmox` owns growing the virtual disk under a guest that runs Syncthing
- `security-review` owns judging an exposed GUI, a published port or a token
- `bash` and `powershell` own scripts that wrap these commands

---

### Checklist

- [ ] `syncthing --version` checked, and `syncthing paths` read before touching any file
- [ ] Syncthing runs as the owner's user, started by the user unit, a logon task or `brew services`
- [ ] The default folder path set to `~/Documents/sync` or `%USERPROFILE%\Documents\sync`
- [ ] A Default Folder left over from 1.x removed, and `~/Sync` deleted only when it held nothing but `.stfolder`
- [ ] Each folder added by its folder ID, shared with the device on both sides, its type set on purpose
- [ ] `min-disk-free` set on every folder added through `syncthing cli config folders add`
- [ ] Introducer and auto accept read back as false on both sides
- [ ] The connection type read from `show connections`, and a peer in Docker given `tcp://<peer-lan-ip>:22000`
- [ ] `syncthing cli errors show` and the folder status read back after the change
- [ ] A GUI user and password set wherever the GUI listens beyond localhost
- [ ] No API key, password or real device ID written into a shared file
