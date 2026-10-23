# API Access for an Agent

Read this before giving an agent access to a Proxmox VE host, or before calling its API. The main way is an admin token for a user of its own, described first. Narrower tokens follow at the end of the file as alternatives, for an owner who chose one of them instead. The rules live in [SKILL.md](../SKILL.md), and rule 4 there holds for every token: the agent asks the owner before every change, and rule 9 before every delete. The admin token commands and its permission list were measured on Proxmox VE 8.3.2, as that section says. Every other command here is UNVERIFIED. The API paths and the privilege each one needs were checked against the API schema of the API viewer on 2026-10-23.

Sources, fetched on 2026-10-23: the user management chapter https://pve.proxmox.com/pve-docs/chapter-pveum.html and its source `pveum.adoc`, the manual page https://pve.proxmox.com/pve-docs/pveum.1.html at version 9.2.13, the API viewer https://pve.proxmox.com/pve-docs/api-viewer/, the certificate section of https://pve.proxmox.com/pve-docs/chapter-sysadmin.html, `src/PVE/AccessControl.pm` in `pve-access-control` at commit `dff26b45` of 2026-09-17, `src/PVE/API2/Qemu.pm` in `qemu-server` at commit `71ea0ac7` of 2026-10-20, `www/manager6/dc/Config.js`, `www/manager6/dc/ACLView.js` and `www/manager6/dc/TokenEdit.js` in `pve-manager` at commit `f643ce4b`, and the curl manual https://curl.se/docs/manpage.html. The API viewer's schema file was last modified on 2026-09-24, the same day as the 9.2.13 manual page.

---

### What a token is

The user management chapter, section "API Tokens": "API tokens allow stateless access to most parts of the REST API from another system, software, or API client." There are two kinds: "Separated privileges: The token needs to be given explicit access with ACLs. Its effective permissions are calculated by intersecting user and token permissions. This is the default for newly created tokens." And: "Full privileges: The token's permissions are identical to that of the associated user." The admin token below is of the second kind, and the alternatives at the end are of the first.

The chapter also says: "The token value is only displayed/returned once when the token is generated. It cannot be retrieved again over the API at a later time!"

---

### Proxmox VE 8 and 9

Every `pveum` command and every API call in this file works on Proxmox VE 8.x and 9.x, except that an early 8.x host lacks `Sys.AccessNetwork`, which the download role of the admin token and of Alternative 3 uses, as "Proxmox VE 8 and 9 for this alternative" under Alternative 3 says. What differs between the two is what the built-in roles contain, and one extra check on rollback. Checked on 2026-10-23 against the 8.x branches, `stable-bookworm` of `pve-access-control` at commit `0f258e71`, of `qemu-server` at `5ccd363e` and of `pve-docs` at `fa0b4f6b`, and `stable-8` of `pve-manager` at `5aee9c09`, beside the 9.x sources named above.

| Item | 8.x | 9.x |
|---|---|---|
| `pveum acl modify` options | `--users`, `--tokens`, `--roles`, `--propagate` | the same |
| The short form `-user`, `-token`, `-role` | works, and `-user`, `-role`, `-comment`, `-privsep` and `-privs` were measured on 8.3.2 | works, inferred from the source, not measured |
| `pveum user token add` with `--privsep` and `--expire` | yes | yes |
| `pveum user token permissions` | yes | yes |
| `VM.Monitor` in `PVEVMAdmin` | yes | no, the privilege is gone |
| `VM.GuestAgent.*` and `VM.Replicate` | do not exist | in `PVEVMAdmin`, and `VM.GuestAgent.Audit` in `PVEAuditor` |
| `Datastore.AllocateSpace` on the disk's storage for a resize | checked | checked |
| `VM.PowerMgmt` for a rollback with `start` set | not checked | checked |
| Web page names below | the same | the same |

The `pveum` manual page writes the ACL options as `--users`, `--tokens` and `--roles`, under `pveum acl modify <path> --roles <string> [OPTIONS]`, because those are the parameter names of `PUT /access/acl` in `ACL.pm`, the same on both branches. The chapter's own examples write `-user`, `-token` and `-role`, and both work because the command line parser in `JSONSchema.pm` sets `prefix_pattern=(--|-)` on both branches and leaves Getopt::Long's abbreviation of option names on, so `-user` is read as `--users`. The admin token commands use the short form exactly as the owner ran them on 8.3.2, and the alternatives use the manual page's form.

---

### The admin token

This is the main way to give an agent access. The owner does this, on the host or in the web page. The agent only receives the result in the env file below.

The token belongs to a user of its own and holds `PVEAdmin` on `/`. It can create, change and delete VMs and storage content, manage storages and SDN, create users and groups but not grant permissions, and download ISO files. The agent still asks the owner before every change and before every delete, one VM per yes, as rules 4 and 9 in [SKILL.md](../SKILL.md) say. The token makes a change possible. It is not permission to make one.

The token is made with `-privsep 0`, so its permissions are the user's own. On a dedicated user that holds nothing but this token, that gives the same result as privilege separation with the same ACLs given to the token.

