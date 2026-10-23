---
name: asus-router
description: 'Working on an ASUS router from an agent over SSH, read only unless the owner says yes to one exact change: stock Asuswrt 3.0.0.4.388 and 3.0.0.6.102 on Wi-Fi 6 and 6E models such as the GT-AX6000, and Asuswrt-Merlin where it differs. SSH on the LAN only with an ed25519 key and no password login, the env file keys ASUS_ROUTER_SSH, ASUS_ROUTER_SSH_PORT and HOMELAB_SSH_KEY, taking the key back, the system log in /tmp/syslog.log or /jffs/syslog.log, WAN link, PPPoE and DHCP lines in the log, nvram get for the WAN type and interfaces, the WAN port link, ping from the router, reaching the ONT page from the LAN while the WAN runs PPPoE, and telling a WAN link drop from an ISP outage. Use when you say "let the agent into my router", "read the router log", "why does the internet drop", "is the WAN PPPoE or DHCP", "I cannot open the ONT page", or "was it the cable or the ISP". Not for a Proxmox host behind the router, use `proxmox`, and not for judging an exposed port, use `security-review`.'
---

# ASUS Router Administration

How an agent reads an ASUS router over SSH without a password, and how a change the owner approved is done. The agent logs in with an SSH key as the router's administrator, which is root on the router. So the key can change anything, and the rules below are all that keeps the agent to reading. Stock Asuswrt and Asuswrt-Merlin share the SSH server, the system log and the WAN code, and every topic file says where Merlin differs.

Baseline, fetched and read on 2026-10-23: the stock firmware image for the GT-AX6000, version 3.0.0.6.102_37437 released on 2026-10-20, unpacked in a throwaway container and read file by file, never run. It carries Dropbear 2020.81, BusyBox 1.24.1, `ip`, `ethctl` and `ethtool`, though the tested router below had no `ethtool`. Beside it the Asuswrt-Merlin source at tag 3006.102.9 of 2026-09-23, the Asuswrt-Merlin wiki at its commit of 2026-10-11, and the ASUS FAQ pages named in each topic file. On 2026-10-23 the owner tested part of it on a GT-AX6000 with stock firmware whose `nvram get buildno` printed `386`: the SSH login with an ed25519 key, the log files, the `nvram get` reads, the PPP options, the log lines of PPPoE session drops, the WAN port link, the interfaces, routes and counters, and ping and traceroute from the router. Those commands and lines are marked VERIFIED with that build named. Every other command that runs on a router is UNVERIFIED until it is tested on a real one.

| You are about to | Open |
|---|---|
| Turn SSH on, choose and paste the key, fill the env file, connect, take the key back | [ssh-access.md](references/ssh-access.md) |
| Read the system log, the WAN type, the interface names, the WAN port link, the uptime, ping from the router | [reading-state.md](references/reading-state.md) |
| Open the ONT management page from the LAN while the WAN runs PPPoE | [ont-access.md](references/ont-access.md) |
| Explain an internet drop: a WAN link drop, a PPPoE session drop, or an outage at the ISP | [troubleshooting-drops.md](references/troubleshooting-drops.md) |

---

### Facts about one setup

The router address, the administrator user name, the SSH port, the ONT address, the public IP and the PPPoE user name of a real setup belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md`, never in this skill and never in a shared repository. Every example uses placeholders in angle brackets: `<router-ip>`, `<router-admin-user>`, `<ssh-port>`, `<wan-ifname>`, `<ont-ip>`, `<ont-subnet>`, `<wan-side-ip>`.

---

### When to activate

- Giving an agent SSH access to an ASUS router, or taking it back
- Reading the router's system log, its WAN state or its uptime
- An internet connection that drops now and then, and the question of whose fault it is
- An ISP optical terminal or modem whose web page cannot be reached from the LAN
- A change on the router that the owner asked for, such as a persistent ONT route on Merlin

---

### When not to activate

- A Proxmox host or a virtual machine behind the router, use `proxmox`
- A service inside the home lab, such as Home Assistant or Syncthing, use `home-assistant` or `syncthing`
- The network settings of one client machine, use `windows`, `macos`, `arch-linux` or `cachyos`
- Judging whether an open port, a key or a firewall rule is acceptable, use `security-review`
- A script that wraps these commands on the agent's own machine, use `bash` or `powershell`

---

### Hard rules

1. The agent logs in with a key only: Enable SSH set to LAN only, Allow Password Login set to No, and the key in Authorized Keys. Never LAN & WAN, and the agent never gets the router password.
2. The agent only reads. Without the owner's explicit yes for that exact change, it never runs `reboot`, a firmware update, `nvram set`, `nvram unset` or `nvram commit`, a factory reset, `service restart_<name>` or `service stop_<name>`, a change to Wi-Fi or WAN settings, an `ip`, `ifconfig`, `route` or `iptables` command that changes state, or a write under `/jffs`. One yes covers one change.
3. Before a change, say what it changes, the worst case, and the exact command that undoes it, then wait. A change to the WAN, the firewall or SSH itself can cut the agent off, so name that case too.
4. Never run `nvram show` or `nvram getall` unfiltered and never print a value that holds a secret: the PPPoE password, a Wi-Fi key, the administrator password, a VPN key. Read named values with `nvram get <name>`.
5. The private key stays on the agent's machine, in `~/.ssh`, and is passed with `-i`. Only the public key goes into the router. Never print the private key or the env file.
6. Keep writes off the flash. A ping log or a capture goes to `/tmp` on the router, which is memory, or better to a machine in the LAN, never to `/jffs`.
7. Read the log before it rotates away. The log file is small and keeps one older copy, so copy the lines you need into the agent's workspace right after reading them, and filter and count them there, because the router's BusyBox lacks tools such as `uniq`.
8. A claim that the ISP is at fault needs the log lines and the ping log that show it, with their times, as [troubleshooting-drops.md](references/troubleshooting-drops.md) explains.
9. Check the clock offset of each kind of log line before you match it against anything else. On the tested router the `pppd` lines ran one hour behind the router's own `date`, while other lines of the same event did not.

---

### Related skills

- `proxmox` owns the Proxmox host and its virtual machines behind the router
- `home-assistant` owns Home Assistant, which can also watch the router
- `security-review` owns judging an exposed port, a key or a firewall rule
- `bash` and `powershell` own scripts on the agent's machine that wrap these commands
- `windows`, `macos`, `arch-linux` and `cachyos` own the client machines on the LAN

---

### Checklist

- [ ] SSH runs on the LAN only, password login is off, and the agent's public key is in Authorized Keys
- [ ] The env file holds `ASUS_ROUTER_SSH`, `ASUS_ROUTER_SSH_PORT` and `HOMELAB_SSH_KEY`, sits outside every repository, and is readable only by the owner
- [ ] The first connection stored the router's host key, and `BatchMode=yes` connects with no prompt
- [ ] The firmware version was read with `nvram get firmver`, `nvram get buildno` and `nvram get extendno` before a recipe was applied
- [ ] No `nvram show`, no secret printed, no write under `/jffs`
- [ ] Every change had its own yes after the worst case and the undo command were stated
- [ ] The log lines and the ping log behind a diagnosis were copied out with their times
- [ ] Every router command marked UNVERIFIED stays marked until it ran on a real router
