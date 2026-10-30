# Plex

Read this before running Plex in the stack, claiming it, mounting the media, or adding a library. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab with the `plexinc/pms-docker` image. Every other command here is UNVERIFIED.

Sources: the image README at https://github.com/plexinc/pms-docker. The Plex support articles "Requirements for Remote Playback of Personal Media" and "Network" at https://support.plex.tv are quoted from the owner's notes, and were not fetched again.

---

### The container

Use a version tag in place of `<version-tag>`. The README says the `beta` and `public` tags "do not have any Plex Media Server binary installed" and fetch the newest version at every start.

```yaml
plex:
  image: plexinc/pms-docker:<version-tag>
  network_mode: host
  cpus: 1.5
  environment:
    - PLEX_UID=1000
    - PLEX_GID=1000
    - PLEX_CLAIM=${PLEX_CLAIM:-}
  volumes:
    - <stack-dir>/plex/config:/config
    - <stack-dir>/plex/transcode:/transcode
    - type: bind
      source: /mnt/data/media
      target: /data
      read_only: true
      bind:
        create_host_path: false
```

Create the two Plex folders as the login user before the first start:

```bash
mkdir -p <stack-dir>/plex/config <stack-dir>/plex/transcode
```

---

### Host networking

Plex treats a player that is not on the same subnet as remote, and remote video playback needs a paid pass. On a bridge network Plex sees every home device as coming from another network. The support article lists "Running apps or servers inside a container/virtualization and not using "host networking"" among the causes. With `network_mode: host` Plex listens on `<vm-ip>:32400`, on the home subnet, with no `ports:` list. VERIFIED: host networking with a free account on the homelab.

Nginx Proxy Manager cannot reach it by container name, so its proxy host forwards to `<vm-ip>` and port 32400, see [nginx-proxy-manager.md](nginx-proxy-manager.md#a-service-on-host-networking).

---

### Claim the server

The claim token from https://www.plex.tv/claim links the server to the owner's account, and it is valid for a few minutes only. VERIFIED: about 4 minutes, so the owner gets it and starts Plex back to back. The README: "If server is already logged in, this parameter is ignored."

The owner pastes it, hidden, on the VM:

```bash
read -r -s -p 'Plex claim token: ' PLEX_CLAIM; echo
```

```bash
printf 'PLEX_CLAIM=%s\n' "$PLEX_CLAIM" >> <stack-dir>/.env
```

```bash
unset PLEX_CLAIM
```

Check by length, `PLEX_CLAIM` must show a number above 0:

```bash
awk -F= '{print $1, length($2)}' <stack-dir>/.env
```

```bash
cd <stack-dir> && docker compose up -d plex
```

The owner opens `http://<vm-ip>:32400/web` and signs in. Then the used token goes:

```bash
sed -i '/^PLEX_CLAIM=/d' <stack-dir>/.env
```

A token that ran out before the start leaves the server unclaimed. Stop it, remove the line, add a fresh token, and start it again.

---

### Media read only, one folder per library

Mount the media read only, so Plex can never change or delete a file. With `create_host_path: false` Plex refuses to start when the data disk is not mounted, or when somebody renamed or deleted the `media` folder over the network drive. VERIFIED: the read-only mount. The refusal follows from `create_host_path: false` and was not measured.

Plex takes one kind of media per library, a Movies library and a TV Shows library, so films and series go in separate folders, for example `media/films` and `media/series`. VERIFIED: the two libraries on the homelab. Paths in Plex are paths inside the container, `/data/films` and `/data/series`. A library pointed at the host path `/mnt/data/media` stays empty.

---

### Keep conversion off the VM

`cpus: 1.5` is a hard ceiling the kernel enforces, so a video conversion Plex insists on runs slower than real time instead of starving AdGuard Home of CPU. Store files the players can play as they are, which Plex calls Direct Play, and turn off the settings that start a conversion on their own, such as video preview thumbnails. A film that buffers under the cap is a file in the wrong format.