On the host shell, as root, in the short form the owner ran on Proxmox VE 8.3.2 on 2026-10-23. The user, with no password, because the token is the only way in:

```bash
pveum user add <user>@pve -comment "AI agent"
```

The token. Copy the secret it prints into the env file, because it is shown only this once:

```bash
pveum user token add <user>@pve <token-id> -privsep 0
```

`PVEAdmin` on the whole tree:

```bash
pveum acl modify / -user <user>@pve -role PVEAdmin
```

A custom role for downloading an ISO by URL:

```bash
pveum role add AgentDownload -privs Sys.AccessNetwork
```

That role on each node the agent should download on, with `PVEAdmin` named again beside it:

```bash
pveum acl modify /nodes/<node> -user <user>@pve -role PVEAdmin,AgentDownload
```

Why the second role: `PVEAdmin` does not hold `Sys.AccessNetwork`, and the download call needs it on `/nodes/<node>`, see "What a full VM needs" under Alternative 3. No built-in role but `Administrator` carries it, as "Why a custom role and not PVEDatastoreAdmin" there explains. And a role on a deeper path replaces the inherited one, see "A deeper permission replaces the one above it" there, so an ACL on `/nodes/<node>` with `AgentDownload` alone would take `PVEAdmin` away on that node. That is why the node ACL names `PVEAdmin` again. On 8.x, `Sys.AccessNetwork` exists only from `libpve-access-control` 8.1.2, and an older host refuses the role, see "Proxmox VE 8 and 9 for this alternative" under Alternative 3.

In the web page, under Datacenter, Permissions, the names from `Config.js`, `TokenEdit.js`, `RoleEdit.js` and `ACLView.js`:

1. Users, Add: User name `<user>`, Realm `pve`, Password left empty.
2. API Tokens, Add: User `<user>@pve`, Token ID `<token-id>`, Privilege Separation not ticked. Copy the secret from the Token Secret window, which says "Please record the API token secret - it will only be displayed now".
3. Roles, Create: Name `AgentDownload`, Privileges `Sys.AccessNetwork`.
4. Permissions, Add, User Permission: Path `/` with Role `PVEAdmin`, then Path `/nodes/<node>` twice, once with Role `PVEAdmin` and once with Role `AgentDownload`. Propagate ticked each time.

#### What the token holds

VERIFIED on Proxmox VE 8.3.2 on 2026-10-23, through this token with `GET /access/permissions`:

| Path | Effective privileges |
|---|---|
| `/` | `Datastore.Allocate`, `Datastore.AllocateSpace`, `Datastore.AllocateTemplate`, `Datastore.Audit`, `Group.Allocate`, `Mapping.Audit`, `Mapping.Use`, `Pool.Allocate`, `Pool.Audit`, `Realm.AllocateUser`, `SDN.Allocate`, `SDN.Audit`, `SDN.Use`, `Sys.Audit`, `Sys.Console`, `Sys.Syslog`, `User.Modify`, `VM.Allocate`, `VM.Audit`, `VM.Backup`, `VM.Clone`, `VM.Config.CDROM`, `VM.Config.CPU`, `VM.Config.Cloudinit`, `VM.Config.Disk`, `VM.Config.HWType`, `VM.Config.Memory`, `VM.Config.Network`, `VM.Config.Options`, `VM.Console`, `VM.Migrate`, `VM.Monitor`, `VM.PowerMgmt`, `VM.Snapshot`, `VM.Snapshot.Rollback`, 35 in all |
| `/nodes/<node>` | the same 35 and `Sys.AccessNetwork` |

Not held: `Sys.Modify`, `Sys.PowerMgmt`, `Permissions.Modify` and `Realm.Allocate`. So the token cannot change the host's system settings, cannot reboot or shut down the host, and cannot change permissions. The chapter describes the role the same way: "PVEAdmin: can do most tasks, but has no rights to modify system settings (Sys.PowerMgmt, Sys.Modify, Realm.Allocate) or permissions (Permissions.Modify)".

`create_roles` in `AccessControl.pm` builds `PVEAdmin` from the admin, user and audit groups of every privilege category, the same groups `PVEVMAdmin` takes for VMs. So on 9.x the VM privileges in the role follow the table under "Proxmox VE 8 and 9" above: no `VM.Monitor`, and `VM.GuestAgent.*` and `VM.Replicate` in its place. That is read from the source, not measured.

Check what the token holds before handing it over, on the host:

```bash
pveum user token permissions <user>@pve <token-id>
```

Or from the agent's machine, once the env file below is filled and loaded:

```bash
printf 'Authorization: PVEAPIToken=%s=%s\n' "$PVE_TOKEN_ID" "$PVE_TOKEN_SECRET" | curl -s -k --pinnedpubkey "$PVE_PIN" -H @- "$PVE_API_URL/access/permissions"
```

#### Taking it away

Remove the token, then the user, then the custom role. `pveum user token remove` is, in the manual page's words, "An alias for pveum user token delete":

```bash
pveum user token remove <user>@pve <token-id>
```

```bash
pveum user delete <user>@pve
```

```bash
pveum role delete AgentDownload
```

#### Switching from a narrower alternative

