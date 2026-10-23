# SSH Access for an Agent

Read this before giving an agent SSH access to an ASUS router, before the first connection, and before taking the access back. The rules live in [SKILL.md](../SKILL.md). The owner does the steps in the web page. The agent only receives the values in the env file and connects with them.

Sources, fetched on 2026-10-23: the ASUS FAQ "How to log in ASUS router via Telnet?" at https://www.asus.com/support/faq/1048201/, last updated 2025/04/30, the stock firmware `FW_GT-AX6000_300610237437.zip` from https://dlcdnets.asus.com/pub/ASUS/wireless/GT-AX6000/ with SHA-256 `785dba9b1e89042f5445ce5c14e3f08955d3649ff71d41f350ace0c74f4a56c8`, unpacked in a throwaway container and read but never run, the Asuswrt-Merlin source at tag `3006.102.9` of https://github.com/RMerl/asuswrt-merlin.ng (`release/src/router/rc/ssh.c`, `release/src/router/www/Advanced_System_Content.asp`, `release/src/router/www/EN.dict`, `release/src/router/shared/defaults.c`, `release/src/router/dropbear/CHANGES` and `release/src/router/dropbear/src/default_options.h`), and the wiki page https://github.com/RMerl/asuswrt-merlin.ng/wiki/SSH, last changed 2024-12-18.

Commands marked VERIFIED were run by the owner on 2026-10-23 on a GT-AX6000 with stock firmware whose `nvram get buildno` printed `386`. Every other command here is UNVERIFIED.

---

### What answers on port 22

The router's SSH server is Dropbear. The Asuswrt-Merlin wiki says: "The router can be accessed over SSH (through Dropbear). Password-based login will use the same username and password as web access." So the user name is the one of the router's web page, `<router-admin-user>`, and that account is root on the router.

| Firmware | Dropbear | ed25519 user key |
|---|---|---|
| Stock 3.0.0.6.102_37437 for the GT-AX6000, released 2026-10-20 | 2020.81, the version string inside `/usr/bin/dropbearmulti` of the image | The binary carries the `ssh-ed25519` algorithm, and Dropbear's own changelog says under 2020.79: "Support ed25519 hostkeys and authorized_keys" |
| Stock, the tested build 386 | not read | VERIFIED: an ed25519 key logged in, and the router logged `Pubkey auth succeeded for '<router-admin-user>' with key sha1!! <fingerprint>` |
| Asuswrt-Merlin 3006.102.9 | 2026.94, from `CHANGES` | `#define DROPBEAR_ED25519 1` in `default_options.h`, and `rc/ssh.c` creates an ed25519 host key |

The wiki page names only "a RSA or ECDSA public key", which is older than ed25519 support and not a limit of current firmware. If a router ever answers `Permission denied (publickey)` to a correct ed25519 key, fall back to ECDSA as described under "The key" below.

Dropbear 2020.81 predates the Strict KEX mitigation that Dropbear added in 2024.84 for CVE-2023-48795. Dropbear's own note says "At present the flaw does not seem to reduce Dropbear's security", and with SSH on the LAN only the exposure is the LAN. Asuswrt-Merlin 3006.102.9 ships 2026.94, which has the mitigation.

The OpenSSH client may print a warning that the connection is not using a post-quantum key exchange algorithm. That is the client describing the router's older Dropbear. It does not stop the login and needs no action.

---

### The fields in the web page

The FAQ above, under "How to enable the SSH function in ASUS router?": "Click [Administration] > [System]" and "Find [Service]>[Enable SSH]. Click the dropdown list and choose [LAN only] or [LAN & WAN]." The other labels and the values each field stores were read in `Advanced_System_Content.asp` and the English dictionary of the stock image, and match the same page in the Asuswrt-Merlin source. The defaults were read in `shared/defaults.c` of the Asuswrt-Merlin source, not in the stock image.

| Label in Administration, System, Service | nvram name | Values and default | Set it to |
|---|---|---|---|
| Enable SSH | `sshd_enable` | No `0`, LAN only `2`, LAN & WAN `1`, default `0` | LAN only |
| SSH Port | `sshd_port` | 1 to 65535, default `22` | the port the owner chose, also written into `ASUS_ROUTER_SSH_PORT` |
| Allow Password Login | `sshd_pass` | Yes `1`, No `0`, default `1` | No |
| Authorized Keys | `sshd_authkeys` | text, at most 2999 characters | the agent's public key, one key per line |
| Idle Timeout | `shell_timeout`, in seconds | shown in minutes, 0 disables, default 1200 seconds | leave as it is |

Asuswrt-Merlin adds one row the stock page does not have, Allow SSH Port Forwarding, `sshd_forwarding`, default No. Leave it at No.

The page refuses to apply SSH with password login off and no key. In the Asuswrt-Merlin copy of the page the message is "You must configure at least one SSH authentication method!".

What happens on Apply, read in `rc/ssh.c`: the router writes the content of `sshd_authkeys` to `/root/.ssh/authorized_keys`, with each `>` in the stored value turned back into a line break, and starts Dropbear with `-s`, which turns password login off, when `sshd_pass` is `0`. The host keys live in `/jffs/.ssh/`, so they survive a reboot and change after a factory reset or a format of the JFFS partition.

