# Syncthing in Docker

Read this before running Syncthing in a container, or before running `syncthing cli` against one. The rules live in [SKILL.md](../SKILL.md), and Compose and image design in general belong to the `docker-patterns` skill. Commands marked VERIFIED ran against the `lscr.io/linuxserver/syncthing` and `syncthing/syncthing` images of Syncthing 2 in throwaway containers on an isolated network. Every other command here is UNVERIFIED.

Sources: the linuxserver README at https://github.com/linuxserver/docker-syncthing, its `root/etc/s6-overlay/s6-rc.d/svc-syncthing/run`, and https://github.com/syncthing/syncthing/blob/main/README-Docker.md.

---

### The Compose service

The linuxserver README gives this service. Here it carries placeholders for the host paths, and the GUI port is bound to `127.0.0.1` so the GUI stays on the Docker host until a GUI user and password exist:

```yaml
services:
  syncthing:
    image: lscr.io/linuxserver/syncthing:<version-tag>@sha256:<digest>
    container_name: syncthing
    hostname: <syncthing-host-name>
    environment:
      - PUID=<uid>
      - PGID=<gid>
      - TZ=<time-zone>
    volumes:
      - <syncthing-config-dir>:/config
      - <sync-data-dir>:/data1
    ports:
      - 127.0.0.1:8384:8384
      - 22000:22000/tcp
      - 22000:22000/udp
      - 21027:21027/udp
    restart: unless-stopped
```

| Port | The README calls it |
|---|---|
| 8384 | "Application WebUI" |
| 22000/tcp | "Listening port (TCP)" |
| 22000/udp | "Listening port (UDP)" |
| 21027/udp | "Protocol discovery" |

`PUID` and `PGID` are the numeric user and group that own the data on the host. The README says: "Ensure any volume directories on the host are owned by the same user you specify and any permissions issues will vanish like magic." Read them on the host:

```bash
id -u
```

```bash
id -g
```

Pin `<version-tag>` to a release tag of the image rather than `latest`, so an upgrade is a deliberate change, and `<digest>` with the digest that tag resolves to, read with `docker buildx imagetools inspect lscr.io/linuxserver/syncthing:<version-tag>`, so a re-pushed tag cannot change what runs.

---

### Paths inside the container

Syncthing in the container sees container paths. The folder layout rule from [folders-and-devices.md](folders-and-devices.md) applies to the mounted data volume: set the default folder path to the data mount, and give every folder its own directory under it, `/data1/<folder-label>`. The host side of that mount follows the host's own layout.

---

### syncthing cli inside the container

The linuxserver image starts Syncthing as the user `abc` with `--home=/config --no-browser --no-restart --gui-address="0.0.0.0:8384"`. Run the command line tool as the same user with the same home. VERIFIED:

```bash
docker exec -u abc syncthing syncthing cli --home=/config show system
```

Every command from the other topic files works the same way behind that prefix, for example the default folder path:

```bash
docker exec -u abc syncthing syncthing cli --home=/config config defaults folder path set /data1
```

The official image `syncthing/syncthing` instead runs as UID 1000 and sets `STGUIADDRESS=0.0.0.0:8384` and `STHOMEDIR=/var/syncthing/config`. With `STGUIADDRESS` set, `syncthing cli` refuses with `Both --gui-address and --gui-apikey should be specified`, so drop that variable for the one command. VERIFIED:

```bash
docker exec -u 1000 <container> env -u STGUIADDRESS syncthing cli show system
```

Neither image created a Default Folder in Syncthing 2, VERIFIED with `config folders list`.

---

### Discovery and the GUI

The official README says Docker's default network mode "prevents local IP addresses from being discovered", and recommends host network mode. With the bridge network above, every peer needs this host's LAN address, `tcp://<peer-lan-ip>:22000`, as [connections.md](connections.md) shows.

On the GUI it says that inside the image Syncthing "listens on `0.0.0.0:8384`" and: "If you configure your GUI to be externally reachable, make sure you set up authentication and enable TLS." The linuxserver image does the same through `--gui-address`. Publishing 8384 on all host interfaces makes the GUI reachable from the LAN, so set the GUI user and password first, as [cli-and-rest.md](cli-and-rest.md) shows, and only then change the port binding.