An owner who set up one of the alternatives below first removes every ACL it gave the user, path by path, naming the role each one gave, and then deletes every custom role nothing else uses. Remove the deeper ACLs as well, such as those of Alternative 3 on a bridge, an ISO storage or a node, because a deeper permission replaces the inherited one and a leftover one would take `PVEAdmin` away on that path. List what is there:

```bash
pveum acl list
```

For each ACL of the user:

```bash
pveum acl delete <path> -user <user>@pve -role <role>
```

For each custom role nothing else uses, such as `AgentISO` from Alternative 3:

```bash
pveum role delete <custom-role>
```

The owner did exactly this on 8.3.2, coming from `PVEAuditor` on `/`, `PVEDatastoreUser` on `/storage` and a custom VM role on `/vms`. An alternative's token was made with privilege separation. Remove it with `pveum user token remove` as above and add the new one with `-privsep 0`, then give the user the ACLs above. Skip `pveum role add AgentDownload` when Alternative 3 already made that role.

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

`PVE_PIN` and `PVE_CA_FILE` are alternatives, see the next section. With Alternative 2 or 3, the owner fills a second file beside it, `agent-change.env` in the same folder, with the same five names and the change token in `PVE_TOKEN_ID` and `PVE_TOKEN_SECRET`. Restrict both files the same way. On Linux and macOS:

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

The calls an agent needs to build a whole VM itself: pick a VM ID, put an ISO on a storage, create the VM with a disk, a CD drive with the ISO and a network device on a bridge, start it, and delete a VM nobody needs any more. The admin token can make every one of them. Each step needs its own yes from the owner, and a delete needs a yes for that one VM after the agent named it by ID and name, its node, and its newest backup with the date, as rule 9 in [SKILL.md](../SKILL.md) says. A deleted VM has no undo except restoring a backup, see "The risk, in plain words" under Alternative 3.

What each step checks, parameter by parameter, is in the tables under Alternative 3. The admin token holds every privilege those tables name except `Sys.Modify`, which the `startup` setting needs, so `startup` and the settings only root can set stay the owner's. That is read from the measured list above, not measured on a create call.

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

---

### Alternatives: narrower tokens

Three narrower tokens, for an owner who chose one of them instead of the admin token. Alternative 1 can only read. Alternative 2 is a second token beside it that can also resize disks, take snapshots and start or stop VMs. Alternative 3 adds to that second token what it needs to create and delete VMs. Rule 4 and rule 9 in [SKILL.md](../SKILL.md) hold for each of them the same way.

---

### Alternative 1: a read-only token

The owner does this, on the host or in the web page. The agent only receives the result in the env file described above.

The role for reading is `PVEAuditor`, which the chapter lists as "has read only access". In `AccessControl.pm` that role is built from every privilege of the audit group, which includes `VM.Audit`, `Datastore.Audit` and `Sys.Audit`.

In the web page the panel is Datacenter, Permissions, API Tokens, which `www/manager6/dc/Config.js` lists under the permissions group. Create the token there for a dedicated user, leave Privilege Separation ticked, and set an expiry date. Then add a permission under Datacenter, Permissions for the token, not the user, with the path `/` and the role `PVEAuditor`.

The same on the host shell, as root. The user below gets no password, so it is meant for tokens only. That it then cannot log in to the web page is inferred from the realm design, not measured:

```bash
pveum user add <user>@pve --comment "read only agent access"
```

```bash
pveum acl modify / --users <user>@pve --roles PVEAuditor
```

```bash
pveum user token add <user>@pve <token-id> --privsep 1 --expire <unix-time> --comment "agent, read only"
```

```bash
pveum acl modify / --tokens '<user>@pve!<token-id>' --roles PVEAuditor
```

The user needs the role as well, because a separated token gets the intersection of both. The chapter's own example, under "Limited API Token for Monitoring", does the same pair of `acl modify` calls. Check what the token can do:

```bash
pveum user token permissions <user>@pve <token-id>
```

The manual page says `--expire` is "seconds since epoch" and "0 means no expiration date". Use a date. Revoke a token without touching the user:

```bash
pveum user token delete <user>@pve <token-id>
```

---

### Alternative 2: a token that can also change VMs

For an owner who chose this, for an agent that should resize disks, take snapshots and start or stop VMs itself. It builds on Alternative 1 and does not replace it. The agent keeps reading with the read-only token and loads this one only for a change the owner approved, one change per yes, as rule 4 in [SKILL.md](../SKILL.md) says. The token makes a change possible. It is not permission to make one.

Give it a user of its own, `<change-user>@pve`, rather than a second token on the read-only user. A separated token gets the intersection of its user's permissions and its own, so the user's permissions are the most any of its tokens can ever reach. Keeping the read-only user at `PVEAuditor` keeps that ceiling read-only, whatever happens to a token ACL later.

This alternative uses privilege separation. The manual page describes `--privsep` as "Restrict API token privileges with separate ACLs (default), or give full privileges of corresponding user." With it on, the token gets the intersection of its own ACLs and its user's, so the user and the token both get the three roles below.

