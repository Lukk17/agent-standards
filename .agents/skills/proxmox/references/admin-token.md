# The Admin Token

Contents:

- [What a token is](#what-a-token-is)
- [Proxmox VE 8 and 9](#proxmox-ve-8-and-9)
- [The admin token](#the-admin-token)
- [What the token holds](#what-the-token-holds)
- [Taking it away](#taking-it-away)
- [Switching from a narrower alternative](#switching-from-a-narrower-alternative)

Read this before giving an agent access to a Proxmox VE host. The main way is an admin token for a user of its own, described here. Narrower tokens are in [narrower-tokens.md](narrower-tokens.md) as alternatives, for an owner who chose one of them instead. The env file, the certificate check and every API call are in [api-calls.md](api-calls.md). The rules live in [SKILL.md](../SKILL.md), and rule 4 there holds for every token: the agent asks the owner before every change, and rule 9 before every delete. The admin token commands and its permission list were measured on Proxmox VE 8, as "The admin token" says. Every other command here is UNVERIFIED.

Sources: the user management chapter https://pve.proxmox.com/pve-docs/chapter-pveum.html and its source `pveum.adoc`, the manual page https://pve.proxmox.com/pve-docs/pveum.1.html, the API viewer https://pve.proxmox.com/pve-docs/api-viewer/, `src/PVE/AccessControl.pm` in `pve-access-control`, and `www/manager6/dc/Config.js`, `www/manager6/dc/ACLView.js` and `www/manager6/dc/TokenEdit.js` in `pve-manager`.

---

### What a token is

The user management chapter, section "API Tokens": "API tokens allow stateless access to most parts of the REST API from another system, software, or API client." There are two kinds: "Separated privileges: The token needs to be given explicit access with ACLs. Its effective permissions are calculated by intersecting user and token permissions. This is the default for newly created tokens." And: "Full privileges: The token's permissions are identical to that of the associated user." The admin token below is of the second kind, and the alternatives in [narrower-tokens.md](narrower-tokens.md) are of the first.

The chapter also says: "The token value is only displayed/returned once when the token is generated. It cannot be retrieved again over the API at a later time!"

---

### Proxmox VE 8 and 9

Every `pveum` command and every API call in this file, in [api-calls.md](api-calls.md) and in [narrower-tokens.md](narrower-tokens.md), works on Proxmox VE 8.x and 9.x, except that an early 8.x host lacks `Sys.AccessNetwork`, which the download role of the admin token and of Alternative 3 uses, as "Proxmox VE 8 and 9 for this alternative" under Alternative 3 in [narrower-tokens.md](narrower-tokens.md#proxmox-ve-8-and-9-for-this-alternative) says. What differs between the two is what the built-in roles contain, and one extra check on rollback. Checked against the 8.x branches, `stable-bookworm` of `pve-access-control`, `qemu-server` and `pve-docs`, and `stable-8` of `pve-manager`, beside the 9.x sources named above.

| Item | 8.x | 9.x |
|---|---|---|
| `pveum acl modify` options | `--users`, `--tokens`, `--roles`, `--propagate` | the same |
| The short form `-user`, `-token`, `-role` | works, and `-user`, `-role`, `-comment`, `-privsep` and `-privs` were measured on Proxmox VE 8 | works, inferred from the source, not measured |
| `pveum user token add` with `--privsep` and `--expire` | yes | yes |
| `pveum user token permissions` | yes | yes |
| `VM.Monitor` in `PVEVMAdmin` | yes | no, the privilege is gone |
| `VM.GuestAgent.*` and `VM.Replicate` | do not exist | in `PVEVMAdmin`, and `VM.GuestAgent.Audit` in `PVEAuditor` |
| `Datastore.AllocateSpace` on the disk's storage for a resize | checked | checked |
| `VM.PowerMgmt` for a rollback with `start` set | not checked | checked |
| Web page names below and in [narrower-tokens.md](narrower-tokens.md) | the same | the same |

The `pveum` manual page writes the ACL options as `--users`, `--tokens` and `--roles`, under `pveum acl modify <path> --roles <string> [OPTIONS]`, because those are the parameter names of `PUT /access/acl` in `ACL.pm`, the same on both branches. The chapter's own examples write `-user`, `-token` and `-role`, and both work because the command line parser in `JSONSchema.pm` sets `prefix_pattern=(--|-)` on both branches and leaves Getopt::Long's abbreviation of option names on, so `-user` is read as `--users`. The admin token commands use the short form exactly as the owner ran them on Proxmox VE 8, and the alternatives use the manual page's form.

---

### The admin token

This is the main way to give an agent access. The owner does this, on the host or in the web page. The agent only receives the result in the env file that [api-calls.md](api-calls.md#the-env-file) describes.

The token belongs to a user of its own and holds `PVEAdmin` on `/`. It can create, change and delete VMs and storage content, manage storages and SDN, create users and groups but not grant permissions, and download ISO files. The agent still asks the owner before every change and before every delete, one VM per yes, as rules 4 and 9 in [SKILL.md](../SKILL.md) say. The token makes a change possible. It is not permission to make one.

The token is made with `-privsep 0`, so its permissions are the user's own. On a dedicated user that holds nothing but this token, that gives the same result as privilege separation with the same ACLs given to the token.

On the host shell, as root, in the short form the owner ran on Proxmox VE 8. The user, with no password, because the token is the only way in:

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

Why the second role: `PVEAdmin` does not hold `Sys.AccessNetwork`, and the download call needs it on `/nodes/<node>`, see "What a full VM needs" under Alternative 3 in [narrower-tokens.md](narrower-tokens.md#what-a-full-vm-needs). No built-in role but `Administrator` carries it, as "Why a custom role and not PVEDatastoreAdmin" there explains. And a role on a deeper path replaces the inherited one, see "A deeper permission replaces the one above it" there, so an ACL on `/nodes/<node>` with `AgentDownload` alone would take `PVEAdmin` away on that node. That is why the node ACL names `PVEAdmin` again. On 8.x, `Sys.AccessNetwork` exists only from `libpve-access-control` 8.1.2, and an older host refuses the role, see "Proxmox VE 8 and 9 for this alternative" under Alternative 3.

In the web page, under Datacenter, Permissions, the names from `Config.js`, `TokenEdit.js`, `RoleEdit.js` and `ACLView.js`:

1. Users, Add: User name `<user>`, Realm `pve`, Password left empty.
2. API Tokens, Add: User `<user>@pve`, Token ID `<token-id>`, Privilege Separation not ticked. Copy the secret from the Token Secret window, which says "Please record the API token secret - it will only be displayed now".
3. Roles, Create: Name `AgentDownload`, Privileges `Sys.AccessNetwork`.
4. Permissions, Add, User Permission: Path `/` with Role `PVEAdmin`, then Path `/nodes/<node>` twice, once with Role `PVEAdmin` and once with Role `AgentDownload`. Propagate ticked each time.

#### What the token holds

VERIFIED on Proxmox VE 8, through this token with `GET /access/permissions`:

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

Or from the agent's machine, once the env file of [api-calls.md](api-calls.md#the-env-file) is filled and loaded:

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

An owner who set up one of the alternatives in [narrower-tokens.md](narrower-tokens.md) first removes every ACL it gave the user, path by path, naming the role each one gave, and then deletes every custom role nothing else uses. Remove the deeper ACLs as well, such as those of Alternative 3 on a bridge, an ISO storage or a node, because a deeper permission replaces the inherited one and a leftover one would take `PVEAdmin` away on that path. List what is there:

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

The owner did exactly this on Proxmox VE 8, coming from `PVEAuditor` on `/`, `PVEDatastoreUser` on `/storage` and a custom VM role on `/vms`. An alternative's token was made with privilege separation. Remove it with `pveum user token remove` as above and add the new one with `-privsep 0`, then give the user the ACLs above. Skip `pveum role add AgentDownload` when Alternative 3 already made that role.
