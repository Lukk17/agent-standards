# Syncthing Checklist

Run it before calling work on Syncthing done. The rules behind the items are in [SKILL.md](../SKILL.md).

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