Three roles, each on the path it is needed on, read from `create_roles` in `AccessControl.pm`, which builds every `PVE` role from the privilege groups listed above it:

| Role | Path | Privileges in the role | Why |
|---|---|---|---|
| `PVEAuditor` | `/` | `VM.Audit`, `VM.GuestAgent.Audit`, `Sys.Audit`, `Datastore.Audit`, `SDN.Audit`, `Pool.Audit`, `Mapping.Audit` | the same reads as Alternative 1, including task status, thin pools and backup jobs |
| `PVEVMAdmin` | `/vms` | `VM.Config.Disk`, `VM.Config.CPU`, `VM.Config.Memory`, `VM.Config.Network`, `VM.Config.HWType`, `VM.Config.Options`, `VM.Config.CDROM`, `VM.Config.Cloudinit`, `VM.Allocate`, `VM.Clone`, `VM.Migrate`, `VM.Replicate`, `VM.Snapshot`, `VM.Snapshot.Rollback`, `VM.PowerMgmt`, `VM.Backup`, `VM.Console`, `VM.GuestAgent.Unrestricted`, `VM.GuestAgent.FileRead`, `VM.GuestAgent.FileWrite`, `VM.GuestAgent.FileSystemMgmt`, `VM.Audit`, `VM.GuestAgent.Audit` | resize, snapshot, start, stop and backup on every VM |
| `PVEDatastoreUser` | `/storage` | `Datastore.AllocateSpace`, `Datastore.Audit` | the space a resize or a backup takes on a storage |

The table is the 9.x content. On 8.x, `PVEVMAdmin` has `VM.Monitor`, which the 8.x chapter describes as "access to VM monitor (kvm)", and has none of `VM.GuestAgent.*` or `VM.Replicate`. `PVEAuditor` there has no `VM.GuestAgent.Audit`.

VERIFIED on Proxmox VE 8.3.2 with `GET /access/permissions`, for a user given exactly these three ACLs and read through one of its tokens with privilege separation off, so the list is the user's own:

| Path | Effective privileges |
|---|---|
| `/`, `/nodes`, `/pool`, `/sdn`, `/access` | `Datastore.Audit`, `Mapping.Audit`, `Pool.Audit`, `SDN.Audit`, `Sys.Audit`, `VM.Audit` |
| `/storage` | `Datastore.AllocateSpace`, `Datastore.Audit` |
| `/vms` | `VM.Allocate`, `VM.Audit`, `VM.Backup`, `VM.Clone`, `VM.Config.CDROM`, `VM.Config.CPU`, `VM.Config.Cloudinit`, `VM.Config.Disk`, `VM.Config.HWType`, `VM.Config.Memory`, `VM.Config.Network`, `VM.Config.Options`, `VM.Console`, `VM.Migrate`, `VM.Monitor`, `VM.PowerMgmt`, `VM.Snapshot`, `VM.Snapshot.Rollback` |

That matches the 8.x privilege groups in `AccessControl.pm` on `stable-bookworm` exactly. That token had privilege separation off, which this section does not do. With privilege separation on, as below, the token needs the same three ACLs of its own, so check the token itself with `pveum user token permissions`.

The chapter describes them as "PVEAuditor: has read only access", "PVEVMAdmin: fully administer VMs" and "PVEDatastoreUser: allocate backup space and view storage". An ACL propagates down the tree unless told otherwise: the manual page gives `--propagate <boolean> (default = 1)`, so `/vms` covers every VM and `/storage` every storage, including ones added later.

`PVEVMAdmin` holds more than the three jobs need, and the agent never uses the rest unless the owner asks for that exact action:

1. `VM.Allocate` creates and destroys VMs. The API schema gives `DELETE /nodes/{node}/qemu/{vmid}`, "Destroy the VM and all used/owned volumes", the check `VM.Allocate` on `/vms/{vmid}`.
2. `VM.Config.*` changes any part of a VM's configuration, CPU, memory, network and options included.
3. `VM.GuestAgent.Unrestricted` on 9.x, which the chapter describes as "issue arbitrary QEMU guest agent commands", runs commands inside a guest that has the agent installed. `VM.Monitor` on 8.x gives access to the QEMU monitor of every VM.
4. `VM.Snapshot.Rollback` throws away everything a guest wrote since the snapshot, and `VM.Migrate`, `VM.Clone` and `VM.Console` do what their names say.

What each change needs, from the API schema and from the checks in `Qemu.pm`:

| Change | Call | Privilege |
|---|---|---|
| Grow a disk | `PUT /nodes/<node>/qemu/<vm-id>/resize` | `VM.Config.Disk` on `/vms/<vm-id>`, from the schema, and `Datastore.AllocateSpace` on `/storage/<storage>` of the disk's own storage, from `resize_vm` in `Qemu.pm` |
| Take or delete a snapshot | `POST /nodes/<node>/qemu/<vm-id>/snapshot`, `DELETE /nodes/<node>/qemu/<vm-id>/snapshot/<snapshot-name>` | `VM.Snapshot` |
| Roll back to a snapshot | `POST /nodes/<node>/qemu/<vm-id>/snapshot/<snapshot-name>/rollback` | `VM.Snapshot` or `VM.Snapshot.Rollback`, and on 9.x `VM.PowerMgmt` as well when `start` is set |
| Start, shut down, stop, reboot | `POST /nodes/<node>/qemu/<vm-id>/status/start`, and `shutdown`, `stop`, `reboot` in its place | `VM.PowerMgmt` |
| Back up a VM now | `POST /nodes/<node>/vzdump` | `VM.Backup` on the VM and `Datastore.AllocateSpace` on the backup storage |
| Follow the task a change started | `GET /nodes/<node>/tasks/<upid>/status` | none for the token that started it, `Sys.Audit` on `/nodes/<node>` for any other |

