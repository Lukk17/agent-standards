# ASUS Router Checklist

Run it before calling work on the router done. The rules behind the items are in [SKILL.md](../SKILL.md).

- [ ] SSH runs on the LAN only, password login is off, and the agent's public key is in Authorized Keys
- [ ] The env file holds `ASUS_ROUTER_SSH`, `ASUS_ROUTER_SSH_PORT` and `HOMELAB_SSH_KEY`, sits outside every repository, and is readable only by the owner
- [ ] The first connection stored the router's host key, and `BatchMode=yes` connects with no prompt
- [ ] The firmware version was read with `nvram get firmver`, `nvram get buildno` and `nvram get extendno` before a recipe was applied
- [ ] No `nvram show`, no secret printed, no write under `/jffs`
- [ ] Every change had its own yes after the worst case and the undo command were stated
- [ ] The log lines and the ping log behind a diagnosis were copied out with their times
- [ ] Every router command marked UNVERIFIED stays marked until it ran on a real router
