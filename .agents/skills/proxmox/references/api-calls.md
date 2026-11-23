# API Calls

Contents:

- [The env file](#the-env-file)
- [Verify the certificate](#verify-the-certificate)
- [Call the API without the secret on the command line](#call-the-api-without-the-secret-on-the-command-line)
- [Reading](#reading)
- [Calls that change something](#calls-that-change-something)
- [Create and delete a VM](#create-and-delete-a-vm)
- [pvesh is for the host, not the agent](#pvesh-is-for-the-host-not-the-agent)

Read this before calling the API of a Proxmox VE host. The token the calls use is the admin token of [admin-token.md](admin-token.md), or one of the alternatives in [narrower-tokens.md](narrower-tokens.md) when the owner chose one. The rules live in [SKILL.md](../SKILL.md), and rule 4 there holds for every token: the agent asks the owner before every change, and rule 9 before every delete. Every command here is UNVERIFIED. The API paths and the privilege each one needs were checked against the API schema of the API viewer.

Sources: the user management chapter https://pve.proxmox.com/pve-docs/chapter-pveum.html, the API viewer https://pve.proxmox.com/pve-docs/api-viewer/, the certificate section of https://pve.proxmox.com/pve-docs/chapter-sysadmin.html, `src/PVE/API2/Qemu.pm` in `qemu-server`, and the curl manual https://curl.se/docs/manpage.html.

---

### The env file

The owner fills one file outside every repository and makes it readable only by himself. The agent reads it, never prints it, and never copies it.

| Platform | Path |
|---|---|
| Linux and macOS | `~/.config/proxmox/agent.env` |
| Windows | `%USERPROFILE%\.config\proxmox\agent.env` |

The content, one `NAME=value` per line, no quotes, no spaces around `=`:

```text
PVE_API_URL=https://<proxmox-host>:8006/api2/json
PVE_TOKEN_ID=<user>@<realm>!<token-id>
PVE_TOKEN_SECRET=<secret>
PVE_PIN=sha256//<base64-public-key-hash>
PVE_CA_FILE=<path-to-pve-root-ca.pem>
```

`PVE_PIN` and `PVE_CA_FILE` are alternatives, see the next section. With Alternative 2 or 3 of [narrower-tokens.md](narrower-tokens.md), the owner fills a second file beside it, `agent-change.env` in the same folder, with the same five names and the change token in `PVE_TOKEN_ID` and `PVE_TOKEN_SECRET`. Restrict both files the same way. On Linux and macOS:

```bash
chmod 600 ~/.config/proxmox/agent.env
```

On Windows, remove inherited access and give the owner alone full control:

```powershell
icacls "$env:USERPROFILE\.config\proxmox\agent.env" /inheritance:r /grant:r "${env:USERNAME}:F"
```

Load it into the current shell without printing anything:

```bash
source ~/.config/proxmox/agent.env
```

```powershell
Get-Content "$env:USERPROFILE\.config\proxmox\agent.env" | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object { $name, $value = $_ -split '=', 2; Set-Variable -Name $name -Value $value -Scope Global }
```

---

### Verify the certificate

The host uses a certificate signed by its own cluster CA. The certificate section says the default node certificate "is signed by the cluster CA and therefore not automatically trusted by browsers and operating systems", and that to trust it you "copy `/etc/pve/pve-root-ca.pem` from any cluster node out of band", because "There is no API or web interface endpoint for downloading the file."

Two ways, in order of preference:

1. The owner copies `/etc/pve/pve-root-ca.pem` to the agent's machine, and curl gets `--cacert "$PVE_CA_FILE"`. If curl then reports that the name in `PVE_API_URL` does not match the certificate, use the pin instead.
2. Pin the public key. The curl manual says `--pinnedpubkey` "is independent of option --insecure. If you use both options together then the peer is still verified by public key." So `-k` together with `--pinnedpubkey "$PVE_PIN"` still refuses any other server.

The owner computes the pin on the host from the certificate `pveproxy` serves, `/etc/pve/local/pveproxy-ssl.pem` when a custom or ACME certificate is installed, otherwise `/etc/pve/local/pve-ssl.pem`:

```bash
openssl x509 -in /etc/pve/local/pve-ssl.pem -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | openssl enc -base64
```

`PVE_PIN` is `sha256//` followed by that output. A certificate renewal that keeps the key keeps the pin. A new key needs a new pin, and curl then fails closed, which is what a pin is for.

---

### Call the API without the secret on the command line

The chapter says: "To use an API token, set the HTTP header 'Authorization' to the displayed value of the form `PVEAPIToken=USER@REALM!TOKENID=UUID`". A header on the command line shows up in the process list, and the curl manual says "Using @- makes curl read the header file from stdin". `printf` is a shell builtin, so the secret never becomes a process argument.

In bash or zsh, with the pin:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- "$PVE_API_URL/version"
```

With the CA file:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s --cacert "$PVE_CA_FILE" -H @- "$PVE_API_URL/version"
```

In PowerShell, call `curl.exe` by that name, because `curl` is an alias for `Invoke-WebRequest` in Windows PowerShell 5.1, and quote `@-`. The curl manual lists Schannel, the Windows TLS library, as supporting sha256 pins:

```powershell
"Authorization: PVEAPIToken=$PVE_TOKEN_ID=$PVE_TOKEN_SECRET" | curl.exe -s -k --pinnedpubkey $PVE_PIN -H '@-' "$PVE_API_URL/version"
```

A refused call is not a reason to ask for a stronger role. Report it with the HTTP status curl returns. Which status Proxmox uses for a bad token and for a missing privilege was not measured here.

---

### Reading

Every call below works with the admin token, and with `PVEAuditor` on `/` in the alternatives. Put the path after `$PVE_API_URL` in the bash or PowerShell form above. Responses are JSON with the result under `data`.

| What | Path | Privilege, from the API schema |
|---|---|---|
| API version | `/version` | any user |
| Nodes | `/nodes` | any user |
| Every VM and container in the cluster | `/cluster/resources?type=vm` | any user, filtered to what the token may see |
| VMs on one node | `/nodes/<node>/qemu` | lists only VMs with `VM.Audit` |
| One VM's configuration | `/nodes/<node>/qemu/<vm-id>/config` | `VM.Audit` on `/vms/<vm-id>` |
| One VM's snapshots | `/nodes/<node>/qemu/<vm-id>/snapshot` | `VM.Audit` |
| Storage use on one node | `/nodes/<node>/storage` | lists only storages with `Datastore.Audit` |
| One storage | `/nodes/<node>/storage/<storage>/status` | `Datastore.Audit` |
| Thin pools with data and metadata use | `/nodes/<node>/disks/lvmthin` | `Sys.Audit` on `/` |
| Backup jobs | `/cluster/backup` | `Sys.Audit` on `/` |
| The token's own effective permissions | `/access/permissions` | its own |

For example, every VM in the cluster:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- "$PVE_API_URL/cluster/resources?type=vm"
```

```powershell
("Authorization: PVEAPIToken=$PVE_TOKEN_ID=$PVE_TOKEN_SECRET" | curl.exe -s -k --pinnedpubkey $PVE_PIN -H '@-' "$PVE_API_URL/cluster/resources?type=vm" | ConvertFrom-Json).data | Select-Object vmid, name, node, status, maxdisk, disk
```

The schema lists `vmid`, `name`, `node`, `status`, `maxdisk` and `disk` among the fields of `/cluster/resources`, and describes `maxdisk` for a VM as the "root image size" and `disk` as "used root image space". Neither is the guest's file system use, so read real use inside the guest with `df -h` or `Get-Volume`.

---

### Calls that change something

Only after the owner said yes to that one change, with the worst case and the undo stated first. With the admin token, each call uses the token loaded from `agent.env`, the same as a read.

With Alternative 2 or 3, the change token sits in `agent-change.env`. Run the same call inside a subshell that loads that file first, `( source ~/.config/proxmox/agent-change.env && <the call> )`, so the change token is gone from the shell when the call ends and every later call reads with the read-only token again.

A form value goes through `--data-urlencode`, because in form data a bare `+` is read as a space, and the `+` in a resize size is what makes it a growth rather than an absolute size.

Grow a disk by `<size>` gigabytes, always with the `+`, as [disk-resize.md](disk-resize.md) explains:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- -X PUT --data-urlencode 'disk=<disk-slot>' --data-urlencode 'size=+<size>G' "$PVE_API_URL/nodes/<node>/qemu/<vm-id>/resize"
```

```powershell
"Authorization: PVEAPIToken=$PVE_TOKEN_ID=$PVE_TOKEN_SECRET" | curl.exe -s -k --pinnedpubkey $PVE_PIN -H '@-' -X PUT --data-urlencode 'disk=<disk-slot>' --data-urlencode 'size=+<size>G' "$PVE_API_URL/nodes/<node>/qemu/<vm-id>/resize"
```

In PowerShell with Alternative 2 or 3, read `agent-change.env` into a table inside a script block, so the change token is gone when the block ends:

```powershell
& { $pve = @{}; Get-Content "$env:USERPROFILE\.config\proxmox\agent-change.env" | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object { $name, $value = $_ -split '=', 2; $pve[$name] = $value }; "Authorization: PVEAPIToken=$($pve.PVE_TOKEN_ID)=$($pve.PVE_TOKEN_SECRET)" | curl.exe -s -k --pinnedpubkey $pve.PVE_PIN -H '@-' -X PUT --data-urlencode 'disk=<disk-slot>' --data-urlencode 'size=+<size>G' "$($pve.PVE_API_URL)/nodes/<node>/qemu/<vm-id>/resize" }
```

Take a snapshot:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- -X POST --data-urlencode 'snapname=<snapshot-name>' --data-urlencode 'description=<why>' "$PVE_API_URL/nodes/<node>/qemu/<vm-id>/snapshot"
```

Shut a VM down cleanly. The schema describes `shutdown` as "similar to pressing the power button on a physical machine" and `stop` as "akin to pulling the power plug of a running computer and may damage the VM data", so `stop` is only for a guest that does not react to `shutdown`, and only after the owner said yes to that as well. Put `start` in place of `shutdown` to start one:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- -X POST "$PVE_API_URL/nodes/<node>/qemu/<vm-id>/status/shutdown"
```

Each of these starts a task and returns its ID under `data`, which the schema calls "the task ID" for resize and snapshot. Put it in place of `<upid>` and follow the task with the token from `agent.env`, which may, because the admin token, and `PVEAuditor` on `/` in the alternatives, give `Sys.Audit` on every node. The schema gives `status` as `running` or `stopped` and `exitstatus` as an optional string. A task is finished at `stopped`, and that it succeeded when `exitstatus` reads `OK` was not measured here:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- "$PVE_API_URL/nodes/<node>/tasks/<upid>/status"
```

---

### Create and delete a VM

The calls an agent needs to build a whole VM itself: pick a VM ID, put an ISO on a storage, create the VM with a disk, a CD drive with the ISO and a network device on a bridge, start it, and delete a VM nobody needs any more. The admin token can make every one of them. Each step needs its own yes from the owner, and a delete needs a yes for that one VM after the agent named it by ID and name, its node, and its newest backup with the date, as rule 9 in [SKILL.md](../SKILL.md) says. A deleted VM has no undo except restoring a backup, see "The risk, in plain words" under Alternative 3 in [narrower-tokens.md](narrower-tokens.md#the-risk-in-plain-words).

What each step checks, parameter by parameter, is in the tables under Alternative 3 in [narrower-tokens.md](narrower-tokens.md#what-a-full-vm-needs). The admin token holds every privilege those tables name except `Sys.Modify`, which the `startup` setting needs, so `startup` and the settings only root can set stay the owner's. That is read from the measured list in [admin-token.md](admin-token.md#what-the-token-holds), not measured on a create call.

The owner can mark a VM that must never go with the protection flag, which the `qm` schema in `QemuServer.pm` describes as "Sets the protection flag of the VM. This will disable the remove VM and remove disk operations." A token can clear the flag again, because `protection` is checked as `VM.Config.Options`, which both the admin token and `PVEVMAdmin` hold, so the flag stops a mistake, not a misused token. On the host shell, as root:

```bash
qm set <vm-id> --protection 1
```

Pick a free VM ID:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- "$PVE_API_URL/cluster/nextid"
```

Upload an ISO from the agent's machine. The field names are those the web page sends from `UploadToStorage.js`:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- -X POST -F 'content=iso' -F 'filename=@<local-file>.iso' "$PVE_API_URL/nodes/<node>/storage/<iso-storage>/upload"
```

Or download one by URL, with the checksum the vendor publishes, so a changed file is refused:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- -X POST --data-urlencode 'content=iso' --data-urlencode 'filename=<file>.iso' --data-urlencode 'url=<https-url>' --data-urlencode 'checksum=<sha256>' --data-urlencode 'checksum-algorithm=sha256' "$PVE_API_URL/nodes/<node>/storage/<iso-storage>/download-url"
```

Create the VM, with a new disk of `<size-in-GiB>` on `<storage>`, the ISO in a CD drive and one network device:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- -X POST --data-urlencode 'vmid=<vm-id>' --data-urlencode 'name=<vm-name>' --data-urlencode 'memory=<mib>' --data-urlencode 'cores=<cores>' --data-urlencode 'ostype=l26' --data-urlencode 'agent=1' --data-urlencode 'scsihw=virtio-scsi-single' --data-urlencode 'scsi0=<storage>:<size-in-GiB>' --data-urlencode 'ide2=<iso-storage>:iso/<file>.iso,media=cdrom' --data-urlencode 'net0=virtio,bridge=<bridge>' "$PVE_API_URL/nodes/<node>/qemu"
```

Delete a VM, only after the yes for that VM. The VM has to be stopped first, because `destroy_vm` refuses with "VM <vm-id> is running - destroy failed":

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- -X DELETE "$PVE_API_URL/nodes/<node>/qemu/<vm-id>"
```

Each change call returns a task ID under `data`. Follow it as "Calls that change something" says. With Alternative 3, each change call runs inside the `agent-change.env` subshell described there, and the VM ID is picked with the read-only token.

---

### pvesh is for the host, not the agent

`pvesh` calls the same API from the host shell. The manual page says "Only 'root' is allowed to do that." It is the owner's tool, for example `pvesh get /nodes`, never the agent's route in.
