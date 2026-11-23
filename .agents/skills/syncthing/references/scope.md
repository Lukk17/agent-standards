# Scope

Companion reference for the [syncthing](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Installing Syncthing, or making it start at login or at boot
- Pairing two devices, or sharing a folder between them
- Choosing a folder type, or keeping files on one side after the other side deletes them
- A folder that shows Stopped, Out of Sync, or 0 files on one side
- A slow transfer that may run through a relay, or a peer inside a Docker container
- Moving a synced folder to a new path, or cleaning up folders that appeared by themselves
- Also covers starting it as the user (systemd user unit, logon task, brew services), syncthing cli and the REST API with the API key, the folder layout under ~/Documents/sync, pairing, adding a folder by its folder ID, the folder types sendreceive, sendonly and receiveonly, ignoreDelete, introducer and autoAcceptFolders, moving a folder, a direct connection instead of a relay, a peer in Docker, the database disk space error, a peer that shows 0 files, and the linuxserver/syncthing image
- The user says "pair this device", "share this folder one way", "the folder shows Stopped", "is it going through a relay", "keep the files when the sender deletes them", "insufficient space on disk for database", "move this synced folder" or "Remote is an introducer to us"

---

### When not to activate

- Designing a Compose stack, an image or a container network in general, use `docker-patterns`
- Service, firewall, package or disk work on one machine beyond the Syncthing steps here, use `windows`, `macos`, `arch-linux` or `cachyos`
- Growing the virtual disk of a Proxmox guest that holds the Syncthing database, use `proxmox`
- Backups with history and point in time restore, which Syncthing does not provide, use a backup tool

---

### Related skills

- `docker-patterns` owns Compose, images and container networks around a Syncthing container
- `windows`, `macos`, `arch-linux` and `cachyos` own services, firewalls and packages on each kind of machine
- `proxmox` owns growing the virtual disk under a guest that runs Syncthing
- The `security-auditor` agent owns judging an exposed GUI, a published port or a token
- `bash` and `powershell` own scripts that wrap these commands
