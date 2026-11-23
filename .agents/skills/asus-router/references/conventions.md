# Conventions

Companion reference for the [asus-router](../SKILL.md) skill. Load it before writing a command or a note that names the router, a user or an address, and when judging how far to trust a command in the topic files.

---

### Facts about one setup

The router address, the administrator user name, the SSH port, the ONT address, the public IP and the PPPoE user name of a real setup belong in the owner's own notes, for example `MACHINE.md` next to the global `AGENTS.md`, never in this skill and never in a shared repository. Every example uses placeholders in angle brackets: `<router-ip>`, `<router-admin-user>`, `<ssh-port>`, `<wan-ifname>`, `<ont-ip>`, `<ont-subnet>`, `<wan-side-ip>`.

---

### Verification

Stock Asuswrt and Asuswrt-Merlin share the SSH server, the system log and the WAN code, and every topic file says where Merlin differs.

Written for stock Asuswrt on the 388 and 102 firmware branches, on Wi-Fi 6 and 6E models such as the GT-AX6000, and Asuswrt-Merlin where it differs. Tool names and log texts were read in an unpacked stock firmware image for the GT-AX6000, never run, and in the Asuswrt-Merlin source and wiki and the ASUS FAQ pages named in each topic file. The image carries Dropbear, BusyBox, `ip`, `ethctl` and `ethtool`, though the tested router below had no `ethtool`. The owner tested part of it on a GT-AX6000 with stock firmware whose `nvram get buildno` printed `386`: the SSH login with an ed25519 key, the log files, the `nvram get` reads, the PPP options, the log lines of PPPoE session drops, the WAN port link, the interfaces, routes and counters, and ping and traceroute from the router. Those commands and lines are marked VERIFIED with that build named. Every other command that runs on a router is UNVERIFIED until it is tested on a real one.
