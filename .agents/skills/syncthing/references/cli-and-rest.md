# syncthing cli and the REST API

Contents:

- [How syncthing cli finds the running instance](#how-syncthing-cli-finds-the-running-instance)
- [Read the API key and the GUI address](#read-the-api-key-and-the-gui-address)
- [Call the REST API without the key on the command line](#call-the-rest-api-without-the-key-on-the-command-line)
- [Set a GUI user and password](#set-a-gui-user-and-password)

Read this before reading the API key, calling the REST API, or changing the GUI credentials. The rules live in [SKILL.md](../SKILL.md). Commands marked VERIFIED ran on Syncthing 2 in a throwaway container. Every other command here, every PowerShell command included, is UNVERIFIED.

Sources: https://docs.syncthing.net/users/syncthing.html, https://docs.syncthing.net/dev/rest.html, https://docs.syncthing.net/rest/config.html, https://curl.se/docs/manpage.html, and `cmd/syncthing/cli/config.go` of `syncthing/syncthing`.

---

### How syncthing cli finds the running instance

The command line page says the `cli` subcommand "basically saves the hassle of handling HTTP connections and API authentication". Run on the same machine and as the same user as Syncthing, it reads the local configuration for the GUI address and the API key, so no key has to be typed. VERIFIED.

It reads the local configuration only when neither an address nor a key was given. When one of `--gui-address` and `--gui-apikey` is given, or one of `STGUIADDRESS` and `STGUIAPIKEY` is set in the environment, it wants both, read in `cmd/syncthing/cli/client.go`, and stops with this error, measured in the official Docker image, which sets `STGUIADDRESS`:

```text
syncthing: error: Both --gui-address and --gui-apikey should be specified
```

Every level answers `--help` and lists what it can do. Start there rather than guessing a name. VERIFIED:

```bash
syncthing cli --help
```

```bash
syncthing cli config folders --help
```

The `config` tree is generated from the configuration structure, so a property is reached by its path in kebab case and read or written with `get` and `set`, a list grows with `add`, and an item goes with `delete`. `dump-json` prints a whole object. VERIFIED examples:

```bash
syncthing cli config folders list
```

```bash
syncthing cli config devices <device-id> dump-json
```

```bash
syncthing cli config options min-home-disk-free dump-json
```

In Syncthing 2 `syncthing cli config` reads the whole configuration over the REST API, changes it, and posts the whole configuration back to `system/config`, read in `cmd/syncthing/cli/config.go`. Run one change at a time and read it back, because two writers at once can overwrite each other. That last point is inferred from the code, not measured.

The other groups, all present in Syncthing 2, read in the help output and in `cmd/syncthing/cli/show.go`, `errors.go` and `pending.go`:

| Command | What it does |
|---|---|
| `syncthing cli show system` | `myID`, uptime, listeners |
| `syncthing cli show connections` | one entry per device with `connected`, `type`, `address` |
| `syncthing cli show pending devices` | devices that tried to connect and are not configured |
| `syncthing cli show pending folders` | folders a peer offered that are not added here |
| `syncthing cli errors show` | the recent error list, the same as `/rest/system/error` |
| `syncthing cli errors clear` | clears that list |
| `syncthing cli operations restart` | restarts Syncthing |
| `syncthing cli operations shutdown` | stops Syncthing |
| `syncthing cli operations folder-override <folder-id>` | its own help says "WARNING: Destructive - deletes/changes your data", ask first |

---

### Read the API key and the GUI address

The REST page says: "To use an API key, set the request header `X-API-Key` to the API key value, or set it as a `Bearer` token in the `Authorization` header". The key is a secret, so read it into a variable instead of printing it. VERIFIED in bash:

```bash
st_key="$(syncthing cli config gui apikey get)"
```

```powershell
$stKey = syncthing cli config gui apikey get
```

The address the GUI and the API listen on, and whether they use TLS. VERIFIED:

```bash
syncthing cli config gui raw-address get
```

```bash
syncthing cli config gui raw-use-tls get
```

The default is `127.0.0.1:8384`. The official Docker image overrides it with `STGUIADDRESS=0.0.0.0:8384`, see [docker.md](docker.md).

---

### Call the REST API without the key on the command line

A header on the command line shows up in the process list. curl reads headers from standard input: its manual says "Using @- makes curl read the header file from stdin". `printf` is a shell builtin, so the key never becomes an argument of a separate process. VERIFIED in bash:

```bash
printf 'X-API-Key: %s\n' "$st_key" | curl -s -H @- http://127.0.0.1:8384/rest/system/version
```

In PowerShell call `curl.exe` by that name, because `curl` is an alias for `Invoke-WebRequest` in Windows PowerShell 5.1, and quote `@-`, because a bare `@` starts a splat:

```powershell
"X-API-Key: $stKey" | curl.exe -s -H '@-' http://127.0.0.1:8384/rest/system/version
```

Add `-k` only when `raw-use-tls` is true and the GUI uses Syncthing's own certificate, and then use `https://`. The endpoint `/rest/noauth/health` needs no key and answered HTTP 200 in the container, and the official image's health check greps its body for `OK`.

The configuration endpoints, from the config page: `/rest/config/folders` and `/rest/config/devices` take `POST` for one object, and `/rest/config/folders/<folder-id>` takes `GET`, `PUT`, `PATCH` and `DELETE`. "PATCH replaces only the given child objects." A folder created with `POST` gets every default filled in, `minDiskFree` included, which `syncthing cli config folders add` does not do, see [folders-and-devices.md](folders-and-devices.md).

---

### Set a GUI user and password

The page on the GUI listen address, https://docs.syncthing.net/users/guilisten.html, says the default `127.0.0.1:8384` "only listens for connections from the same computer Syncthing is running on". Before the GUI listens on anything else, give it a user and a password.

The command line route keeps the password out of the process list. `syncthing generate` reads it from standard input when `--gui-password=-` is given, and the page says "A plaintext password is hashed before writing to the config file". Stop Syncthing first, because the running instance keeps its own copy of the configuration and writes it back. VERIFIED on a fresh home in a container, where the stored value began with `$2a$10$`:

```bash
syncthing generate --gui-user=<gui-user> --gui-password=-
```

Type the password, press Enter, then end the input with Ctrl+D on Linux and macOS or Ctrl+Z and Enter on Windows, and start Syncthing again.

On a running instance, `PATCH /rest/config/gui` with `{"user": "<gui-user>", "password": "<password>"}` does the same: the config page says "a plaintext password is first hashed". `syncthing cli config gui password set <password>` also stores a bcrypt hash, VERIFIED, but it puts the password on the command line, so use it only where nobody else can read the process list.

Leave `insecure-admin-access` false, and check it:

```bash
syncthing cli config gui insecure-admin-access get
```
