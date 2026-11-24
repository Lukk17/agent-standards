---
name: syncthing
description: 'Syncthing 2 from a terminal: the CLI and REST API, pairing, folder types, relays, Docker peers. Use when the user says "pair this device" or "the folder shows Stopped". Not for Compose design, use `docker-patterns`.'
metadata:
  version: "1.1.0"
---

# Syncthing Administration

How to set up and repair Syncthing from a terminal so that nothing waits for a click in the web page. Every change goes through `syncthing cli` or the REST API, every synced folder lives under one base folder, and no device may add folders or devices on its own. Syncthing changed a lot between 1.x and 2.x, so check `syncthing --version` before you apply a recipe. Written for Syncthing 2. Setup facts belong in the owner's notes, never here, and examples use `<placeholders>`.

---

### When not to activate

- Designing a Compose stack, an image or a container network in general, use `docker-patterns`
- Service, firewall, package or disk work on one machine beyond the Syncthing steps here, use `windows`, `macos`, `arch-linux` or `cachyos`
- Growing the virtual disk of a Proxmox guest that holds the Syncthing database, use `proxmox`

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
10. Ask before removing a device or a folder, before `folder-override`, and before deleting any directory. Anything that needs root or administrator rights goes to the owner with what it changes.

---

### Reference files

| You are about to | Open |
|---|---|
| Find the state directory, read the firewall ports, run the first check after a start | [install-and-start.md](references/install-and-start.md) |
| Install, start at login and open the firewall on Linux | [install-linux.md](references/install-linux.md) |
| Install, start at logon and open the firewall on Windows | [install-windows.md](references/install-windows.md) |
| Install, start at login and answer the firewall prompt on macOS | [install-macos.md](references/install-macos.md) |
| Read the API key or the GUI address, drive `syncthing cli` or the REST API, set a GUI password | [cli-and-rest.md](references/cli-and-rest.md) |
| Set the folder layout, pair a device, add or share a folder, set its type, ignoreDelete, introducer, auto accept, move a folder | [folders-and-devices.md](references/folders-and-devices.md) |
| Check whether a connection is direct or relayed, give a peer a fixed address, reach a peer in Docker | [connections.md](references/connections.md) |
| Explain a folder that shows Stopped, a disk space error, a peer with 0 files, or a warning in the log | [troubleshooting.md](references/troubleshooting.md) |
| Run Syncthing in a container with the linuxserver image | [docker.md](references/docker.md) |
| Name a device, a folder or an address, or judge a VERIFIED mark | [conventions.md](references/conventions.md) |
| Before calling the work done | [checklist.md](references/checklist.md) |
