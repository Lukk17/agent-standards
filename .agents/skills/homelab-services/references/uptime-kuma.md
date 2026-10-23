# Uptime Kuma

Read this before changing monitors, reading `/metrics` with the API key, adding a tag, or editing the database. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab on 2026-10-23 with `louislam/uptime-kuma:2.5.5`. The database edit was also run end to end on 2026-10-23 in a throwaway container of that image with no network. Every other command here is UNVERIFIED.

Sources, read on 2026-10-23 at tag 2.5.5 of https://github.com/louislam/uptime-kuma: `server/server.js` and `server/auth.js` for the API key, `server/prometheus.js` for the tag labels, `server/database.js` for the database path and its WAL journal, `db/knex_init_db.js` for the `monitor` columns, and `docker/debian-base.dockerfile`, which installs `sqlite3` into the image. The wiki page Prometheus API Keys at https://github.com/louislam/uptime-kuma/wiki/Prometheus-API-Keys.

---

### Monitors and their intervals

Every check writes a row into the database, so the interval decides how fast it grows. A monitor that alerts on a network drop does well at 30 seconds with 1 retry 30 seconds later: it goes red after two failed checks in a row. The record of every short drop belongs to a per-second probe such as [telegraf-network-watch.md](telegraf-network-watch.md), not to Uptime Kuma. VERIFIED: six network monitors moved from 2 to 7 seconds to 30 seconds on the homelab.

Point every monitor at an address and port, never at a `.internal` name, so a red monitor names one service. Proxmox answers an unauthenticated request with 401, so it gets a Ping monitor, not an HTTP one. A DNS monitor that asks AdGuard Home for a public name catches the failure where the web page loads and nothing resolves.

Settings, then Monitor History, keeps the history for a number of days. Set it, so the database stops growing without a limit.

---

### The read-only API key

An API key opens one route, `/metrics`, in the Prometheus text format: every monitor with its name, target, status and response time. `server/server.js` has `app.get("/metrics", apiAuth, prometheusAPIMetrics())`, and no other route takes the key. `server/auth.js` reads the key as the password of basic authentication and ignores the user name. The wiki says "The API key cannot be used to access the web interface" and "As soon as you add your first API key, the use of basic authentication for the endpoint will be permanently disabled". So the key cannot change a monitor. VERIFIED: the key reads `/metrics` on the homelab, and every change still needs the logged-in web page or the database edit below.

The owner creates it under Settings, then API Keys, and it is shown once. Give it to curl on standard input as a config line, with an empty user name before the colon, so it never lands on a command line. The env file path is the owner's:

```bash
{ printf 'user = ":'; grep '^UPTIME_KUMA_API_KEY=' <env-file> | cut -d= -f2- | tr -d '\n'; printf '"\n'; } | curl -s -K - http://<vm-ip>:<kuma-port>/metrics
```

Lines starting with `monitor_status` mean the key works. A `401` means it does not. The status of each monitor, 1 for up and 0 for down:

```bash
{ printf 'user = ":'; grep '^UPTIME_KUMA_API_KEY=' <env-file> | cut -d= -f2- | tr -d '\n'; printf '"\n'; } | curl -s -K - http://<vm-ip>:<kuma-port>/metrics | grep '^monitor_status'
```

---

### The labelset log flood

Uptime Kuma reads the tag names once, at start, and uses them as the labels of its metrics. `server/prometheus.js` says "New tags will NOT be added dynamically, a restart is sadly required to add new tags to the metrics." A monitor that carries a tag created after the start then fails to write its metrics on every heartbeat, and each failure writes a stack trace starting with:

```text
[PROMETHEUS] ERROR: Error: Added label "<tag>" is not included in initial labelset
```

VERIFIED: after a tag was added to six monitors, the container log grew 1,607,027 bytes in 60 seconds, about 2.3 GB a day, and had reached 24.7 GB. A restart stopped it at once, 0 bytes in the next 60 seconds.

So after creating a tag, restart, with the owner's yes:

```bash
docker restart uptime-kuma
```

Then check that it is gone. A count of 0 means it is:

```bash
docker logs --since 1m uptime-kuma 2>&1 | grep -c PROMETHEUS
```

A log limit, from [deploy-and-logs.md](deploy-and-logs.md#log-limits-on-every-service), keeps such a flood from filling the disk, but the flood still hides every other line until the restart.

---

### Editing monitors in the database

When the agent has no login to the web page, it changes monitors in the SQLite database, `/app/data/kuma.db` inside the container. Uptime Kuma keeps the database open in WAL mode and holds the monitors in memory, so it is stopped first, the database is backed up, the change is made, and it is started again. The image ships `sqlite3`, so a one-off container of the same image does the work, and nothing is installed on the VM. VERIFIED on 2026-10-23 on the homelab, and in a throwaway container of the same image, with the commands below.

Ask the owner first. Every monitor is silent while it is stopped.

Stop it:

```bash
docker stop uptime-kuma
```

Back up the database next to itself. `.backup` copies it consistently, WAL included:

```bash
docker run --rm --network none -v <kuma-data-dir>:/app/data --entrypoint sqlite3 louislam/uptime-kuma:2.5.5 /app/data/kuma.db ".backup /app/data/kuma.db.bak"
```

Read the monitors first, to pick the exact names or IDs:

```bash
docker run --rm --network none -v <kuma-data-dir>:/app/data --entrypoint sqlite3 louislam/uptime-kuma:2.5.5 -header -column /app/data/kuma.db "SELECT id, name, type, interval, retry_interval, maxretries, active FROM monitor;"
```

Change them, here one monitor to 30 seconds with 1 retry after 30 seconds:

```bash
docker run --rm --network none -v <kuma-data-dir>:/app/data --entrypoint sqlite3 louislam/uptime-kuma:2.5.5 /app/data/kuma.db "UPDATE monitor SET interval = 30, retry_interval = 30, maxretries = 1 WHERE id = <monitor-id>;"
```

Read them back with the `SELECT` above, then start it:

```bash
docker start uptime-kuma
```

Check that it came up healthy:

```bash
docker ps --filter name=uptime-kuma --format '{{.Status}}'
```

To undo, stop it again, put the backup back, and start it. UNVERIFIED, the undo was not run:

```bash
docker run --rm --network none -v <kuma-data-dir>:/app/data --entrypoint cp louislam/uptime-kuma:2.5.5 /app/data/kuma.db.bak /app/data/kuma.db
```

Use the image tag the Compose file runs, so the `sqlite3` matches. `<kuma-data-dir>` is the host side of the `/app/data` mount. The columns named above exist in 2.5.5. Tags live in the tables `tag` and `monitor_tag`, and a tag added there needs the restart above as well.
