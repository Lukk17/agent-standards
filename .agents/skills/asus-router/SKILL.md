---
name: asus-router
description: 'An ASUS router over SSH, read only unless the owner approves a change: key access, the log, WAN state. Use when the user says "read the router log" or "why does the internet drop". Not for a Proxmox host, use `proxmox`.'
metadata:
  version: "1.1.0"
---

# ASUS Router Administration

How an agent reads an ASUS router over SSH without a password, and how a change the owner approved is done. The agent logs in with an SSH key as the router's administrator, which is root on the router. So the key can change anything, and the rules below are all that keeps the agent to reading. Written for stock Asuswrt and Asuswrt-Merlin. Setup facts belong in the owner's notes, never here, and examples use `<placeholders>`.

---

### When not to activate

- A Proxmox host or a virtual machine behind the router, use `proxmox`
- A service inside the home lab, such as Home Assistant or Syncthing, use `home-assistant` or `syncthing`
- The network settings of one client machine, use `windows`, `macos`, `arch-linux` or `cachyos`

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
9. Check the router's time zone rule and the clock offset of each kind of log line before you match it against anything else, and again after each daylight saving time change. On build 386 the `pppd` lines ran one hour behind the router's own `date` at one time of the year, while other lines of the same event did not, and matched it at another.

---

### Reference files

| You are about to | Open |
|---|---|
| Turn SSH on, choose and paste the key, fill the env file, connect, take the key back | [ssh-access.md](references/ssh-access.md) |
| Read the system log, the WAN type, the interface names, the WAN port link, the uptime, ping from the router | [reading-state.md](references/reading-state.md) |
| Open the ONT management page from the LAN while the WAN runs PPPoE | [ont-access.md](references/ont-access.md) |
| Explain an internet drop: a WAN link drop, a PPPoE session drop, or an outage at the ISP | [troubleshooting-drops.md](references/troubleshooting-drops.md) |
| Name the router, a user or an address, or judge a VERIFIED mark | [conventions.md](references/conventions.md) |
| Before calling the work done | [checklist.md](references/checklist.md) |
