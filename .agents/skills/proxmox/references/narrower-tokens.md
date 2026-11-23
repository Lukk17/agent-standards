# Narrower Tokens

Contents:

- [Alternative 1: a read-only token](#alternative-1-a-read-only-token)
- [Alternative 2: a token that can also change VMs](#alternative-2-a-token-that-can-also-change-vms)
- [Alternative 3: a token that can also create and delete VMs](#alternative-3-a-token-that-can-also-create-and-delete-vms)
- [The risk, in plain words](#the-risk-in-plain-words)
- [What a full VM needs](#what-a-full-vm-needs)
- [Why a custom role and not PVEDatastoreAdmin](#why-a-custom-role-and-not-pvedatastoreadmin)
- [A deeper permission replaces the one above it](#a-deeper-permission-replaces-the-one-above-it)
- [Proxmox VE 8 and 9 for this alternative](#proxmox-ve-8-and-9-for-this-alternative)
- [The commands](#the-commands)
- [The calls](#the-calls)

Three narrower tokens, for an owner who chose one of them instead of the admin token in [admin-token.md](admin-token.md). Alternative 1 can only read. Alternative 2 is a second token beside it that can also resize disks, take snapshots and start or stop VMs. Alternative 3 adds to that second token what it needs to create and delete VMs. Rule 4 and rule 9 in [SKILL.md](../SKILL.md) hold for each of them the same way. What a token is, and what differs between Proxmox VE 8 and 9, is in [admin-token.md](admin-token.md). Every command here is UNVERIFIED, except the permission list marked VERIFIED under Alternative 2. The API paths and the privilege each one needs were checked against the API schema of the API viewer.

Sources: the user management chapter https://pve.proxmox.com/pve-docs/chapter-pveum.html and its source `pveum.adoc`, the manual page https://pve.proxmox.com/pve-docs/pveum.1.html, the API viewer https://pve.proxmox.com/pve-docs/api-viewer/, `src/PVE/AccessControl.pm` in `pve-access-control`, `src/PVE/API2/Qemu.pm` in `qemu-server`, and `www/manager6/dc/Config.js`, `www/manager6/dc/ACLView.js` and `www/manager6/dc/TokenEdit.js` in `pve-manager`.

---

### Alternative 1: a read-only token

The owner does this, on the host or in the web page. The agent only receives the result in the env file that [api-calls.md](api-calls.md#the-env-file) describes.

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

VERIFIED on Proxmox VE 8 with `GET /access/permissions`, for a user given exactly these three ACLs and read through one of its tokens with privilege separation off, so the list is the user's own:

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

Sources. For 9.x the `master` branches of `qemu-server`, `pve-access-control`, `pve-storage`, `pve-manager` and `pve-guest-common`. For 8.x the `stable-bookworm` branches of `qemu-server` and `pve-access-control`, the `stable-8` branches of `pve-storage` and `pve-manager`, and the last 5.x release of `pve-guest-common`, because that repository has no 8.x branch. Also the API viewer schema, and `pveum.adoc` on both `pve-docs` branches. Where a file is named below, the 9.x and the 8.x copy agree unless the text says otherwise.

#### The risk, in plain words

1. This token can delete every VM on every node, VMs added later included, because the ACL on `/vms` propagates. The schema describes `DELETE /nodes/{node}/qemu/{vmid}` as "Destroy the VM and all used/owned volumes". `destroy_vm` in `QemuServer.pm` removes every disk "owned by this VM (referenced in the config)" and the saved state of its snapshots. A `vzdump` backup on a backup storage is not part of the VM's configuration and stays. So a deleted VM has no undo except restoring such a backup. That a backup survives the delete is read from the source, not measured.
2. It can create VMs until a storage is full. A full thin pool returns write errors to every guest on it, see [storage.md](storage.md).
3. With the optional download role, the host fetches any URL the agent names, addresses on the owner's own network included. The schema says the download call "allows one to probe the (local!) host network indirectly".

So the agent asks the owner before every change and before every delete, as rules 4 and 9 in [SKILL.md](../SKILL.md) say. Before a delete it names the VM by ID and name, its node, and its newest backup with the date, and then waits for a yes for that one VM. One yes covers one VM. No answer means no delete. The token makes a delete possible. It is not permission to make one.

The protection flag, which stops a delete made by mistake, is under "Create and delete a VM" in [api-calls.md](api-calls.md#create-and-delete-a-vm).

#### What a full VM needs

| Step | Call | Privilege and path | Granted by |
|---|---|---|---|
| Pick a free VM ID | `GET /cluster/nextid` | none, the schema says `"user": "all"`, `Cluster.pm` | any token |
| See the bridges | `GET /nodes/<node>/network?type=any_bridge` | any user, but a bridge is listed only with `SDN.Audit` or `SDN.Use` on `/sdn/zones/localnetwork/<bridge>`, `Network.pm` | `PVEAuditor` on `/`, Alternative 1 and Alternative 2 |
| See the ISOs on a storage | `GET /nodes/<node>/storage/<iso-storage>/content?content=iso` | `Datastore.Audit` or `Datastore.AllocateSpace` on `/storage/<iso-storage>` | `PVEDatastoreUser`, Alternative 2 |
| Upload an ISO | `POST /nodes/<node>/storage/<iso-storage>/upload` | `Datastore.AllocateTemplate` on `/storage/<iso-storage>`, `Status.pm` | `AgentISO`, new here |
| Download an ISO by URL | `POST /nodes/<node>/storage/<iso-storage>/download-url` | `Datastore.AllocateTemplate` on `/storage/<iso-storage>`, and either `Sys.AccessNetwork` on `/nodes/<node>` or both `Sys.Audit` and `Sys.Modify` on `/`, `Status.pm` | `AgentISO` and `AgentDownload`, new here, optional |
| Create the VM | `POST /nodes/<node>/qemu` | `VM.Allocate` on `/vms/<vm-id>`, then one check per parameter, see the next table | `PVEVMAdmin`, `PVEDatastoreUser` and `PVESDNUser` |
| Start it | `POST /nodes/<node>/qemu/<vm-id>/status/start` | `VM.PowerMgmt` on `/vms/<vm-id>` | `PVEVMAdmin`, Alternative 2 |
| Delete a VM | `DELETE /nodes/<node>/qemu/<vm-id>` | `VM.Allocate` on `/vms/<vm-id>` | `PVEVMAdmin`, Alternative 2 |

The schema sums up the create call as: "You need 'VM.Allocate' permissions on /vms/{vmid} or on the VM pool /pool/{pool}. ... If you create disks you need 'Datastore.AllocateSpace' on any used storage.If you use a bridge/vlan, you need 'SDN.Use' on any used bridge/vlan." What `create_vm` in `Qemu.pm` checks, parameter by parameter:

| Parameter | Check | Where |
|---|---|---|
| `vmid` | `VM.Allocate` on `/vms/<vm-id>`, or on `/pool/<pool>` when `pool` is set | `Qemu.pm` |
| a new disk, `scsi0=<storage>:<size-in-GiB>` | `Datastore.AllocateSpace` on `/storage/<storage>` | `check_storage_access`, `Qemu.pm` |
| an ISO, `ide2=<iso-storage>:iso/<file>.iso,media=cdrom` | `Datastore.AllocateSpace` or `Datastore.Audit` on `/storage/<iso-storage>`, because `check_volume_access` in `Storage.pm` asks for one of them for `iso` content | `Qemu.pm`, `Storage.pm` |
| a network device, `net0=virtio,bridge=<bridge>` | `VM.Config.Network`, and `SDN.Use` on `/sdn/zones/localnetwork/<bridge>`. With a VLAN tag the path is `/sdn/zones/localnetwork/<bridge>/<tag>`, which an ACL on the bridge covers when it propagates. A bridge that is an SDN VNet is checked on `/sdn/zones/<zone>/<vnet>` instead | `check_bridge_access`, `Qemu.pm`, calling `check_vnet_access` in `GuestHelpers.pm` |
| `cores`, `sockets`, `cpu` | `VM.Config.CPU`, and `Mapping.Use` on `/mapping/cpu/<name>` for a custom CPU model | `check_vm_modify_config_perm` and `check_cpu_model_access` |
| `memory`, `balloon` | `VM.Config.Memory` | `check_vm_modify_config_perm` |
| `name`, `ostype`, `onboot`, `agent`, `bios`, `protection` | `VM.Config.Options`, and `Sys.Modify` on `/` for `startup`, which this alternative does not give | `check_vm_modify_config_perm` |
| `scsihw`, `machine`, `vga` | `VM.Config.HWType` | `check_vm_modify_config_perm` |
| `boot` | `VM.Config.Disk` | `check_vm_modify_config_perm` |
| cloud-init settings, `ciuser`, `cipassword`, `sshkeys`, `ipconfig0` | `VM.Config.Cloudinit`. On 9.x `nameserver` and `searchdomain` take that or `VM.Config.Network`, and on 8.x every cloud-init setting takes either one | `check_vm_modify_config_perm` |
| a cloud-init drive, `ide0=<storage>:cloudinit` | nothing beyond `VM.Allocate`, because `check_storage_access` skips a `cloudinit` volume | `Qemu.pm` |
| `start=1` | `VM.PowerMgmt`, checked before the VM is made on 9.x only | `Qemu.pm` |
| `ha-managed=1`, 9.x only | `Sys.Console` on `/`, which this alternative does not give | `Qemu.pm` |

The guest agent is the `agent=1` setting above. Talking to it later takes `VM.GuestAgent.Audit` or more on 9.x and `VM.Monitor` on 8.x, all in `PVEVMAdmin`.

Some things no token can set, because the check ends in "only root can set", for example a USB or PCI device passed through by its host ID rather than by a resource mapping, a serial port on a real device, and any setting in none of the lists, which the source comments as "catches args, lock, etc.", `Qemu.pm`. A custom cloud-init file in `cicustom` is the owner's job as well: the upload call takes only `iso`, `vztmpl` and `import`, so a snippet cannot be put on a storage through the API, and on recent 9.x releases of `qemu-server` the snippet also needs `Datastore.AllocateSpace` on its storage. Deleting an ISO needs `Datastore.Allocate`, which the schema gives for `DELETE /nodes/{node}/storage/{storage}/content/{volume}` as "You need 'Datastore.Allocate' privilege on the storage", so old ISOs are the owner's to remove.

#### Why a custom role and not PVEDatastoreAdmin

No built-in role holds `Datastore.AllocateTemplate` without `Datastore.Allocate`. `create_roles` in `AccessControl.pm` builds `PVEDatastoreAdmin` from the whole admin group of the storage privileges, and that group is `'Datastore.Allocate', 'Datastore.AllocateTemplate'` on one line. `PVEDatastoreUser` stops at `Datastore.AllocateSpace`, and apart from `PVEDatastoreAdmin` only `PVEAdmin` and `Administrator` carry the admin group.

`Datastore.Allocate` is much more than an ISO. The chapter describes it as "create/modify/remove a datastore and delete volumes". The schema asks for it on `/storage` to create, change or remove a storage configuration, `POST /storage`, `PUT /storage/{storage}` and `DELETE /storage/{storage}`, in `Config.pm`. And `check_volume_access` in `Storage.pm` returns at once for anyone holding it, so that token could use any disk or backup of any VM on that storage. A custom role with `Datastore.AllocateTemplate` alone gives the upload and the download and nothing else. The chapter says "Roles starting with `PVE` are always builtin, custom roles are not allowed use this reserved prefix."

The same holds for the download. `Sys.AccessNetwork` sits in the root group of the system privileges in `AccessControl.pm`, commented "for, e.g., downloading ISOs from any URL", and no role but `Administrator` carries that group. The other way the download call accepts, `Sys.Modify` on `/`, is what the chapter lists as "create/modify/remove node network parameters" and warns about. On `/nodes/<node>`, `Sys.AccessNetwork` also opens `query-url-metadata` and `query-oci-repo-tags` on that node, and on 9.x `oci-registry-pull` together with `Datastore.AllocateTemplate`. Each of those fetches something from a network address and changes nothing else. The checks that ask for it in the notification calls are on `/`, which this ACL does not reach.

#### A deeper permission replaces the one above it

The chapter, section "Inheritance": "Permissions on deeper levels replace those inherited from an upper level." In `roles` in `AccessControl.pm` that is `$roles = $new; # overwrite previous settings`. So an ACL on `/storage/<iso-storage>` with only `AgentISO` would take `PVEDatastoreUser` away on that storage, and an ACL on `/nodes/<node>` with only `AgentDownload` would take `PVEAuditor` away on that node. That is why both commands below name the inherited role again beside the new one. `PVESDNUser` holds `SDN.Audit` as well as `SDN.Use`, the `user` and `audit` groups of the SDN privileges as `create_roles` builds it, so the bridge needs nothing beside it.

#### Proxmox VE 8 and 9 for this alternative

| Item | 8.x | 9.x |
|---|---|---|
| `PVESDNUser` with `SDN.Use` and `SDN.Audit` | yes, `AccessControl.pm` | yes |
| `SDN.Use` checked on the bridge when a VM is created | yes in the `stable-bookworm` source, UNVERIFIED which 8.x release added the check, so an older 8.x host may skip it | yes |
| `Datastore.AllocateTemplate` for upload and download | yes | yes |
| `Sys.AccessNetwork` | only from `libpve-access-control` 8.1.2, and the download call accepts it only from `libpve-storage-perl` 8.1.0. An older host refuses the role with "invalid privilege" | yes |
| `VM.PowerMgmt` checked before the VM is made with `start=1` | no | yes |
| `Datastore.AllocateSpace` on the snippet storage for `cicustom` | not checked | yes in the `master` source, UNVERIFIED which 9.x release added the check, so an older 9.x host may skip it |
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

The calls are under "Create and delete a VM" in [api-calls.md](api-calls.md#create-and-delete-a-vm). With this alternative, pick the VM ID with the read-only token, and run every change call inside the `agent-change.env` subshell that "Calls that change something" in [api-calls.md](api-calls.md#calls-that-change-something) describes, only after the owner said yes to that one step.
