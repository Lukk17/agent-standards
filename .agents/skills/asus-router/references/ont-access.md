# Reaching the ONT Page from the LAN

Read this before trying to open the management page of the ISP's optical network terminal (ONT), or of a modem, that sits on the router's WAN port while the WAN runs PPPoE. Every step that adds an address, a firewall rule or a file is a change. The agent proposes it with the worst case and the undo command, and runs it only after the owner says yes to that exact step, as rules 2 and 3 in [SKILL.md](../SKILL.md) say.

Sources, fetched on 2026-10-23: the Asuswrt-Merlin wiki at https://github.com/RMerl/asuswrt-merlin.ng/wiki, pages "User scripts", "Access modem Web UI on WAN port (no script)" and "Jffs", the last two last changed 2024-12-18 and the wiki at its commit of 2026-10-11, the Asuswrt-Merlin source at tag `3006.102.9` (`release/src/router/rc/wan.c`, `rc/services.c` and `www/Advanced_System_Content.asp`), and the stock firmware image for the GT-AX6000, version 3.0.0.6.102_37437, read in a throwaway container.

VERIFIED on 2026-10-23 on a GT-AX6000 with stock firmware build 386, PPPoE on a VLAN: a ping from the router to the ONT's management address got 0 answers of 3, the VLAN interface carried only a `169.254.x.x/16` address, and no address in the ONT's subnet showed on the WAN side. Every command below is UNVERIFIED.

---

### Why the page cannot be reached

With PPPoE the router's internet address sits on the PPP interface, and the interface under it, the WAN port or a VLAN on it, needs no address at all. The ONT answers on its own small private subnet, such as `<ont-ip>` in `<ont-subnet>`. The router has no address in that subnet, so it has no route there, and a packet from the LAN to `<ont-ip>` leaves through the default route into the PPPoE session, where the ISP drops it.

Two things are needed:

1. An address for the router in the ONT's subnet, `<wan-side-ip>`, on the interface the ONT actually listens on.
2. Source NAT for that subnet, so the ONT sees requests coming from `<wan-side-ip>`, an address it can answer, instead of from a LAN address it has no route back to.

---

### Find the right interface and a free address

When `wan0_ifname` is a VLAN, the ISP's PPPoE runs tagged, and the ONT's management page usually answers untagged, on the port under the VLAN. That port is the last column of the VLAN's line here:

```sh
cat /proc/net/vlan/config
```

When `wan0_ifname` is not a VLAN, it is the port itself:

```sh
nvram get wan0_ifname
```

In the commands below that port is `<wan-port>`. Which subnet the ONT uses, and which address in it is free, comes from the ONT's manual or the ISP. Pick `<wan-side-ip>` in the same subnet, not the ONT's own address, and check that `<ont-subnet>` does not overlap the LAN:

```sh
nvram get lan_ipaddr
```

```sh
nvram get lan_netmask
```

---

### Try it until the next reboot, stock and Merlin alike

Stock firmware runs no user scripts. The stock GT-AX6000 image has no `/jffs/scripts` hook anywhere in `/sbin/rc`, so on stock there is no supported way to keep this across a reboot. The commands below last until the router reboots, and often less, as "What undoes it by itself" says.

Each step is a change and needs its own yes.

Step 1, the address on the WAN port. Worst case: a wrong prefix that overlaps the LAN breaks access to part of the LAN until the undo command runs or the router reboots.

```sh
ip addr add <wan-side-ip>/<prefix> dev <wan-port>
```

Step 2, source NAT for the ONT's subnet. Worst case: none beyond the ONT's subnet, because the rule matches that destination only.

```sh
iptables -t nat -I POSTROUTING -o <wan-port> -d <ont-subnet>/<prefix> -j MASQUERADE
```

Then test from the router, and from a LAN machine with a browser on `http://<ont-ip>`:

```sh
ping -c 3 -W 2 <ont-ip>
```

When the router answers but a LAN machine does not, read the forward rules before proposing anything else:

```sh
iptables -S FORWARD
```

The undo, in reverse order:

```sh
iptables -t nat -D POSTROUTING -o <wan-port> -d <ont-subnet>/<prefix> -j MASQUERADE
```

```sh
ip addr del <wan-side-ip>/<prefix> dev <wan-port>
```

---

### What undoes it by itself

