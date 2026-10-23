# Intermittent Internet Drops

Read this before explaining why the internet behind an ASUS router drops now and then, and before saying whose fault it is. The answer comes from two sources read side by side: the router's log, which says what the router saw, and a ping log kept on a machine in the LAN, which says when traffic really stopped. The log lines and the commands that read them are in [reading-state.md](reading-state.md). The rules live in [SKILL.md](../SKILL.md), and rule 8 there holds here: no verdict without the lines and times that show it.

Sources, fetched on 2026-10-23: the same source files and stock image as [reading-state.md](reading-state.md), and `pppd/pppd/lcp.c` in the Asuswrt-Merlin source at tag `3006.102.9`. The ping log command was run on 2026-10-23 with `ping` from iputils 20240905 in a throwaway Debian 13 container, against a local address and against an address that never answers. The patterns marked VERIFIED were seen by the owner on 2026-10-23 on a GT-AX6000 with stock firmware build 386 and PPPoE on a VLAN, over about 4.5 days of log. Every router command is UNVERIFIED unless [reading-state.md](reading-state.md) marks it.

---

### Three kinds of drop

| Kind | In the router log | In the ping log | Whose side |
|---|---|---|---|
| WAN port link drop | `WAN(0) link down.` from `wanduck` and the kernel's `Link DOWN.` for the WAN port, later `link up` and `Link Up at <speed>` | everything beyond the router fails, the router itself answers | the cable, the ONT or modem, or its power. The ONT rebooting shows as exactly this |
| PPPoE session drop | `pppd` lines without any link line: `Serial link appears to be disconnected.`, `Fail to connect with some issues.`, `Connection terminated.`, then `Connected to <mac> via interface <wan-ifname>`, `Connect: ppp0 <--> <wan-ifname>`, the address lines and `WAN was restored.` | at least about 60 seconds of failure before the `pppd` lines, then a short gap while the session comes back | beyond the port: the ONT's fibre side or the ISP's access server, because the port stayed up |
| Drop beyond the router | no `pppd` line and no link line at that time | the ISP's peer or the internet fails for a while, the router answers | beyond the router, while the PPPoE session and the port stayed up |

Two more lines change the reading of a PPPoE drop. `LCP terminated by peer` means the ISP ended the session itself, often a planned daily reconnect at the same hour each day. `Failed to authenticate ourselves to peer.` means the ISP refused the login, which is an account or ISP problem, not a line problem.

On a DHCP WAN the session rows do not apply. Look for `dhcp client: deconfig` or `leasefail` instead. `dhcp client: renew` with the same address is a normal renewal and no drop at all.

VERIFIED on build 386: in 4.5 days every drop in the log was a PPPoE session drop. `WAN was restored.` came about 11 to 15 seconds after the drop lines, and no WAN port link down line appeared at all.

---

### Why a short outage leaves no line

The PPPoE keep alive decides what the log can show. `rc/pppd.c` writes `lcp-echo-interval`, `lcp-echo-failure` and `lcp-echo-adaptive` into the PPP options, and on build 386 they were 6, 10 and set, VERIFIED. `lcp.c` says adaptive echo requests are sent "only if the link was idle", and after 10 unanswered requests `pppd` logs `No response to 10 echo-requests` and `Serial link appears to be disconnected.`

So the session ends only after about 60 seconds in which nothing came back from the ISP. A gap shorter than that, or one where the ISP's access server still answers keep alive requests while traffic to the internet fails, never ends the session and leaves no `pppd` line. Only the ping log shows it. That is the third row of the table, and it is why the ping log is not optional.

---

### Keep a ping log in the LAN

Run it on a machine in the LAN that stays on, not on the router, because the router's `/tmp` is lost on reboot and its `/jffs` is flash. Ping three targets, each in its own log, so the logs show where traffic stopped:

1. The router's LAN address, `<router-ip>`. If this fails, the problem is inside the LAN or the router itself.
2. The ISP's peer, `wan0_gateway` from [reading-state.md](reading-state.md), `<isp-gateway>`. If this fails while the router answers, the problem is on the WAN side.
3. A public address by number, `<public-ip>`. If this fails while the ISP's peer answers, the problem is beyond the ISP's first hop.

Each line of iputils `ping` with `-D` starts with a Unix time in seconds, which has no time zone, and `-O` writes `no answer yet for icmp_seq=<n>` for every lost reply. Measured in a container, the file grows line by line while `ping` runs. One target per command, on Linux:

```bash
nohup ping -D -O -n -W 2 -i 1 <router-ip> >> <workspace>/ping-router.log 2>&1 &
```

```bash
nohup ping -D -O -n -W 2 -i 1 <isp-gateway> >> <workspace>/ping-isp-gateway.log 2>&1 &
```

```bash
nohup ping -D -O -n -W 2 -i 1 <public-ip> >> <workspace>/ping-public.log 2>&1 &
```

Turn the Unix times of the lost replies into local time, on the agent's machine:

```bash
grep 'no answer yet' <workspace>/ping-public.log | awk -F'[][]' '{ print strftime("%F %T %z", $2) }'
```

That `strftime` call needs GNU awk. Stop the three logs when the drops have been caught. The `^` matters: without it the pattern also matches the shell that runs `pkill`, and kills it, which happened in the container test:

```bash
pkill -f '^ping -D -O'
```

---

### Read both side by side

1. Copy the router log to the agent's machine, as [reading-state.md](reading-state.md) shows, as soon as a drop happened. The log covers only a few days.
2. Find the clock offset of each tag before matching anything, as "The clock in the log is not one clock" in [reading-state.md](reading-state.md) says. On build 386 the `pppd` lines were UTC+1 while the router's `date` and the `wan:` lines were in local summer time, VERIFIED.
3. List the drops in the ping log: runs of `no answer yet`, each with its start, its end and its length.
4. For each drop, look in the router log within a minute of its start, after correcting the offset.

Then:

1. `pppd` drop lines about 60 seconds after the ping log started failing, and no link line: a PPPoE session drop, row 2. The ISP side stopped answering first, and the router ended the session because of it.
2. A link line at the start of the drop: a WAN port link drop, row 1. Check the cable and the ONT's power before calling the ISP.
3. No `pppd` line and no link line within a minute of the drop: the PPPoE session and the port stayed up while traffic stopped beyond the router, row 3. Which hop failed is in the ISP gateway and public logs.
4. The router's own address failing too: not a WAN problem. Check the router's uptime for a reboot, and the LAN.
5. Drops at the same time each day with `LCP terminated by peer`: the ISP's planned reconnect.

---

### What to give the owner

1. The list of drops, each with its start in local time, its length and its kind from the table.
2. For each kind, the router log lines and the ping log lines that show it, copied, with the offset that was applied.
3. Whose side each kind points to, and what would settle it, for example a ping log to the ONT's own address through [ont-access.md](ont-access.md), which separates the fibre side from the router's port: when the ONT still answers while the ISP's peer does not, the drop is on the fibre or ISP side.
4. Anything that would need a change on the router, such as the ONT address, proposed with its worst case and its undo, and left for the owner's yes.

Facts about the owner's line, such as the ISP, the addresses and the times of day, go into the owner's notes, never into this skill.
