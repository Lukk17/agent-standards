# Reading the Router's State

Contents:

- [How to run a command on the router](#how-to-run-a-command-on-the-router)
- [Model, firmware and uptime](#model-firmware-and-uptime)
- [Where the system log lives](#where-the-system-log-lives)
- [The clock in the log is not one clock](#the-clock-in-the-log-is-not-one-clock)
- [What the WAN lines look like](#what-the-wan-lines-look-like)
- [The WAN type and interface names](#the-wan-type-and-interface-names)
- [The PPPoE keep alive settings](#the-pppoe-keep-alive-settings)
- [The WAN port link](#the-wan-port-link)
- [Addresses, routes and counters](#addresses-routes-and-counters)
- [Ping from the router](#ping-from-the-router)

Read this before reading the system log, the WAN settings, the WAN port or the uptime of an ASUS router. Every command here only prints. The rules live in [SKILL.md](../SKILL.md), and rule 4 there matters most on this page: never `nvram show`, never a value or a file that holds a secret.

Sources: a 3.0.0.6.102 stock firmware image for the GT-AX6000, unpacked in a throwaway container and read but never run, which is where every tool name and every log text below was found, the Asuswrt-Merlin 3006.102 source of https://github.com/RMerl/asuswrt-merlin.ng (`release/src/router/rc/services.c`, `rc/wanduck.c`, `rc/wan.c`, `rc/ppp.c`, `rc/pppd.c`, `rc/udhcpc.c`, `shared/misc.c`, `shared/rtstate.h`, `shared/defaults.c`, `rom/apps_scripts/getrealip.sh` and `pppd/pppd/lcp.c`), and the ASUS FAQ "How to save System Log in my ASUS router?" at https://www.asus.com/support/faq/1044954/.

Commands and log lines marked VERIFIED were run or seen by the owner on a GT-AX6000 with stock firmware whose `nvram get buildno` printed `386`. Every other command here is UNVERIFIED.

---

### How to run a command on the router

Each block below shows only the part that runs on the router. Wrap it in the connect line from [ssh-access.md](ssh-access.md), with the router part in single quotes:

```bash
ssh -o BatchMode=yes -i "$HOMELAB_SSH_KEY" -p "$ASUS_ROUTER_SSH_PORT" "$ASUS_ROUTER_SSH" 'uptime'
```

The router's shell is BusyBox `ash`. It has `grep`, `sed`, `awk`, `tail`, `head`, `sort` and `wc`, and no `uniq`, so bring the text back to the agent's machine and count it there.

---

### Model, firmware and uptime

The model. VERIFIED on build 386:

```sh
nvram get productid
```

The build number. VERIFIED on build 386:

```sh
nvram get buildno
```

The full version is `firmver`, `buildno` and `extendno` together, for example 3.0.0.6, 102 and a build number for a 3.0.0.6.102 release. Build 386 printed an `extendno` with a short git hash after the number. Both VERIFIED on build 386:

```sh
nvram get firmver
```

```sh
nvram get extendno
```

Uptime and load. VERIFIED on build 386:

```sh
uptime
```

The router's own clock and time zone, needed before any time in the log is matched against something else. VERIFIED on build 386, which printed local summer time:

```sh
date
```

---

### Where the system log lives

The web page shows the same log under System Log, General Log. The ASUS FAQ above says: "System log records are still retained after the router is rebooted/powered off. However, if you restore the router to its default, the system log records are deleted."

In the source, `get_syslog_fname` in `shared/misc.c` writes the log to `/jffs/syslog.log` when the firmware keeps a persistent log and `/jffs` is writable, and to `/tmp/syslog.log` otherwise. `start_syslogd` in `rc/services.c` starts BusyBox `syslogd` with `-s` set to `log_size`, whose default in `shared/defaults.c` is 256, in kilobytes, so the file rotates at about 256 KB into one older copy, `syslog.log-1`.

VERIFIED on build 386: `/jffs/syslog.log` and `/jffs/syslog.log-1` are the files, and `/tmp/syslog.log` and `/tmp/syslog.log-1` are symbolic links to them. The current file held 44 KB and the rotated one 262 KB, about 4.5 days together. A busy router covers fewer days.

See which files exist on this router:

```sh
ls -l /tmp/syslog.log /tmp/syslog.log-1 /jffs/syslog.log /jffs/syslog.log-1
```

Copy both files, the older first, to the agent's machine and work on the copy. Run this on the agent's machine, with a path in the agent's workspace. VERIFIED on build 386:

```bash
ssh -o BatchMode=yes -i "$HOMELAB_SSH_KEY" -p "$ASUS_ROUTER_SSH_PORT" "$ASUS_ROUTER_SSH" 'cat /jffs/syslog.log-1 /jffs/syslog.log' > <workspace>/router-syslog.log
```

On a router whose log is in `/tmp` only, read `/tmp/syslog.log-1 /tmp/syslog.log` instead. The last lines, on the router:

```sh
tail -n 100 /jffs/syslog.log
```

VERIFIED on build 386.

The WAN lines from the copy, on the agent's machine:

```bash
grep -E 'WAN[ _]Connection|pppd|Link (DOWN|Up)|dhcp client|wan:' <workspace>/router-syslog.log
```

How often each kind of WAN message appears, on the agent's machine:

```bash
grep -E 'WAN[ _]Connection' <workspace>/router-syslog.log | sed -E 's/^.*WAN[ _]Connection: //' | sort | uniq -c | sort -rn
```

---

### The clock in the log is not one clock

VERIFIED on build 386: `date` on the router printed the local summer time, the `pppd` lines and most other daemon lines were one hour behind it, and the `wan: finish adding multi routes` lines of the same reconnect were in local time, one hour after the `pppd` lines of the same event. Matched against an outside ping log kept in UTC, the `pppd` times were UTC+1.

So before you match a log line against a ping log or against another machine:

1. Find one event that shows in both sources, such as a reconnect, and read the difference.
2. Do this for each tag you use, `pppd`, `WAN Connection` and `wan`, because they can differ from each other.
3. Write the offset you found next to the result.

---

### What the WAN lines look like

`logmessage` in `shared/misc.c` sends each firmware message with its title as the tag. The Asuswrt-Merlin 3006.102 source turns the space in a title into an underscore, `WAN_Connection`, and build 386 showed `WAN Connection` with a space, so match both. The texts below were all found in the 3.0.0.6.102 stock image, in `/sbin/rc`, `/usr/sbin/pppd`, `/usr/lib/pppd/rp-pppoe.so` and the kernel module `bcm_enet.ko`, unless the row says it was seen on build 386.

| Line | Comes from | Means |
|---|---|---|
| `pppd[<pid>]: No response to 10 echo-requests` | `pppd`, at info level | the ISP side stopped answering the keep alive requests |
| `pppd[<pid>]: Serial link appears to be disconnected.` | `pppd`, seen on build 386 | the PPPoE session is being ended for that reason |
| `WAN Connection: Fail to connect with some issues.` | `wanduck`, seen on build 386 | the firmware noticed the session went down |
| `pppd[<pid>]: Connection terminated.` | `pppd`, seen on build 386 | the session is gone |
| `pppd[<pid>]: Modem hangup` | `pppd`, seen on build 386, not every time | the PPPoE layer under the session closed |
| `Failed to disconnect PPPoE socket: 114 Operation already in progress` | the PPPoE plugin, seen on build 386, not every time | cleanup noise during the same drop |
| `Connected to <mac> via interface <wan-ifname>` | the PPPoE plugin, seen on build 386 | a new PPPoE session was found with the ISP's access server |
| `Connect: ppp0 <--> <wan-ifname>` | `pppd`, seen on build 386 | the PPP link is up again |
| `local  IP address <ip>` and `remote IP address <ip>` | `pppd`, seen on build 386 | the addresses of the new session |
| `WAN Connection: WAN was restored.` | `wanduck`, seen on build 386 | the firmware sees the internet back, on build 386 about 11 to 15 seconds after the drop lines |
| `wan: finish adding multi routes` | the firmware, seen on build 386 | routes set again after the WAN came up |
| `LCP terminated by peer (<text>)` | `pppd` | the ISP ended the session on purpose, for example a forced daily reconnect |
| `WAN Connection: No response from ISP.` | `wanduck` | PPPoE got no answer from any access server |
| `WAN Connection: Failed to authenticate ourselves to peer.` | `wanduck` | the ISP refused the PPPoE user name or password |
| `WAN Connection: WAN(0) link down.` and `WAN(0) link up.` | `wanduck` | the cable link on the WAN port went down or came back |
| `<if> (<Ext or Int> switch port: <n>) (Logical Port: <n>) (phyId: <id>) Link DOWN.` | kernel, Broadcom `bcm_enet.ko` | the same port link loss, from the driver |
| `<if> (... ) Link Up at <speed> mbps <full or half> duplex` | kernel, Broadcom `bcm_enet.ko` | the port link is back, with its speed |
| `dhcp client: bound <ip>/<mask> via <gateway> for <n> seconds.` | `rc`, DHCP WAN only | a new lease, `renew` instead of `bound` when it was renewed |
| `dhcp client: deconfig` and `dhcp client: leasefail` | `rc`, DHCP WAN only | the lease was dropped, or no DHCP server answered |
| `WAN Connection: WAN was exceptionally disconnected.` | `wanduck` | the firmware lost the WAN for a reason it did not name |

---

### The WAN type and interface names

The connection type. `dhcp`, `static`, `pppoe`, `pptp` or `l2tp`, and on some regional firmware `lw4o6`, `v6plus`, `ocnvc`, `dslite` or `v6opt`, read in `get_wan_proto` in `shared/misc.c`. VERIFIED on build 386, which printed `pppoe`:

```sh
nvram get wan0_proto
```

The interface the WAN runs on. It is the WAN port itself, such as `eth0`, or a VLAN on it when the ISP needs a VLAN tag, named `vlan<id>`. VERIFIED on build 386, which printed a VLAN interface:

```sh
nvram get wan0_ifname
```

The interface that carries the default route. `ppp0` or similar for PPPoE, the same as `wan0_ifname` for DHCP or a static address. VERIFIED on build 386, which printed `ppp0`:

```sh
nvram get wan0_gw_ifname
```

The PPP interface name, which `rc/ppp.c` sets when the session comes up. VERIFIED on build 386, which printed `ppp0`:

```sh
nvram get wan0_pppoe_ifname
```

The WAN address and the gateway. With PPPoE, `rc/ppp.c` stores the session's local address in `wan0_ipaddr` and the ISP's peer in `wan0_gateway`. Both are facts about one setup, so they stay out of shared files. Both VERIFIED on build 386:

```sh
nvram get wan0_gateway
```

```sh
nvram get wan0_ipaddr
```

The public address the router found with STUN, and whether it found one. `getrealip.sh` sets `wan0_realip_state` to `2` when it got an answer and `1` when it did not. An address in `wan0_realip_ip` that differs from `wan0_ipaddr` means the ISP puts the router behind its own NAT. Both VERIFIED on build 386, where `wan0_realip_state` printed `2`:

```sh
nvram get wan0_realip_ip
```

```sh
nvram get wan0_realip_state
```

The WAN state as the firmware sees it, from `shared/rtstate.h`. The three commands below are VERIFIED on build 386, which printed `2`, `0` and `0` on a working line:

```sh
nvram get wan0_state_t
```

| `wan0_state_t` | Meaning |
|---|---|
| `0` | initializing |
| `1` | connecting |
| `2` | connected |
| `3` | disconnected |
| `4` | stopped, with the reason in `wan0_sbstate_t` |
| `5` | disabled |
| `6` | stopping |

```sh
nvram get wan0_sbstate_t
```

| `wan0_sbstate_t` | Reason |
|---|---|
| `0` | none |
| `1` | PPP, no response |
| `2` | PPP, authentication failed |
| `3` | DHCP lease dropped |
| `4` | invalid IP address |
| `5` | stopped by hand |
| `6` | system error |
| `7` | the WAN address equals the gateway |
| `10` | PPP, ended for lack of activity |

```sh
nvram get wan0_auxstate_t
```

`wan0_auxstate_t` is `0` when nothing is wrong, `1` when the WAN port has no link, and `2` when the link is up but the router sees no internet activity.

---

### The PPPoE keep alive settings

`rc/pppd.c` writes the PPP options to `/tmp/ppp/options.wan0`. That file also holds the PPPoE user name and password, on the lines starting with `user` and `password`, so never print it whole. Read only the keep alive lines. VERIFIED on build 386, which showed `lcp-echo-interval 6`, `lcp-echo-failure 10` and `lcp-echo-adaptive`:

```sh
grep '^lcp-echo' /tmp/ppp/options.wan0
```

What they mean, from `pppd/pppd/lcp.c`: `lcp-echo-adaptive` sends a keep alive request only when nothing was received in the last interval, "request echo only if the link was idle". With an interval of 6 seconds and 10 failures, the session ends only after about 60 seconds in which nothing at all came back from the ISP. A shorter gap never ends the PPPoE session, so it leaves no `pppd` line in the log.

---

### The WAN port link

The kernel's view of the link, `1` for up and `0` for down, on the WAN port and not on a VLAN or PPP interface. Both VERIFIED on build 386, where the WAN port was `eth0` and printed `1` and `up`:

```sh
cat /sys/class/net/<wan-port>/carrier
```

```sh
cat /sys/class/net/<wan-port>/operstate
```

On a WAN that runs on a VLAN, find the port under it. The last column of the VLAN's line names the port. VERIFIED on build 386, which listed the WAN VLAN on `eth0` and, beside it, internal VLANs such as `eth1.501` and `eth1.502` on the LAN ports, which are not the WAN:

```sh
cat /proc/net/vlan/config
```

Speed and duplex with Broadcom's own tool, `/bin/ethctl`. VERIFIED on build 386, where it printed `Auto-Negotiation: Enabled`, `PHY Capabilities: 2.5GFD|1GFD|100MFD` and `Link is Up at Speed: 1G, Duplex: FD`:

```sh
ethctl <wan-port> media-type
```

Do not count on `ethtool`. Build 386 answered `sh: ethtool: not found`, VERIFIED, although the 3.0.0.6.102 image carries `/usr/sbin/ethtool`. Use it only where `which ethtool` finds it:

```sh
which ethtool
```

Older Broadcom models that are not on Broadcom's HND platform used `robocfg show` for the switch ports. The stock GT-AX6000 image has no `robocfg`, so use the commands above there.

---

### Addresses, routes and counters

```sh
ip -4 addr show
```

The routing table. VERIFIED on build 386:

```sh
ip route show
```

One interface. On the PPP interface it shows the MTU, 1492 for PPPoE on build 386, and the ISP's peer as `P-t-P`. VERIFIED on build 386 with `ppp0`:

```sh
ifconfig <wan-ifname>
```

The bytes, errors and drops of one interface. The PPP interface is created again for each session, so its counters start from zero at every reconnect, while the port's counters last until a reboot. VERIFIED on build 386 with `ppp0`:

```sh
ip -s link show <wan-ifname>
```

---

### Ping from the router

BusyBox `ping` takes `-c` for the count, `-W` for the time to wait for an answer and `-I` for the interface to send from. The ISP's peer, the first hop beyond the router:

```sh
ping -c 5 -W 2 <isp-gateway>
```

An address on the internet, by number, so a DNS failure does not hide behind it. VERIFIED on build 386 with `-c 3`:

```sh
ping -c 3 -W 2 <public-ip>
```

The same by name, which also tests the router's DNS:

```sh
ping -c 5 -W 2 <public-host-name>
```

The first hops of the route to it, with BusyBox `traceroute`, numbers only, three hops and two seconds per answer. VERIFIED on build 386:

```sh
traceroute -n -m 3 -w 2 <public-ip>
```
