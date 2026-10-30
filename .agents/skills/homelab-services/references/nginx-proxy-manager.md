# Nginx Proxy Manager

Contents:

- [How a name reaches a container](#how-a-name-reaches-a-container)
- [First login](#first-login)
- [A proxy host per name](#a-proxy-host-per-name)
- [Forward Hostname takes no port](#forward-hostname-takes-no-port)
- [A service on host networking](#a-service-on-host-networking)
- [The Proxmox web UI behind the proxy](#the-proxmox-web-ui-behind-the-proxy)
- [Check a proxy host](#check-a-proxy-host)

Read this before adding a proxy host for a `.internal` name, before forwarding one to a service that runs on host networking or on another machine, before putting the Proxmox web UI behind the proxy, or when a proxy host answers 500. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab with Nginx Proxy Manager 2. Every other command here is UNVERIFIED.

Sources: `backend/setup.js` of https://github.com/NginxProxyManager/nginx-proxy-manager, and its setup page `docs/src/setup/index.md` on the `develop` branch.

Sources: `backend/templates/proxy_host.conf` and `docker/rootfs/etc/nginx/conf.d/include/proxy.conf`, the nginx proxy module page https://nginx.org/en/docs/http/ngx_http_proxy_module.html, the Proxmox wiki page "Web Interface Via Nginx Proxy" at https://pve.proxmox.com/wiki/Web_Interface_Via_Nginx_Proxy, `src/Utils.js` of https://git.proxmox.com/?p=proxmox-widget-toolkit.git on its default branch, and https://www.ietf.org/archive/id/draft-ietf-httpbis-rfc6265bis-22.txt.

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

In Nginx Proxy Manager 2 the first visit to the admin page on port 81 shows a setup page that creates the first user. `backend/setup.js` says "Otherwise, users should be shown the setup wizard in the frontend", and creates a user by itself only when `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` are set, and then logs `Creating a new user: ${initialAdminEmail} with password: ${initialAdminPassword}`, the password in clear text in the container log. So leave those two variables out, and let the owner create the user on the setup page. UNVERIFIED by a run.

Port 81 is reachable from the whole network, so the user is created before anything else.

---

### A proxy host per name

Hosts, then Proxy Hosts, then Add Proxy Host. On the Details tab:

1. Domain Names: the `.internal` name, confirmed with Enter.
2. Scheme: `http`.
3. Forward Hostname / IP: the container name on the shared network, with no port after it. The port goes in Forward Port only.
4. Forward Port: the port inside the container, the right-hand side of its Compose port mapping, not the published port.
5. Websockets Support on, and Block Common Exploits on.
6. SSL: none. A `.internal` name cannot get a public certificate, and `https` comes from the local CA include in [local-ca.md](local-ca.md), which needs this tab on None.

VERIFIED: one proxy host per `.internal` name on the homelab. A forward port set to the published port instead of the container port is the usual reason a new proxy host answers 502.

---

### Forward Hostname takes no port

VERIFIED on Nginx Proxy Manager 2: Forward Hostname / IP takes the name or the address only, never `host:port`. The proxy host template `backend/templates/proxy_host.conf` writes the field into `set $server "{{ forward_host }}";` and Forward Port into `set $port {{ forward_port }};`, and `conf.d/include/proxy.conf` builds `proxy_pass $forward_scheme://$server:$port$request_uri;`. A port typed into the hostname field therefore appears twice. nginx logs `invalid port in upstream "<host>:<port>:<port>/"`, and every request answers HTTP 500, while the proxy host list still shows the host as Online. The same template sends the errors of a proxy host to `/data/logs/proxy-host-<id>_error.log` inside the container.

So a proxy host that answers 500 and shows Online gets its Forward Hostname / IP read first. Remove the `:<port>` there and keep the port in Forward Port.

---

### A service on host networking

A container with `network_mode: host`, Plex for one, is not on the shared network, so the proxy cannot reach it by name. Forward to the VM's address and the port the service listens on:

| Domain name | Scheme | Forward hostname | Port |
|---|---|---|---|
| `<name>.internal` | http | `<vm-ip>` | 32400 |

VERIFIED on the homelab for Plex. Another machine, such as the Proxmox host on 8006 with scheme `https`, is forwarded the same way, to its own address. The proxy does not check the upstream certificate, so a self-signed one works.

---

### The Proxmox web UI behind the proxy

On the Details tab:

| Domain name | Scheme | Forward hostname | Port |
|---|---|---|---|
| `<name>.internal` | https | `<proxmox-host>` | 8006 |

Websockets Support on, because the console needs the websocket upgrade headers that the wiki example below passes, and Block Common Exploits on.

On the Advanced tab, Custom Nginx Configuration:

```nginx
proxy_buffering off;
client_max_body_size 0;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
send_timeout 3600s;
```

These lines come from the example in the Proxmox wiki page "Web Interface Via Nginx Proxy", which it says "works for the web interface and also the noVNC console". `client_max_body_size 0` lets an ISO or a template upload through, and the long timeouts keep a console open. The wiki also sets `proxy_connect_timeout 3600s`, which is left out, because the nginx proxy module page says of it: "It should be noted that this timeout cannot usually exceed 75 seconds."

Put no `proxy_set_header` line and no `location` block in Advanced. The template places the Advanced text at server level, ahead of its own `location /`, and that location sets its own headers from `proxy.conf`. nginx says `proxy_set_header` directives "are inherited from the previous configuration level if and only if there are no proxy_set_header directives defined on the current level", so a header set in Advanced never reaches Proxmox, and a `location /` there repeats the one the template writes.

UNVERIFIED in a browser: the login over plain `http` most likely loops back to the login form. Proxmox sets its login ticket cookie with the Secure flag. `src/Utils.js` of proxmox-widget-toolkit, which ships as `proxmoxlib.js`, calls `Ext.util.Cookies.set(Proxmox.Setup.auth_cookie_name, data.ticket, null, '/', null, true, 'lax')`, and the `true` is the secure argument. The cookie draft draft-ietf-httpbis-rfc6265bis-22, step 13 of section 5.7 "Storage Model", says: "If the request-uri does not denote a "secure" connection (as defined by the user agent), and the cookie's secure-only-flag is true, then abort these steps and ignore the cookie entirely." So do one of these two:

1. Serve the name over `https` with the local certificate authority in [local-ca.md](local-ca.md), with the SSL tab left on None, so the browser opens `https://<name>.internal`. VERIFIED: the Proxmox name answered 200 over `https` that way. The login itself has not been tried in a browser.
2. Open Proxmox at `https://<proxmox-host>:8006` directly and keep the proxy host out of the login path.

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