---

### The key

One key pair serves the router and the other machines of the home lab. The private half stays in `~/.ssh` on the agent's machine and never leaves it. Only the public half is pasted into the router. If the key does not exist yet, create it on the agent's machine, with a comment that names it, here `homelab-agent`:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/<key-name> -C homelab-agent
```

```powershell
ssh-keygen -t ed25519 -f "$HOME\.ssh\<key-name>" -C homelab-agent
```

Print the public half for the owner to paste into Authorized Keys. It is one line:

```bash
cat ~/.ssh/<key-name>.pub
```

```powershell
Get-Content "$HOME\.ssh\<key-name>.pub"
```

Fallback, only if the router refuses the ed25519 key: an ECDSA key for the router alone.

```bash
ssh-keygen -t ecdsa -b 256 -f ~/.ssh/<router-key-name> -C homelab-agent
```

The router then has a key file of its own, so `HOMELAB_SSH_KEY` no longer fits it. Ask the owner which env file key should name the new file, and use that key in every command below instead.

---

### The env file

The owner keeps one env file outside every repository, readable only by the owner. The agent reads it and never prints it. The three keys for the router, one `NAME=value` per line:

```text
ASUS_ROUTER_SSH=<router-admin-user>@<router-ip>
ASUS_ROUTER_SSH_PORT=<ssh-port>
HOMELAB_SSH_KEY=~/.ssh/<key-name>
```

Restrict it on Linux and macOS:

```bash
chmod 600 <env-file>
```

Load it into the current shell without printing anything:

```bash
source <env-file>
```

---

### Connect

The first connection has to store the router's host key. `accept-new` stores a key it has not seen and still refuses one that changed. VERIFIED on build 386, where it connected and added the router to `~/.ssh/known_hosts`:

```bash
ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes -i "$HOMELAB_SSH_KEY" -p "$ASUS_ROUTER_SSH_PORT" "$ASUS_ROUTER_SSH" uptime
```

Every later call. `BatchMode=yes` makes `ssh` fail instead of asking for a password. VERIFIED on build 386, where it printed the uptime:

```bash
ssh -o BatchMode=yes -i "$HOMELAB_SSH_KEY" -p "$ASUS_ROUTER_SSH_PORT" "$ASUS_ROUTER_SSH" uptime
```

The same from PowerShell, once the env file values are in variables of the same names:

```powershell
ssh -o BatchMode=yes -i $HOMELAB_SSH_KEY -p $ASUS_ROUTER_SSH_PORT $ASUS_ROUTER_SSH uptime
```

What the answer means:

1. A line with the uptime: the key works.
2. `Permission denied (publickey)`: the router refused the key. Check that the public key in Authorized Keys is the one that matches `HOMELAB_SSH_KEY`, whole and on one line, and that Apply was pressed.
3. `Connection refused`: SSH is off, or the port differs from `ASUS_ROUTER_SSH_PORT`.
4. `REMOTE HOST IDENTIFICATION HAS CHANGED`: the router has a new host key, which is expected after a factory reset or a JFFS format and suspicious otherwise. Tell the owner and wait. Removing the old entry is the owner's call. On port 22 the entry is named by the address alone:

```bash
ssh-keygen -R <router-ip>
```

On any other port it is named `[<router-ip>]:<ssh-port>`:

```bash
ssh-keygen -R "[<router-ip>]:<ssh-port>"
```

Read which keys the router accepts right now. The file is rewritten from `sshd_authkeys` each time SSH starts. VERIFIED on build 386, where it held the pasted key, starting with `ssh-ed25519`:

```bash
ssh -o BatchMode=yes -i "$HOMELAB_SSH_KEY" -p "$ASUS_ROUTER_SSH_PORT" "$ASUS_ROUTER_SSH" cat /root/.ssh/authorized_keys
```

The file ends without a line break after the last key, so `wc -l` prints `0` for one key, measured on build 386. Count the keys by their type prefix instead, which also counts an ECDSA key:

```bash
ssh -o BatchMode=yes -i "$HOMELAB_SSH_KEY" -p "$ASUS_ROUTER_SSH_PORT" "$ASUS_ROUTER_SSH" 'grep -c -E "^(ssh-|ecdsa-)" /root/.ssh/authorized_keys'
```

---

### Taking it back

The owner does this in the web page, in the same Service section:

1. To revoke the key on the router only, delete its line from Authorized Keys and press Apply. The other home lab machines still accept it.
2. To close SSH on the router completely, set Enable SSH to No and press Apply.
3. To revoke the key everywhere, remove it from the router as in step 1 and from every other machine that lists it, and only then delete both key files on the agent's machine. Deleting only the files revokes nothing, because a copy elsewhere would still be accepted.

Then confirm from the agent's machine that the router refuses. `Permission denied (publickey)` or `Connection refused` is the expected answer:

```bash
ssh -o BatchMode=yes -i "$HOMELAB_SSH_KEY" -p "$ASUS_ROUTER_SSH_PORT" "$ASUS_ROUTER_SSH" uptime
```
