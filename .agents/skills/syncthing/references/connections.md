# Connections

Read this before deciding why a transfer is slow, giving a peer a fixed address, or connecting to a peer that runs in Docker. The rules live in [SKILL.md](../SKILL.md). Commands marked VERIFIED ran on Syncthing 2.1.7 between two throwaway containers on 2026-10-23. Every other command here, every PowerShell command included, is UNVERIFIED.

Sources, fetched on 2026-10-23: https://docs.syncthing.net/rest/system-connections-get.html, https://docs.syncthing.net/users/relaying.html, https://docs.syncthing.net/users/config.html, https://docs.syncthing.net/users/firewall.html, and https://github.com/syncthing/syncthing/blob/v2.1.7/README-Docker.md.

---

### Direct or relayed

The connections endpoint lists one entry per configured device. Its page says: "The connection types are `tcp-client`, `tcp-server`, `relay-client`, `relay-server`, `quic-client` and `quic-server`." A type that starts with `relay` means the traffic goes through a public relay. The relaying page says the downside "is that the transfer rate is much lower than a direct connection would allow".

The whole answer, VERIFIED:

```bash
syncthing cli show connections
```

Only the lines that decide it:

```bash
syncthing cli show connections | grep -E '"(connected|type|address)"'
```

```powershell
(syncthing cli show connections | ConvertFrom-Json).connections.PSObject.Properties | ForEach-Object { '{0} connected={1} type={2} address={3}' -f $_.Name, $_.Value.connected, $_.Value.type, $_.Value.address }
```

Measured on a LAN between two containers, the entry read `connected` true, `type` `tcp-client`, and the peer's address with port 22000. The relaying page also says that while relayed, "Syncthing will periodically retry a direct connection and, if one is established, stop communicating via the relay", so after adding the address below, wait for that retry before restarting anything. That conclusion is inferred from the sentence, not measured.

---

### Give the peer a direct address

A device starts with the address `dynamic`, which means global and local discovery. The configuration page says an address other than `dynamic` needs "a protocol specific prefix", `tcp://` for TCP and `quic://` for QUIC, and that a bare IP address uses "The default port (22000)". Add the peer's LAN address next to `dynamic` rather than replacing it, so the device can still be found when it moves. VERIFIED:

```bash
syncthing cli config devices <device-id> addresses add tcp://<peer-lan-ip>:22000
```

```bash
syncthing cli config devices <device-id> addresses list
```

`list` prints index numbers. Read one address by its index, or replace it. VERIFIED:

```bash
syncthing cli config devices <device-id> addresses 0 get
```

```bash
syncthing cli config devices <device-id> addresses 0 set tcp://<peer-lan-ip>:22000
```

---

### A peer that runs in Docker

Local discovery does not cross a Docker bridge network. The official image's README says: "Docker's default network mode prevents local IP addresses from being discovered, as Syncthing can only see the internal IP address of the container", which leads to "poor transfer rates unless local device addresses are configured manually". It recommends host network mode.

When the container uses a bridge network and publishes port 22000 on TCP and UDP, every device that talks to it needs the Docker host's LAN address added as shown above, `tcp://<peer-lan-ip>:22000`, where `<peer-lan-ip>` is the address of the machine that runs Docker, not the container's internal address. The container's own setup is in [docker.md](docker.md).

---

### Ports

The firewall page lists 22000/TCP for the TCP sync protocol, 22000/UDP for QUIC, and 21027/UDP for local discovery. A host firewall that blocks 22000 forces a relay even on a LAN, so check it before blaming the network. Opening the ports is in [install-and-start.md](install-and-start.md).