1. A reboot removes both.
2. A WAN restart can remove the address. `stop_wan_if` in `rc/wan.c` sets the WAN interface to `0.0.0.0` with `ifconfig`, which clears its main address. Whether it touches the port under a VLAN was not checked.
3. A firewall restart removes the NAT rule, because the firmware rebuilds the NAT table. Many Apply buttons in the web page restart the firewall.

So after any of those, the page stops answering until the steps run again.

---

### Keep it on Asuswrt-Merlin

Asuswrt-Merlin runs shell scripts from `/jffs/scripts/` on events. The wiki page "User scripts" says: "Support for these scripts must be enabled, under Administration -> System on the webui." In 3006.102.9 that row is named "Enable JFFS custom scripts and configs", nvram `jffs2_scripts`, default No. Turning it on is itself a change for the owner.

Which hooks fit, read in the wiki and in the source:

1. Not `wan-start`. The wiki marks it "deprecated since 384.15, please use wan-event instead". `rc/wan.c` still calls it on a connected event "For backward/legacy compatibility".
2. Not `services-start` alone. It runs once at boot, "Called after all other system services have been started at boot", and the address it adds is gone after the next WAN restart, as item 2 above says.
3. `wan-event` for the address. The wiki: "$1 will contain the WAN unit" and "$2 will contain the event type", one of them `connected`. It runs again after every reconnect.
4. `nat-start` for the rule. The wiki: "Called after NAT rules (i.e. port forwards and such) have been applied to the NAT table. This is where you will want to put your own NAT table custom rules". It runs again after every firewall restart.

Before writing anything, check whether the two scripts already exist, because add-ons often install them. If one exists, the owner decides whether to add the lines to it, never to replace it:

```sh
ls -l /jffs/scripts/
```

The content of `/jffs/scripts/wan-event`, with the placeholders filled in. It adds the address only when it is missing, so a second connected event changes nothing:

```sh
#!/bin/sh
[ "$1" = "0" ] && [ "$2" = "connected" ] || exit 0
ip -4 addr show dev <wan-port> | grep -q "inet <wan-side-ip>/" || ip addr add <wan-side-ip>/<prefix> dev <wan-port>
```

The content of `/jffs/scripts/nat-start`. `-C` checks whether the rule is already there:

```sh
#!/bin/sh
iptables -t nat -C POSTROUTING -o <wan-port> -d <ont-subnet>/<prefix> -j MASQUERADE 2>/dev/null || iptables -t nat -I POSTROUTING -o <wan-port> -d <ont-subnet>/<prefix> -j MASQUERADE
```

Write each file on the agent's machine first, then copy it to the router after the owner's yes. Worst case: an existing script of the same name is overwritten, which is why the listing above comes first.

```bash
ssh -o BatchMode=yes -i "$HOMELAB_SSH_KEY" -p "$ASUS_ROUTER_SSH_PORT" "$ASUS_ROUTER_SSH" 'cat > /jffs/scripts/wan-event' < <workspace>/wan-event
```

```bash
ssh -o BatchMode=yes -i "$HOMELAB_SSH_KEY" -p "$ASUS_ROUTER_SSH_PORT" "$ASUS_ROUTER_SSH" 'cat > /jffs/scripts/nat-start' < <workspace>/nat-start
```

The wiki: "Don't forget to set any script you create as being executable", and the files need Unix line endings:

```sh
chmod a+rx /jffs/scripts/wan-event /jffs/scripts/nat-start
```

Run both once by hand to apply them now, then test as above:

```sh
/jffs/scripts/wan-event 0 connected
```

```sh
/jffs/scripts/nat-start
```

The undo: delete both files, or remove only the added lines from a script that existed before, then run the two undo commands from the section above:

```sh
rm /jffs/scripts/wan-event /jffs/scripts/nat-start
```

---

### What the wiki suggests instead, and why it does not fit PPPoE

The wiki page "Access modem Web UI on WAN port (no script)" changes the router's WAN to a static address in the modem's subnet, and as an alternative adds `ifconfig eth0:1 192.168.0.2 netmask 255.255.255.0`, with the note that it "does not persist after reboot" and should go into `init-start`. The first replaces the WAN connection type, so it cannot work while the WAN must stay PPPoE. The second names `eth0` and a fixed subnet, while the right port and subnet differ per model and per ISP, and `init-start` runs before the WAN exists, so a WAN restart clears it. The `wan-event` and `nat-start` pair above covers both cases.
