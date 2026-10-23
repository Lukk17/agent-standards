# Deploying the stack and capping its logs

Read this before copying a change to the VM, before the first start of a new service, or before adding a service to the Compose file. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab on 2026-10-23. Every other command here is UNVERIFIED.

Sources, fetched on 2026-10-23: the Docker page on the json-file logging driver at https://docs.docker.com/engine/logging/drivers/json-file/, the Compose page on interpolation at https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/, and the Compose specification at https://github.com/compose-spec/compose-spec/blob/main/12-interpolation.md.

---

### Where the files live

The Compose file and every file it mounts, such as the Telegraf config, live in a git clone on the owner's machine. The VM holds a plain copy of them in `<stack-dir>`, with no clone and no git. A change goes into the clone first and is copied from there, so the clone always says what runs.

Do not fetch the files from a GitHub raw link. A raw link gives what was pushed, so a change that is committed but not pushed, or not committed yet, never reaches the VM, and nothing says so. On the owner's homelab, on 2026-10-23, the Telegraf config on the VM was found two weeks older than the one in the repository, because nothing had copied it.

---

### Copy and start

From the owner's machine, copy the Compose file. Unix shell:

```bash
scp <clone-dir>/compose.yaml <user>@<vm-ip>:<stack-dir>/compose.yaml
```

PowerShell:

```powershell
scp <clone-dir>\compose.yaml <user>@<vm-ip>:<stack-dir>/compose.yaml
```

Copy every file it mounts that changed the same way, for example the Telegraf config:

```bash
scp <clone-dir>/telegraf/telegraf.conf <user>@<vm-ip>:<stack-dir>/telegraf/telegraf.conf
```

On the VM, fetch any image whose tag changed:

```bash
cd <stack-dir> && docker compose pull
```

Recreate every container whose settings or image changed:

```bash
cd <stack-dir> && docker compose up -d
```

Check that every service is up:

```bash
cd <stack-dir> && docker compose ps
```

`docker compose up -d` leaves a container alone when only a file it mounts changed. A service that reads its configuration only at start, Telegraf for one, needs a restart after its file was copied:

```bash
docker restart telegraf
```

VERIFIED: the owner deployed this way on 2026-10-23.

---

### Folders before the first start

Create every folder a container mounts before its first start, as the login user and without `sudo`. A folder that is missing is created by Docker itself, owned by root, and a container that runs as user 1000 then cannot write into it. VERIFIED on 2026-10-23 for the network watch folder, which Telegraf, running as 1000, could not write until it was given to 1000.

```bash
mkdir -p <stack-dir>/<service>/data
```

A file mount whose source is missing fails the start instead. Docker creates a directory where the file should be, and the error ends with `not a directory: Are you trying to mount a directory onto a file (or vice-versa)? Check if the specified host path exists and is the expected type`. Remove that directory, put the real file there, and start again:

```bash
sudo rmdir <stack-dir>/telegraf/telegraf.conf
```

A mount of a data disk uses the long form with `create_host_path: false`, so Docker refuses to start the container when the folder is missing rather than creating it on the system disk. The mount point itself also needs the protection in [data-disk.md](data-disk.md#protect-the-empty-mount-point), because an empty mount point is always there.

```yaml
volumes:
  - type: bind
    source: /mnt/data
    target: /srv
    bind:
      create_host_path: false
```

---

### Log limits on every service

Docker's `json-file` driver keeps the whole log unless told otherwise. The Docker page lists `max-size` as "The maximum size of the log before it is rolled. [...] Defaults to -1 (unlimited)" and `max-file` as "The maximum number of log files that can be present. [...] Only effective when `max-size` is also set."

Why it matters, VERIFIED on 2026-10-23: with no logging options anywhere, the `uptime-kuma` container's log reached 24.7 GB, growing 1,607,027 bytes in 60 seconds from the error in [uptime-kuma.md](uptime-kuma.md#the-labelset-log-flood), and together with a half-sized root volume it filled the VM's disk.

Put one anchor at the top of the Compose file:

```yaml
x-logging: &default-logging
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

And give it to every service:

```yaml
services:
  uptime-kuma:
    logging: *default-logging
```

A limit applies only to a container created after it. `docker compose up -d` recreates every container whose logging changed, and the old container's log goes with it. VERIFIED on 2026-10-23: `df -h /` showed 44G used before that `docker compose up -d` and 20G after it.

Read the log options a running container really has:

```bash
docker inspect --format '{{.Name}} {{json .HostConfig.LogConfig}}' $(docker ps -q)
```

A line with `"Config":{}` is a container with no limit.

---

### Dollar signs in Compose

Compose replaces `$NAME` and `${NAME}` in the Compose file with a value from the environment or from `.env`. The specification says "You can use a `$$` (double-dollar sign) when your configuration needs a literal dollar sign." So a literal `$` in `compose.yaml` is written `$$`.

In `.env` the Compose page says "Unquoted and double-quoted (`"`) values have interpolation applied" and "Single-quoted (`'`) values are used literally". A password with a `$` in an unquoted value is cut at the `$`. Either leave `$` out of a password, or write the value in single quotes, in which case the password must not hold a `'`. The way to write `.env` without printing a secret is in [samba.md](samba.md#the-login-file).

A required value is written `${NAME:?message}`, and Compose then refuses every command for the whole stack while the value is missing or empty. VERIFIED on 2026-10-23: `required variable SAMBA_USER is missing a value`.
