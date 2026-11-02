# File Browser

Contents:

- [Which image](#which-image)
- [config.yaml before the first start](#configyaml-before-the-first-start)
- [The first admin password](#the-first-admin-password)
- [Resetting a lost admin password](#resetting-a-lost-admin-password)
- [Check it](#check-it)

Read this before setting up File Browser, reading its first admin password, or resetting that password. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab on one File Browser Quantum 2 release from the `gtstef/filebrowser` image. Every other command here is UNVERIFIED.

Sources in https://github.com/gtsteffaniak/filebrowser: `backend/internal/state/bootstrap_admin_password.go` and `backend/pkg/settings/auth.go`, the README at the default branch, and the README of the original `filebrowser/filebrowser` at its default branch.

---

### Which image

`gtstef/filebrowser` is File Browser Quantum, a maintained fork, with a stable channel from 2.0.0. The original `filebrowser/filebrowser` is archived, and its README says: "The last planned release has already shipped. There will be no further releases, bug fixes, or security fixes." The `-slim` tag leaves out ffmpeg, so it makes no video thumbnails, which suits a small VM where Plex owns the video work.

Replace `<version>` with a release of the stable channel, so an upgrade is a deliberate change, and `<digest>` with the digest that tag resolves to, read with `docker buildx imagetools inspect gtstef/filebrowser:<version>-stable-slim`, so a re-pushed tag cannot change what runs. It listens on port 80 inside the container, keeps its database and `config.yaml` in `/home/filebrowser/data`, and runs as the user the Compose file gives it:

```yaml
filebrowser:
  image: gtstef/filebrowser:<version>-stable-slim@sha256:<digest>
  user: "1000:1000"
  ports:
    - "7782:80/tcp"
  volumes:
    - <stack-dir>/filebrowser/data:/home/filebrowser/data
    - type: bind
      source: /mnt/data
      target: /srv
      bind:
        create_host_path: false
```

---

### config.yaml before the first start

The data mount hides the config file the image ships with, so write one before the first start, as the login user. One command writes the whole file:

```bash
printf '%s\n' 'http:' '  port: 80' '  baseURL: "/"' '  trustProxyHeaders: true' 'server:' '  sources:' '    - path: "/srv"' '      name: "files"' 'auth:' '  methods:' '    password:' '      enabled: true' '      minLength: 12' '      signup: false' > <stack-dir>/filebrowser/data/config.yaml
```

`trustProxyHeaders` makes File Browser log the visitor rather than Nginx Proxy Manager. `signup: false` leaves account creation to the admin. VERIFIED: this file on the homelab.

---

### The first admin password

A fresh install creates the user `admin` with a random password and prints it once, in its log. `bootstrap_admin_password.go` logs `Generated initial admin password for user %q (set auth.adminPassword in config to override on future resets): %s`. VERIFIED: the line appeared once, at the first start.

The owner reads it, not the agent, because it is a password. Give the owner this command to run on the VM:

```bash
docker logs filebrowser 2>&1 | grep 'initial admin password'
```

The owner signs in, changes it under Settings, then User management, and makes a normal account for daily use.

---

### Resetting a lost admin password

`ConfigTriggersAdminPasswordReset` in `backend/pkg/settings/auth.go` returns true when `auth.adminPassword` holds anything other than an empty value or `admin`, and the password is then written into the `admin` account at every start. So the owner adds the line, restarts, signs in, removes the line, and restarts again.

The owner types it, hidden. Leave out double quotes and backslashes, because the value goes between double quotes:

```bash
read -r -s -p 'New File Browser admin password: ' FB_ADMIN_PASS; echo
```

`auth:` is the last block of the file above, so a line appended with two spaces in front belongs to it:

```bash
printf '  adminPassword: "%s"\n' "$FB_ADMIN_PASS" >> <stack-dir>/filebrowser/data/config.yaml
```

```bash
unset FB_ADMIN_PASS
```

```bash
cd <stack-dir> && docker compose restart filebrowser
```

After signing in, remove the line, or every later restart undoes a password change made in the web page:

```bash
sed -i '/^  adminPassword:/d' <stack-dir>/filebrowser/data/config.yaml
```

Check it without printing it. This must print 0:

```bash
grep -c '^  adminPassword:' <stack-dir>/filebrowser/data/config.yaml
```

```bash
cd <stack-dir> && docker compose restart filebrowser
```

---

### Check it

File Browser answers `/health`. Through the proxy, from any machine:

```bash
curl -sI http://<name>.internal/health
```

A 200 means it answers. A 502 from the proxy means it is stopped, or the proxy host forwards to the published port instead of container port 80.