The resize check, word for word from `resize_vm`:

```perl
$rpcenv->check($authuser, "/storage/$storeid", ['Datastore.AllocateSpace']);
```

The schema lists only `VM.Config.Disk` for that call, so a token without `PVEDatastoreUser` on the disk's storage passes the first check and is then refused. The schema's text for `vzdump` adds limits that `PVEDatastoreUser` does not lift: "The 'prune-backups' setting requires 'Datastore.Allocate' on the backup storage", and "The 'stop' parameter requires 'Sys.Modify' on '/nodes/{node}'". A backup that needs either is the owner's job, see [snapshots-and-backups.md](snapshots-and-backups.md).

On the host shell, as root. The user, then its three roles, then the token and the same three roles for the token, because a separated token gets the intersection of both:

```bash
pveum user add <change-user>@pve --comment "agent, VM changes"
```

```bash
pveum acl modify / --users <change-user>@pve --roles PVEAuditor
```

```bash
pveum acl modify /vms --users <change-user>@pve --roles PVEVMAdmin
```

```bash
pveum acl modify /storage --users <change-user>@pve --roles PVEDatastoreUser
```

```bash
pveum user token add <change-user>@pve <token-id> --privsep 1 --expire <unix-time> --comment "agent, VM changes"
```

```bash
pveum acl modify / --tokens '<change-user>@pve!<token-id>' --roles PVEAuditor
```

```bash
pveum acl modify /vms --tokens '<change-user>@pve!<token-id>' --roles PVEVMAdmin
```

```bash
pveum acl modify /storage --tokens '<change-user>@pve!<token-id>' --roles PVEDatastoreUser
```

Check what the token can do before handing it over, and look for `VM.Config.Disk` under `/vms` and `Datastore.AllocateSpace` under `/storage`:

```bash
pveum user token permissions <change-user>@pve <token-id>
```

In the web page, under Datacenter, Permissions, the names from `Config.js`, `ACLView.js` and `TokenEdit.js`:

1. Users, Add: User name `<change-user>`, Realm `pve`, Password left empty, because the token is the only way in.
2. API Tokens, Add: User `<change-user>@pve`, a Token ID, Privilege Separation ticked, an expiry date. Copy the secret from the Token Secret window, which says "Please record the API token secret - it will only be displayed now".
3. Permissions, Add, User Permission, three times: Path `/` with Role `PVEAuditor`, Path `/vms` with Role `PVEVMAdmin`, Path `/storage` with Role `PVEDatastoreUser`, Propagate ticked each time.
4. Permissions, Add, API Token Permission, the same three times for the token.

To take the change access away again, delete the token, which leaves Alternative 1 untouched:

```bash
pveum user token delete <change-user>@pve <token-id>
```

---

### Alternative 3: a token that can also create and delete VMs

For an owner who chose this, for an agent that should build a whole VM itself: pick a VM ID, put an ISO on a storage, create the VM with a disk, a CD drive with the ISO and a network device on a bridge, start it, and delete a VM nobody needs any more. Alternative 3 builds on Alternative 2 and does not replace it. It uses the same `<change-user>@pve`, the same token and the same `agent-change.env`, so do Alternative 2 first and then add the lines below. Alternative 1 stays as it is, and the agent keeps reading with the read-only token.

Alternative 2's token can already delete any VM, and can already create a VM without a network device, because `PVEVMAdmin` on `/vms` holds `VM.Allocate`. What Alternative 3 adds is a network device on a bridge, and an ISO the agent uploads or downloads itself.

Sources, read on 2026-10-23. For 9.x the `master` branches: `qemu-server` at `71ea0ac7` of 2026-10-20, `pve-access-control` at `dff26b45` of 2026-09-17, `pve-storage` at `75b36a49` of 2026-10-09, `pve-manager` at `f643ce4b` of 2026-10-19 and `pve-guest-common` at `a9e15736` of 2026-07-06. For 8.x: `stable-bookworm` of `qemu-server` at `5ccd363e` of 2026-08-17 and of `pve-access-control` at `0f258e71` of 2026-04-21, `stable-8` of `pve-storage` at `9aab8f6f` and of `pve-manager` at `5aee9c09`, both of 2026-08-24, and `pve-guest-common` at `58ad183`, the 5.2.2 release of 2025-04-08, the last one before 6.0 for 9.x, because that repository has no 8.x branch. Also the API viewer schema, last modified on 2026-09-24, and `pveum.adoc` on both `pve-docs` branches. Line numbers below are 9.x first, then 8.x.

