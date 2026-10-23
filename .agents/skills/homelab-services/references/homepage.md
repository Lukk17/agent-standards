# Homepage

Read this before configuring the Homepage dashboard or opening it under a new name. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab on 2026-10-23 with `ghcr.io/gethomepage/homepage:v1.13.2`. Every other command here is UNVERIFIED.

Sources, fetched on 2026-10-23: the installation page of the Homepage documentation, `docs/installation/index.md` at https://github.com/gethomepage/homepage.

---

### Where the configuration lives

Homepage is configured by files in `/app/config`, mounted from `<stack-dir>/homepage/config`. It writes a default set at the first start, so start it once before changing them.

| File | Holds |
|---|---|
| `services.yaml` | The tiles, in groups, with their links and status checks |
| `settings.yaml` | Title, theme, layout |
| `widgets.yaml` | The header strip, such as a clock or resources |
| `bookmarks.yaml` | Plain links with no check |

It picks up most changes by itself within seconds. When a change does not show, restart it:

```bash
cd <stack-dir> && docker compose restart homepage
```

---

### Allowed hosts

The documentation says: "As of v1.0 there is one required environment variable to access homepage via a URL other than `localhost`, `HOMEPAGE_ALLOWED_HOSTS`." The value is "a comma-separated (no spaces) list of allowed hosts (sometimes with the port)". A name that is missing gets `Host validation failed` instead of the page. VERIFIED on the homelab.

```yaml
environment:
  - HOMEPAGE_ALLOWED_HOSTS=<name>.internal,<vm-ip>:<homepage-port>
```

It is an environment variable, so the container is recreated, not restarted:

```bash
cd <stack-dir> && docker compose up -d homepage
```

Setting it to `*` turns the check off, which the documentation says "is not recommended".

---

### href and siteMonitor

Each tile has two addresses, and they differ on purpose. `href` is where a click goes, the friendly `.internal` name. `siteMonitor` is what Homepage polls for the status dot, the address and published port, so a dead proxy or a dead AdGuard Home does not turn every dot red at once.

```yaml
- Services:
    - Uptime Kuma:
        href: http://<name>.internal
        siteMonitor: http://<vm-ip>:<kuma-port>
```

A host outside the Compose stack, such as Proxmox, gets its real address in both fields.
