# Nginx Proxy Manager

Read this before adding a proxy host for a `.internal` name, or before forwarding one to a service that runs on host networking or on another machine. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab on 2026-10-23 with `jc21/nginx-proxy-manager:2.15.1`. Every other command here is UNVERIFIED.

Sources, fetched on 2026-10-23: `backend/setup.js` at tag v2.15.1 of https://github.com/NginxProxyManager/nginx-proxy-manager, and its setup page `docs/src/setup/index.md` on the `develop` branch.

---

### How a name reaches a container

AdGuard Home answers every `.internal` name with the VM's address, see [adguard-home.md](adguard-home.md#a-wildcard-rewrite-for-internal-names). The browser then reaches Nginx Proxy Manager on port 80 of the VM, and the proxy picks the proxy host whose domain name matches the Host header. So every web service needs one proxy host and no DNS entry.

Give the proxy and every container it forwards to one shared bridge network in the Compose file, so Docker resolves the container names:

```yaml
networks:
  proxy-tier:
    name: proxy-tier
    driver: bridge
```

---

### First login

At 2.15.1 the first visit to the admin page on port 81 shows a setup page that creates the first user. `backend/setup.js` says "Otherwise, users should be shown the setup wizard in the frontend", and creates a user by itself only when `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` are set, and then logs `Creating a new user: ${initialAdminEmail} with password: ${initialAdminPassword}`, the password in clear text in the container log. So leave those two variables out, and let the owner create the user on the setup page. UNVERIFIED by a run.

Port 81 is reachable from the whole network, so the user is created before anything else.

---

### A proxy host per name

Hosts, then Proxy Hosts, then Add Proxy Host. On the Details tab:

1. Domain Names: the `.internal` name, confirmed with Enter.
2. Scheme: `http`.
3. Forward Hostname / IP: the container name on the shared network.
4. Forward Port: the port inside the container, the right-hand side of its Compose port mapping, not the published port.
5. Websockets Support on, and Block Common Exploits on.
6. SSL: none. A `.internal` name cannot get a public certificate.

VERIFIED: one proxy host per `.internal` name on the homelab. A forward port set to the published port instead of the container port is the usual reason a new proxy host answers 502.

---

### A service on host networking

A container with `network_mode: host`, Plex for one, is not on the shared network, so the proxy cannot reach it by name. Forward to the VM's address and the port the service listens on:

| Domain name | Scheme | Forward hostname | Port |
|---|---|---|---|
| `<name>.internal` | http | `<vm-ip>` | 32400 |

VERIFIED on the homelab for Plex. Another machine, such as the Proxmox host on 8006 with scheme `https`, is forwarded the same way, to its own address. The proxy does not check the upstream certificate, so a self-signed one works.

---

### Check a proxy host

Before any device uses AdGuard Home for DNS, send the Host header yourself:

```bash
curl -sI -H "Host: <name>.internal" http://<vm-ip> | head -1
```

```powershell
curl.exe -sI -H "Host: <name>.internal" http://<vm-ip>
```

A 200 or a 3xx means the proxy found the service. A 502 means the service is down or the forward port is wrong. A 404 from the proxy means no proxy host matches the name.

The proxy hosts and the users live in `<stack-dir>/nginx/data`, with `database.sqlite`. Back up that folder, and a rebuilt VM gets every proxy host back.