#### The risk, in plain words

1. This token can delete every VM on every node, VMs added later included, because the ACL on `/vms` propagates. The schema describes `DELETE /nodes/{node}/qemu/{vmid}` as "Destroy the VM and all used/owned volumes". `destroy_vm` in `QemuServer.pm`, line 1882 and 2267, removes every disk "owned by this VM (referenced in the config)" and the saved state of its snapshots. A `vzdump` backup on a backup storage is not part of the VM's configuration and stays. So a deleted VM has no undo except restoring such a backup. That a backup survives the delete is read from the source, not measured.
2. It can create VMs until a storage is full. A full thin pool returns write errors to every guest on it, see [storage.md](storage.md).
3. With the optional download role, the host fetches any URL the agent names, addresses on the owner's own network included. The schema says the download call "allows one to probe the (local!) host network indirectly".

So the agent asks the owner before every change and before every delete, as rules 4 and 9 in [SKILL.md](../SKILL.md) say. Before a delete it names the VM by ID and name, its node, and its newest backup with the date, and then waits for a yes for that one VM. One yes covers one VM. No answer means no delete. The token makes a delete possible. It is not permission to make one.

The protection flag, which stops a delete made by mistake, is under "Create and delete a VM" above.


#### What a full VM needs

| Step | Call | Privilege and path | Granted by |
|---|---|---|---|
| Pick a free VM ID | `GET /cluster/nextid` | none, the schema says `"user": "all"`, `Cluster.pm` line 1018 and 887 | any token |
| See the bridges | `GET /nodes/<node>/network?type=any_bridge` | any user, but a bridge is listed only with `SDN.Audit` or `SDN.Use` on `/sdn/zones/localnetwork/<bridge>`, `Network.pm` line 472 to 482 and 416 to 426 | `PVEAuditor` on `/`, Alternative 1 and Alternative 2 |
| See the ISOs on a storage | `GET /nodes/<node>/storage/<iso-storage>/content?content=iso` | `Datastore.Audit` or `Datastore.AllocateSpace` on `/storage/<iso-storage>` | `PVEDatastoreUser`, Alternative 2 |
| Upload an ISO | `POST /nodes/<node>/storage/<iso-storage>/upload` | `Datastore.AllocateTemplate` on `/storage/<iso-storage>`, `Status.pm` line 524 and 434 | `AgentISO`, new here |
| Download an ISO by URL | `POST /nodes/<node>/storage/<iso-storage>/download-url` | `Datastore.AllocateTemplate` on `/storage/<iso-storage>`, and either `Sys.AccessNetwork` on `/nodes/<node>` or both `Sys.Audit` and `Sys.Modify` on `/`, `Status.pm` line 748 to 755 and 658 to 665 | `AgentISO` and `AgentDownload`, new here, optional |
| Create the VM | `POST /nodes/<node>/qemu` | `VM.Allocate` on `/vms/<vm-id>`, then one check per parameter, see the next table | `PVEVMAdmin`, `PVEDatastoreUser` and `PVESDNUser` |
| Start it | `POST /nodes/<node>/qemu/<vm-id>/status/start` | `VM.PowerMgmt` on `/vms/<vm-id>` | `PVEVMAdmin`, Alternative 2 |
| Delete a VM | `DELETE /nodes/<node>/qemu/<vm-id>` | `VM.Allocate` on `/vms/<vm-id>` | `PVEVMAdmin`, Alternative 2 |

The schema sums up the create call as: "You need 'VM.Allocate' permissions on /vms/{vmid} or on the VM pool /pool/{pool}. ... If you create disks you need 'Datastore.AllocateSpace' on any used storage.If you use a bridge/vlan, you need 'SDN.Use' on any used bridge/vlan." What `create_vm` in `Qemu.pm` checks, parameter by parameter:

