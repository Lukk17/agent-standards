# Samba

Read this before setting up the network drive or changing its login. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab on 2026-10-23 with `dockurr/samba:4.23.10`. Every other command here is UNVERIFIED.

Sources, fetched on 2026-10-23: the image README at https://github.com/dockur/samba, and the Compose page on interpolation at https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/.

---

### The service

`dockurr/samba` is configured with environment variables: `NAME` for the share, `USER` and `PASS` for the one login, and `UID` and `GID` for the owner of every file it writes. The README's own example uses `USER: "samba"` and `PASS: "secret"`, so the Compose file refuses to start without real values instead of falling back to those:

```yaml
samba:
  image: dockurr/samba:4.23.10
  environment:
    - NAME=files
    - USER=${SAMBA_USER:?set SAMBA_USER in .env}
    - PASS=${SAMBA_PASS:?set SAMBA_PASS in .env}
    - UID=1000
    - GID=1000
  ports:
    - "445:445/tcp"
  volumes:
    - type: bind
      source: /mnt/data
      target: /shared
      bind:
        create_host_path: false
```

Only port 445 is needed. Give `UID` and `GID` the same pair every other container that writes to the disk runs as, so a file written over Samba can be changed in File Browser and the other way round. VERIFIED: both write as 1000 on the homelab.

The server runs no discovery service, so it does not appear under Network in Windows. Type the address, `\\<name>.internal\files` on Windows and `smb://<name>.internal/files` elsewhere, where `<name>` is any `.internal` name, since the AdGuard Home wildcard sends all of them to the VM.

---

### The login file

The user and password live in `.env` next to the Compose file, never in the Compose file. The agent never types or sees the password: the owner types it, on the VM.

Ask for the user name. It shows as it is typed:

```bash
read -r -p 'Samba user: ' SAMBA_USER
```

Leave `$`, `#` and quotes out of the password, because the command below writes the value unquoted, see [deploy-and-logs.md](deploy-and-logs.md#dollar-signs-in-compose). The Compose page says "Unquoted and double-quoted (`"`) values have interpolation applied", so an unquoted `$` starts a variable name, and an unquoted value with a space before `#` ends there.

Ask for the password. It does not show:

```bash
read -r -s -p 'Samba password: ' SAMBA_PASS; echo
```

Write both. This replaces the whole file, so add any other line it held, such as a Plex claim token, afterwards:

```bash
printf 'SAMBA_USER=%s\nSAMBA_PASS=%s\n' "$SAMBA_USER" "$SAMBA_PASS" > <stack-dir>/.env
```

```bash
chmod 600 <stack-dir>/.env
```

```bash
unset SAMBA_USER SAMBA_PASS
```

Check by length, never by value. This prints each name and how long its value is:

```bash
awk -F= '{print $1, length($2)}' <stack-dir>/.env
```

Every number must be above 0. VERIFIED: the first attempt on the homelab left `SAMBA_USER` empty, and every `docker compose` command for the whole stack refused with `required variable SAMBA_USER is missing a value` until the file was written again.

Then start it:

```bash
cd <stack-dir> && docker compose up -d samba
```

---

### Check it

The port, from any machine on the network:

```bash
nc -zv <vm-ip> 445
```

```powershell
Test-NetConnection <vm-ip> -Port 445
```

A drive letter on Windows, which asks for the password:

```powershell
net use Z: \\<vm-ip>\files /persistent:yes /user:<samba-user>
```

Windows may offer the Windows login instead of the Samba one, so name the user. A name that does not resolve while the address works means the machine is not using AdGuard Home for DNS.
