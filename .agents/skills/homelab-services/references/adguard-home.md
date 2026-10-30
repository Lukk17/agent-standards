# AdGuard Home

Contents:

- [Ports and first run](#ports-and-first-run)
- [A wildcard rewrite for .internal names](#a-wildcard-rewrite-for-internal-names)
- [Upstreams](#upstreams)
- [Query log and statistics retention](#query-log-and-statistics-retention)
- [Ignored domains](#ignored-domains)
- [Editing AdGuardHome.yaml](#editing-adguardhomeyaml)

Read this before adding a DNS rewrite, changing upstreams, changing how long the query log or the statistics are kept, ignoring a domain, or editing `AdGuardHome.yaml`. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab with AdGuard Home 0.107. The file edit was also run end to end in a throwaway container of that image with no network. Every other command here is UNVERIFIED.

Sources in https://github.com/AdguardTeam/AdGuardHome: `internal/home/config.go` for the keys and defaults, `internal/home/home.go` and `internal/home/config.go` for when the file is written, `internal/querylog/querylogfile.go` for the rotation, `internal/filtering/rewrites.go` for the rewrite keys, and `docker/build.Dockerfile` for the image, which is Alpine with BusyBox.

---

### Ports and first run

The first run wizard listens on container port 3000. It asks for the port of the web page afterwards. Choose a port other than 80, for example 7777, so port 80 stays free for Nginx Proxy Manager, and publish both container ports in the Compose file. DNS stays on 53.

```yaml
ports:
  - "53:53/tcp"
  - "53:53/udp"
  - "7776:3000/tcp"
  - "7777:7777/tcp"
```

The web page and the API both need the login made in the wizard. An agent without that login reads the query log file and edits `AdGuardHome.yaml` instead, as below.

---

### A wildcard rewrite for .internal names

One rewrite sends every `.internal` name to the VM, where Nginx Proxy Manager routes on the Host header. A new service then needs a proxy host only, never another DNS entry. VERIFIED: one rewrite of `*.internal` to `<vm-ip>` serves every name on the homelab.

In the web page it is Filters, then DNS rewrites, then Add DNS rewrite. In the file it lives under `filtering`:

```yaml
filtering:
  rewrites_enabled: true
  rewrites:
    - domain: '*.internal'
      answer: <vm-ip>
      enabled: true
```

Check it from any machine that uses AdGuard for DNS:

```bash
nslookup anything.internal <vm-ip>
```

A service that is not web traffic, Samba for one, answers on the VM's address directly, so any `.internal` name reaches it without a proxy host.

---

### Upstreams

Settings, then DNS settings. Give several encrypted upstreams from different providers, one per line, and choose Parallel requests, so a dead provider costs no wait. Give one or two plain fallback servers for the moment every upstream has failed. In the file these are `dns.upstream_dns`, `dns.upstream_mode`, `dns.fallback_dns` and `dns.upstream_timeout`. VERIFIED on the homelab: three encrypted upstreams in parallel mode with a 3 second timeout, and ad domains still answered `0.0.0.0`, since the blocklists act before any upstream is asked.

The router hands out the VM as the only DNS server. A public resolver in the second slot gets roughly half the `.internal` lookups and answers them with NXDOMAIN. The router side belongs to the `asus-router` skill.

---

### Query log and statistics retention

The defaults in 0.107 are 90 days for the query log and 1 day for the statistics, `querylog.interval` and `statistics.interval`. That release line writes a whole number of days as `30d` and also reads hours, `720h`.

The query log rotates by age, not by size. When AdGuard Home starts, and then once an hour (`periodicRotate`), it reads the time of the oldest entry in `querylog.json`. When that entry is older than the interval, it renames `querylog.json` to `querylog.json.1` and replaces the older `querylog.json.1`. The two files together hold between one and two intervals. VERIFIED: at 90 days the two files held 4.0 GB.

Lowering the interval deletes old queries at the next start or hourly check, and nothing brings them back. VERIFIED: going from 90 days to 30 days and starting the container replaced `querylog.json.1`, 2.9G in `du -h`, at once, every query older than the oldest entry of `querylog.json` was gone, and the free disk went from 110G to 113G.

So before lowering it, tell the owner, and offer a copy of both files. The log is in the `data` folder of the work mount, `/opt/adguardhome/work/data` inside the container. A copy out of the container, into the current folder:

```bash
docker cp adguard-home:/opt/adguardhome/work/data/querylog.json.1 ./querylog.json.1
```

```bash
docker cp adguard-home:/opt/adguardhome/work/data/querylog.json ./querylog.json
```

The web page sets both under Settings, then General settings, on the Logs configuration card and the Statistics configuration card. It warns "If you decrease the interval value, some data will be lost".

Clear query logs on the same card deletes both files and the entries held in memory at once.

---

### Ignored domains

A probe that asks the same name every second, such as the network watch in [telegraf-network-watch.md](telegraf-network-watch.md), drowns every other query in the log and the statistics. The Logs card and the Statistics card each have their own Ignored domains field, so the domain goes into both. VERIFIED: one entry per card hides the probe's name, whichever client asks.

In the file the lists are `querylog.ignored` and `statistics.ignored`. In 0.107 each block also carries `ignored_enabled`, which the source describes as "whether hosts from the ignored list should be ignored", default false, so a list written by hand needs `ignored_enabled: true` beside it. UNVERIFIED.

---

### Editing AdGuardHome.yaml

When the agent has no AdGuard login, it edits the file. The file sits in the conf mount, owned by root with mode 600, so the agent works through `docker exec` rather than `sudo`. AdGuard Home reads the file at start, writes it back at start, and writes the whole file again every time a setting is saved in the web page. A change made by hand while it runs therefore survives only until the next save in the web page, so nobody may save a setting between the edit and the restart. VERIFIED on the homelab, and in a throwaway container of the same image, with the commands below.

Ask the owner first. The restart leaves the whole network without DNS for a few seconds.

Back up the file, inside the same folder:

```bash
docker exec adguard-home cp -p /opt/adguardhome/conf/AdGuardHome.yaml /opt/adguardhome/conf/AdGuardHome.yaml.bak
```

Read the block you are about to change, here the query log:

```bash
docker exec adguard-home sed -n '/^querylog:/,/^[^ ]/p' /opt/adguardhome/conf/AdGuardHome.yaml
```

Change one key inside that block only, here the query log interval to 30 days:

```bash
docker exec adguard-home sed -i '/^querylog:/,/^[^ ]/ s/^  interval: .*/  interval: 30d/' /opt/adguardhome/conf/AdGuardHome.yaml
```

Read it back. It must show the new value:

```bash
docker exec adguard-home sed -n '/^querylog:/,/^[^ ]/p' /opt/adguardhome/conf/AdGuardHome.yaml
```

Restart, so AdGuard Home reads the file:

```bash
docker restart adguard-home
```

Read the value again after the start, because AdGuard Home has written the file back by then:

```bash
docker exec adguard-home grep -n 'interval:' /opt/adguardhome/conf/AdGuardHome.yaml
```

And check that it answers DNS:

```bash
nslookup example.com <vm-ip>
```

To undo, put the backup back and restart:

```bash
docker exec adguard-home cp -p /opt/adguardhome/conf/AdGuardHome.yaml.bak /opt/adguardhome/conf/AdGuardHome.yaml
```

```bash
docker restart adguard-home
```

When the container will not start after an edit, `docker exec` cannot reach it. Copy the backup in with `docker cp`, which works on a stopped container, then start it:

```bash
docker cp adguard-home:/opt/adguardhome/conf/AdGuardHome.yaml.bak ./AdGuardHome.yaml.bak
```

```bash
docker cp ./AdGuardHome.yaml.bak adguard-home:/opt/adguardhome/conf/AdGuardHome.yaml
```

```bash
docker start adguard-home
```

UNVERIFIED as a whole. In the throwaway container, `docker cp` into a container that was not running worked, which is how its first config got in, but the recovery itself was not run, and not against a bind mount.