| Parameter | Check | Where |
|---|---|---|
| `vmid` | `VM.Allocate` on `/vms/<vm-id>`, or on `/pool/<pool>` when `pool` is set | `Qemu.pm` line 1334 and 1248 |
| a new disk, `scsi0=<storage>:<size-in-GiB>` | `Datastore.AllocateSpace` on `/storage/<storage>` | `check_storage_access`, `Qemu.pm` line 190 and 180 |
| an ISO, `ide2=<iso-storage>:iso/<file>.iso,media=cdrom` | `Datastore.AllocateSpace` or `Datastore.Audit` on `/storage/<iso-storage>`, because `check_volume_access` in `Storage.pm` asks for one of them for `iso` content | `Qemu.pm` line 195 and 185, `Storage.pm` line 632 to 638 and 562 to 568 |
| a network device, `net0=virtio,bridge=<bridge>` | `VM.Config.Network`, and `SDN.Use` on `/sdn/zones/localnetwork/<bridge>`. With a VLAN tag the path is `/sdn/zones/localnetwork/<bridge>/<tag>`, which an ACL on the bridge covers when it propagates. A bridge that is an SDN VNet is checked on `/sdn/zones/<zone>/<vnet>` instead | `check_bridge_access`, `Qemu.pm` line 1397 and 1303, calling `check_vnet_access` in `GuestHelpers.pm`, line 419 and 415 |
| `cores`, `sockets`, `cpu` | `VM.Config.CPU`, and `Mapping.Use` on `/mapping/cpu/<name>` for a custom CPU model | `check_vm_modify_config_perm` and `check_cpu_model_access` |
| `memory`, `balloon` | `VM.Config.Memory` | `check_vm_modify_config_perm` |
| `name`, `ostype`, `onboot`, `agent`, `bios`, `protection` | `VM.Config.Options`, and `Sys.Modify` on `/` for `startup`, which this alternative does not give | `check_vm_modify_config_perm` |
| `scsihw`, `machine`, `vga` | `VM.Config.HWType` | `check_vm_modify_config_perm` |
| `boot` | `VM.Config.Disk` | `check_vm_modify_config_perm` |
| cloud-init settings, `ciuser`, `cipassword`, `sshkeys`, `ipconfig0` | `VM.Config.Cloudinit`. On 9.x `nameserver` and `searchdomain` take that or `VM.Config.Network`, and on 8.x every cloud-init setting takes either one | `check_vm_modify_config_perm` |
| a cloud-init drive, `ide0=<storage>:cloudinit` | nothing beyond `VM.Allocate`, because `check_storage_access` skips a `cloudinit` volume | `Qemu.pm` line 178 to 184 and 168 to 174 |
| `start=1` | `VM.PowerMgmt`, checked before the VM is made on 9.x only | `Qemu.pm` line 1331 |
| `ha-managed=1`, 9.x only | `Sys.Console` on `/`, which this alternative does not give | `Qemu.pm` line 1326 |

The guest agent is the `agent=1` setting above. Talking to it later takes `VM.GuestAgent.Audit` or more on 9.x and `VM.Monitor` on 8.x, all in `PVEVMAdmin`.

Some things no token can set, because the check ends in "only root can set", for example a USB or PCI device passed through by its host ID rather than by a resource mapping, a serial port on a real device, and any setting in none of the lists, which the source comments as "catches args, lock, etc.", `Qemu.pm` line 1059 and 989. A custom cloud-init file in `cicustom` is the owner's job as well: the upload call takes only `iso`, `vztmpl` and `import`, so a snippet cannot be put on a storage through the API, and on 9.x since `qemu-server` 9.2.11 of 2026-10-09 the snippet also needs `Datastore.AllocateSpace` on its storage. Deleting an ISO needs `Datastore.Allocate`, which the schema gives for `DELETE /nodes/{node}/storage/{storage}/content/{volume}` as "You need 'Datastore.Allocate' privilege on the storage", so old ISOs are the owner's to remove.

#### Why a custom role and not PVEDatastoreAdmin

No built-in role holds `Datastore.AllocateTemplate` without `Datastore.Allocate`. `create_roles` in `AccessControl.pm`, line 1175 and 1171, builds `PVEDatastoreAdmin` from the whole admin group of the storage privileges, and that group is `'Datastore.Allocate', 'Datastore.AllocateTemplate'` on one line, 1107 and 1103. `PVEDatastoreUser` stops at `Datastore.AllocateSpace`, and apart from `PVEDatastoreAdmin` only `PVEAdmin` and `Administrator` carry the admin group.

`Datastore.Allocate` is much more than an ISO. The chapter describes it as "create/modify/remove a datastore and delete volumes". The schema asks for it on `/storage` to create, change or remove a storage configuration, `POST /storage`, `PUT /storage/{storage}` and `DELETE /storage/{storage}`, which is `Config.pm` line 205, 305 and 422 on 9.x and 205, 305 and 410 on 8.x. And `check_volume_access` in `Storage.pm` returns at once for anyone holding it, line 630 and 560, so that token could use any disk or backup of any VM on that storage. A custom role with `Datastore.AllocateTemplate` alone gives the upload and the download and nothing else. The chapter says "Roles starting with `PVE` are always builtin, custom roles are not allowed use this reserved prefix."

The same holds for the download. `Sys.AccessNetwork` sits in the root group of the system privileges, `AccessControl.pm` line 1094 and 1090, commented "for, e.g., downloading ISOs from any URL", and no role but `Administrator` carries that group. The other way the download call accepts, `Sys.Modify` on `/`, is what the chapter lists as "create/modify/remove node network parameters" and warns about. On `/nodes/<node>`, `Sys.AccessNetwork` also opens `query-url-metadata` and `query-oci-repo-tags` on that node, and on 9.x `oci-registry-pull` together with `Datastore.AllocateTemplate`. Each of those fetches something from a network address and changes nothing else. The checks that ask for it in the notification calls are on `/`, which this ACL does not reach.

#### A deeper permission replaces the one above it

The chapter, section "Inheritance": "Permissions on deeper levels replace those inherited from an upper level." In `roles` in `AccessControl.pm` that is `$roles = $new; # overwrite previous settings`, line 1847 and 1837. So an ACL on `/storage/<iso-storage>` with only `AgentISO` would take `PVEDatastoreUser` away on that storage, and an ACL on `/nodes/<node>` with only `AgentDownload` would take `PVEAuditor` away on that node. That is why both commands below name the inherited role again beside the new one. `PVESDNUser` holds `SDN.Audit` as well as `SDN.Use`, the `user` and `audit` groups of the SDN privileges as `create_roles` builds it, so the bridge needs nothing beside it.

#### Proxmox VE 8 and 9 for this alternative

| Item | 8.x | 9.x |
|---|---|---|
| `PVESDNUser` with `SDN.Use` and `SDN.Audit` | yes, `AccessControl.pm` line 1118 | yes, line 1122 |
| `SDN.Use` checked on the bridge when a VM is created | yes, since `qemu-server` commit `9cfd06d9` of 2023-06-07 | yes |
| `Datastore.AllocateTemplate` for upload and download | yes | yes |
| `Sys.AccessNetwork` | only from `libpve-access-control` 8.1.2 of 2024-02-28, and the download call accepts it only from `libpve-storage-perl` 8.1.0 of 2024-03-06. An older host refuses the role with "invalid privilege" | yes |
| `VM.PowerMgmt` checked before the VM is made with `start=1` | no | yes, since commit `5086f472` of 2026-04-30 |
| `Datastore.AllocateSpace` on the snippet storage for `cicustom` | not checked | yes, since `qemu-server` 9.2.11 |
| `ha-managed` when creating | not there | needs `Sys.Console` on `/` |

On an 8.x host the owner reads the two package versions before choosing the download role:

```bash
pveversion -v
```

#### The commands

On the host shell, as root, after Alternative 2. One custom role for the ISO storage:

```bash
pveum role add AgentISO --privs Datastore.AllocateTemplate
```

The bridge, for the user and then for the token. Use one bridge, not `/sdn/zones/localnetwork` as a whole, unless the owner wants the agent on every bridge of the host:

```bash
pveum acl modify /sdn/zones/localnetwork/<bridge> --users <change-user>@pve --roles PVESDNUser
```

```bash
pveum acl modify /sdn/zones/localnetwork/<bridge> --tokens '<change-user>@pve!<token-id>' --roles PVESDNUser
```

The ISO storage, usually `local`, again with `PVEDatastoreUser` beside the new role, for the user and then for the token. `--roles` takes a list, which `ACL.pm` splits on commas on both branches:

```bash
pveum acl modify /storage/<iso-storage> --users <change-user>@pve --roles PVEDatastoreUser,AgentISO
```

```bash
pveum acl modify /storage/<iso-storage> --tokens '<change-user>@pve!<token-id>' --roles PVEDatastoreUser,AgentISO
```

Only if the owner wants the agent to download ISOs by URL rather than upload them, a second custom role on each node it should download on, again with `PVEAuditor` beside it:

```bash
pveum role add AgentDownload --privs Sys.AccessNetwork
```

```bash
pveum acl modify /nodes/<node> --users <change-user>@pve --roles PVEAuditor,AgentDownload
```

```bash
pveum acl modify /nodes/<node> --tokens '<change-user>@pve!<token-id>' --roles PVEAuditor,AgentDownload
```

Check the token before handing it over, and look for `SDN.Use` under `/sdn/zones/localnetwork/<bridge>`, `Datastore.AllocateTemplate` under `/storage/<iso-storage>`, and `Sys.AccessNetwork` under `/nodes/<node>` if the download role was given:

```bash
pveum user token permissions <change-user>@pve <token-id>
```

In the web page, under Datacenter, Permissions, the names from `Config.js`, `RoleEdit.js` and `ACLView.js`, the same on `master` and `stable-8`:

1. Roles, Create: Name `AgentISO`, Privileges `Datastore.AllocateTemplate`. For the download, a second one, Name `AgentDownload`, Privileges `Sys.AccessNetwork`.
2. Permissions, Add, User Permission: Path `/sdn/zones/localnetwork/<bridge>` with Role `PVESDNUser`, then Path `/storage/<iso-storage>` twice, once with Role `PVEDatastoreUser` and once with Role `AgentISO`, and for the download Path `/nodes/<node>` twice, with `PVEAuditor` and with `AgentDownload`. Propagate ticked each time. The Path field lists the paths it knows and is a combo box that `PermPathSelector.js` does not limit to that list, so a typed path should be taken. That is inferred from the source, not measured.
3. Permissions, Add, API Token Permission, the same entries for the token.

To step back to Alternative 2, remove the new roles from the token and the user. For the token:

```bash
pveum acl delete /sdn/zones/localnetwork/<bridge> --tokens '<change-user>@pve!<token-id>' --roles PVESDNUser
```

```bash
pveum acl delete /storage/<iso-storage> --tokens '<change-user>@pve!<token-id>' --roles AgentISO
```

The same two with `--users <change-user>@pve` in place of `--tokens`, and the same for `/nodes/<node>` with `--roles AgentDownload` if it was given. To take all change access away, delete the token as Alternative 2 says.

#### The calls

The calls are under "Create and delete a VM" above. With this alternative, pick the VM ID with the read-only token, and run every change call inside the `agent-change.env` subshell that "Calls that change something" describes, only after the owner said yes to that one step.
