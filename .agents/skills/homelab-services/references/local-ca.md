# Local certificate authority for .internal names

Contents:

- [Why a local CA](#why-a-local-ca)
- [The CA and its name constraint](#the-ca-and-its-name-constraint)
- [Make the CA](#make-the-ca)
- [Why every name is listed, not *.internal](#why-every-name-is-listed-not-internal)
- [The CA in .env](#the-ca-in-env)
- [The one-shot Compose service](#the-one-shot-compose-service)
- [What the script checks, issues and refuses](#what-the-script-checks-issues-and-refuses)
- [The Nginx Proxy Manager include](#the-nginx-proxy-manager-include)
- [Keep the SSL tab on None](#keep-the-ssl-tab-on-none)
- [Restart after a new certificate](#restart-after-a-new-certificate)
- [Deploy, add a name, renew](#deploy-add-a-name-renew)
- [Trust the CA](#trust-the-ca)
- [Revoke or replace the CA](#revoke-or-replace-the-ca)
- [When https fails](#when-https-fails)

Read this before giving the `.internal` names `https`, before making or replacing the local certificate authority (CA for short), before adding a name to its certificate, before trusting the CA on a device, or when a `.internal` name fails over `https` only. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured with OpenSSL 3 and Nginx Proxy Manager 2, on the owner's homelab or in throwaway containers as the mark says, unless the mark names another version. Facts marked UNVERIFIED were read in documentation or source and never run.

Sources: `backend/templates/proxy_host.conf`, `backend/internal/nginx.js`, `docker/rootfs/etc/s6-overlay/s6-rc.d/prepare/50-ipv6.sh` and `docker/rootfs/usr/bin/common.sh` of https://github.com/NginxProxyManager/nginx-proxy-manager, `net/cert/x509_certificate.cc` and `net/cert/internal/trust_store_nss.cc` of https://github.com/chromium/chromium, `pki/verify_certificate_chain.cc` of https://github.com/google/boringssl, `lib/mozpkix/lib/pkixnames.cpp` and `lib/mozpkix/lib/pkixbuild.cpp` of https://github.com/nss-dev/nss, `crypto/x509/x509_vfy.c` and `crypto/x509/v3_utl.c` on the `openssl-3.5` branch of https://github.com/openssl/openssl, and the trust store pages each section names.

---

### Why a local CA

A `.internal` name can never get a public certificate, so without a CA of your own every `.internal` name is plain `http`. Most pages do not care, but the Proxmox web UI does: it sets its login cookie with the Secure flag, and a browser drops a Secure cookie on a plain `http` page, see [nginx-proxy-manager.md](nginx-proxy-manager.md#the-proxmox-web-ui-behind-the-proxy). UNVERIFIED in a browser, read in the Proxmox source.

The CA is made once on the owner's computer, stored in `<stack-dir>/.env` on the VM, and trusted on every device. A one-shot Compose service signs one certificate for every listed name and installs an include file into Nginx Proxy Manager, so every proxy host answers on 443 as well as on 80, and the SSL tab of every proxy host stays on None. Plain `http` keeps working.

VERIFIED on the homelab with curl 8 and the CA as `--cacert`: every name that had a proxy host answered over `https` with certificate check 0, and over `http` as before. VERIFIED: after its Forward Hostname lost a stray `:8006`, the Proxmox name answered 200 over `https`.

---

### The CA and its name constraint

The CA is EC P-256, valid 10 years, with three extensions:

1. `basicConstraints=critical,CA:TRUE,pathlen:0`, so it signs server certificates but no further CA.
2. `keyUsage=critical,keyCertSign,cRLSign`.
3. `nameConstraints=critical,permitted;DNS:internal,excluded;IP:0.0.0.0/0.0.0.0,excluded;IP:::/::`, so a verifier that checks it accepts the CA's signature only for names under `.internal` and for no IP address at all.

A CA a device trusts can sign a certificate for any name, a bank included, so its key is worth as much as every password typed into a browser. The constraint limits a stolen key to `.internal`. Every IP address is excluded because a constraint on one name type leaves the other types free.

Write `DNS:internal`, not `DNS:.internal`. RFC 5280 says a name made by adding labels on the left matches, and the NSS comment in `pkixnames.cpp` reads: "We interpret RFC 5280's language of "adding zero or more labels" to mean that whole labels must be prefixed." So `files.internal` matches and `evilinternal` does not. The same comment says a leading dot is something NSS and SChannel support beyond the standard: "a leading "." is legal and means the same thing as when the "." is omitted, EXCEPT that a presented identifier equal (case insensitive) to the name constraint is not matched". The plain form is the one every verifier reads the same way.

OpenSSL writes the IPv6 exclusion as an address and a mask, `IP:::/::`. `a2i_IPADDRESS_NC` in `v3_utl.c` parses the part after the slash as a second address, so `IP:::/0` is refused, with `bad ip address`. UNVERIFIED by a run.

VERIFIED in throwaway containers with a test CA made this way: `openssl verify` from OpenSSL 3 answered `permitted subtree violation` for certificates signed for `example.com`, `<name>.internal.example.com` and `evilinternal`, `excluded subtree violation` for an IPv4 address, and `OK` for `files.internal`. NSS 3 `vfychain`, with the test CA trusted as `C,,`, answered `Chain is bad!` for `example.com` and `Chain is good!` for `files.internal`. NSS printed error -8157 rather than its name constraint error, so the proof is the difference between the two results, not the message.

Who checks the constraint on a CA you added yourself, UNVERIFIED in a browser, read in source:

| Verifier | Checks it | Where |
|---|---|---|
| Chrome and Chromium on Linux | Yes | `trust_store_nss.cc` returns `ForTrustAnchor().WithEnforceAnchorConstraints()` for a CA trusted in the NSS database, and `ApplyTrustAnchorConstraints` in BoringSSL's `verify_certificate_chain.cc` then applies its name constraints |
| Firefox | Yes | `PathBuildingStep::Check` in `pkixbuild.cpp` calls `CheckNameConstraints` for every issuer, the trust anchor included |
| curl and other programs on OpenSSL | Yes, and VERIFIED above for `openssl verify` | `check_name_constraints` in `x509_vfy.c` |
| Windows, macOS, iPhone, Android | Unknown | No source read. The CA still works there, only this extra protection may be missing |

---

### Make the CA

Once, on the owner's computer, in a folder only the owner can read and never in a repository. Ask first, as for every change. Every openssl command runs in a throwaway container with no network, so nothing is installed. Give the CA a common name with the year, so a later replacement is easy to tell apart in a trust store. VERIFIED: these commands made the homelab's CA.

```bash
mkdir -m 700 <ca-dir>
```

In every command and in the Compose file below, replace `<version-tag>` with one release tag of the `alpine/openssl` image, the same tag everywhere, so the CA and every later certificate come from the same openssl.

```bash
docker run --rm --network none -u "$(id -u):$(id -g)" -v <ca-dir>:/ca -w /ca alpine/openssl:<version-tag> genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out ca.key
```

```bash
docker run --rm --network none -u "$(id -u):$(id -g)" -v <ca-dir>:/ca -w /ca alpine/openssl:<version-tag> req -x509 -new -key ca.key -sha256 -days 3650 -subj "/CN=<ca-name>" -addext "basicConstraints=critical,CA:TRUE,pathlen:0" -addext "keyUsage=critical,keyCertSign,cRLSign" -addext "nameConstraints=critical,permitted;DNS:internal,excluded;IP:0.0.0.0/0.0.0.0,excluded;IP:::/::" -out ca.crt
```

```bash
chmod 600 <ca-dir>/ca.key <ca-dir>/ca.crt
```

Read it back. The output must show `CA:TRUE, pathlen:0`, `Permitted: DNS:internal` and the two excluded addresses:

```bash
docker run --rm --network none -u "$(id -u):$(id -g)" -v <ca-dir>:/ca -w /ca alpine/openssl:<version-tag> x509 -in ca.crt -noout -subject -enddate -fingerprint -sha256 -ext basicConstraints,keyUsage,nameConstraints
```

On Windows the same `docker run` lines work in PowerShell without the `-u` option, with the volume written `-v "<ca-dir>:/ca"`, after `New-Item -ItemType Directory <ca-dir>`.

`ca.key` never leaves the owner's computer except into `.env` on the VM, and is backed up like a password manager. `ca.crt` is public, it is what every device trusts.

---

### Why every name is listed, not *.internal

Chrome refuses a wildcard certificate for `*.internal`. `X509Certificate::VerifyHostname` in `x509_certificate.cc` allows no wildcard directly under a registry controlled domain, and says: "In addition, unknown top-level domains (such as 'intranet' domains or new TLDs/gTLDs not yet added to the registry controlled domain dataset) are also implicitly prevented." UNVERIFIED in a browser, read in source. So the certificate lists every name as its own subject alternative name, and a new name means one more entry in `INTERNAL_DNS_NAMES`. The DNS side keeps its `*.internal` rewrite, see [adguard-home.md](adguard-home.md#a-wildcard-rewrite-for-internal-names), because a DNS rewrite is not a certificate.

---

### The CA in .env

The service reads three values from `<stack-dir>/.env`, next to the other secrets of hard rule 8:

| Key | Value |
|---|---|
| `INTERNAL_CA_CERT_B64` | `ca.crt` in base64, on one line |
| `INTERNAL_CA_KEY_B64` | `ca.key` in base64, on one line |
| `INTERNAL_DNS_NAMES` | Every `.internal` name that has a proxy host, separated by commas |

Append them from the owner's computer over SSH, after a yes. The values travel on standard input, so they never appear on a command line of either machine, and `tr` drops the carriage returns PowerShell adds. Unix shell:

```bash
printf 'INTERNAL_CA_CERT_B64=%s\nINTERNAL_CA_KEY_B64=%s\nINTERNAL_DNS_NAMES=%s\n' "$(base64 -w0 <ca-dir>/ca.crt)" "$(base64 -w0 <ca-dir>/ca.key)" '<names>' | ssh <user>@<vm-ip> "umask 077 && tr -d '\r' >> <stack-dir>/.env"
```

PowerShell:

```powershell
"INTERNAL_CA_CERT_B64=$([Convert]::ToBase64String([IO.File]::ReadAllBytes('<ca-dir>\ca.crt')))`nINTERNAL_CA_KEY_B64=$([Convert]::ToBase64String([IO.File]::ReadAllBytes('<ca-dir>\ca.key')))`nINTERNAL_DNS_NAMES=<names>" | ssh <user>@<vm-ip> "umask 077 && tr -d '\r' >> <stack-dir>/.env"
```

VERIFIED in a throwaway container: the PowerShell line, in PowerShell 7, wrote the same bytes as the Unix shell line. On macOS, if `base64` refuses `-w0`, use `openssl base64 -A -in <ca-dir>/ca.crt` instead, UNVERIFIED.

Check the lengths on the VM without printing a value. Every number must be above 0:

```bash
awk -F= '{print $1, length($2)}' <stack-dir>/.env
```

The service gets the values as environment variables, so `docker inspect internal-ca` shows the key. That adds nobody new: only the login user reads `.env`, and an account in the `docker` group is already as strong as root on the VM.

---

### The one-shot Compose service

One service, `internal-ca`, runs a POSIX shell script from the clone, `internal-ca/issue.sh`, in a pinned openssl image, and exits. It has no network, a read-only root with a `tmpfs` on `/tmp` for its work files, and `restart: "no"`. It runs as the image's root, so it can give the files the owner of `/data/custom_ssl`. Nginx Proxy Manager starts only after it exited 0:

```yaml
services:
  internal-ca:
    image: alpine/openssl:<version-tag>
    container_name: internal-ca
    restart: "no"
    logging: *default-logging
    network_mode: none
    read_only: true
    tmpfs:
      - /tmp
    entrypoint: ["/bin/sh", "/internal-ca/issue.sh"]
    environment:
      - INTERNAL_CA_CERT_B64=${INTERNAL_CA_CERT_B64:?set INTERNAL_CA_CERT_B64 in <stack-dir>/.env}
      - INTERNAL_CA_KEY_B64=${INTERNAL_CA_KEY_B64:?set INTERNAL_CA_KEY_B64 in <stack-dir>/.env}
      - INTERNAL_DNS_NAMES=${INTERNAL_DNS_NAMES:?set INTERNAL_DNS_NAMES in <stack-dir>/.env}
    volumes:
      - <stack-dir>/internal-ca:/internal-ca:ro
      - <stack-dir>/nginx/data/custom_ssl:/data/custom_ssl
      - <stack-dir>/nginx/data/nginx:/data/nginx

  nginx-proxy-manager:
    depends_on:
      internal-ca:
        condition: service_completed_successfully
```

The `:?` form makes Compose refuse every command for the whole stack while a value is missing, so the three lines go into `.env` before the new Compose file reaches the VM. `logging: *default-logging` is the anchor from [deploy-and-logs.md](deploy-and-logs.md).

`docker compose ps -a` shows `internal-ca` as `Exited (0)`, its normal state. A VM reboot starts the proxy again without the job, and the certificate stays on disk.

---

### What the script checks, issues and refuses

It refuses to start with exit 3 unless the CA certificate says `CA:TRUE`, carries a critical name constraint permitting `DNS:internal`, and matches the key, compared as public keys:

```sh
openssl x509 -in ca.crt -noout -ext nameConstraints
```

It refuses with exit 2 an empty list or any name that is not a plain name under `.internal`, a wildcard included. The pattern it uses:

```text
^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+internal$
```

It issues a new certificate when one of these is true, and otherwise keeps the old one and only reinstalls the include:

1. There is no certificate yet.
2. The certificate does not verify against the CA in `.env`, which is what a replaced CA causes.
3. Fewer than 30 days remain, `openssl x509 -checkend 2592000`.
4. The sorted names in the certificate differ from the sorted names in `INTERNAL_DNS_NAMES`.

The certificate is EC P-256, valid 397 days, with the first name as its common name and these extensions:

```ini
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature
extendedKeyUsage = serverAuth
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid
subjectAltName = DNS:<name-1>.internal,DNS:<name-2>.internal
```

It writes `fullchain.pem`, mode 644, and `privkey.pem`, mode 600, into `/data/custom_ssl/internal/` through a `.new` file and a rename, both owned like `/data/custom_ssl`. That is the user nginx runs as, root unless `PUID` is set, because `common.sh` sets `PUID=${PUID:-0}`. UNVERIFIED, read in source. The log ends with every name, the `notAfter=` date and the CA's fingerprint.

VERIFIED in throwaway containers: a second run said `the certificate is still good, nothing issued`, a changed name list, a certificate with 10 days left and a replaced CA each issued a new one, and a name outside `.internal`, a wildcard, a CA without the name constraint and the key of another CA each refused with exit 2 or 3. When the job fails during `docker compose up -d`, Compose prints `service "internal-ca" didn't complete successfully: exit 2` and stops, and a proxy already running keeps running. UNVERIFIED wording.

---

### The Nginx Proxy Manager include

Nginx Proxy Manager 2 ends the server block of every proxy host with an optional include, in `backend/templates/proxy_host.conf`:

```nginx
include /data/nginx/custom/server_proxy[.]conf;
```

The square brackets make it a pattern, so nothing happens until the file exists. The script copies this file there:

```nginx
listen 443 ssl;
listen [::]:443 ssl;
ssl_certificate /data/custom_ssl/internal/fullchain.pem;
ssl_certificate_key /data/custom_ssl/internal/privkey.pem;
```

Every proxy host, present and future, then answers on 443 with the one certificate. VERIFIED on the homelab. The IPv6 line follows the proxy's own setting: at every start `50-ipv6.sh` comments out every `listen [::]` line in the `.conf` files under `/data/nginx` when `DISABLE_IPV6` is true, this file included, and uncomments them otherwise. UNVERIFIED, read in source.

A name in the list with no proxy host gets no `https`: the default server refuses the handshake and curl reports `tlsv1 unrecognized name`. VERIFIED on the homelab.

---

### Keep the SSL tab on None

The include already gives every proxy host `listen 443 ssl` and a certificate. A certificate picked on the SSL tab adds a second `listen 443` to the same server block, and nginx refuses it with `a duplicate listen 0.0.0.0:443`, VERIFIED with nginx 1 in a throwaway container. Nginx Proxy Manager then marks the host `nginx_online: false`, renames its file to `.err` and reloads without it, so the host shows Offline. UNVERIFIED in the admin page, read in `backend/internal/nginx.js`.

So a proxy host that turned Offline after someone picked a certificate gets its SSL tab set back to None.

---

### Restart after a new certificate

nginx reads a certificate when it starts or reloads, and nothing reloads it when only the certificate changed. After every run that says `issuing a new certificate`, restart the proxy, after a yes, because every `.internal` name is down for a few seconds:

```bash
docker restart nginx-proxy-manager
```

VERIFIED in throwaway containers: the proxy served the old certificate until it was restarted and the new one after. Compose does not recreate a running proxy when only its `depends_on` changed, so the first deploy also needs this restart to load the include.

---

### Deploy, add a name, renew

Each step is a change on the VM, so each one is asked first, per hard rule 1. Copy `internal-ca/issue.sh` and `internal-ca/server_proxy.conf` from the clone to `<stack-dir>/internal-ca/` with `scp`, then the Compose file as [deploy-and-logs.md](deploy-and-logs.md) says. Then run the job and the proxy after it:

```bash
cd <stack-dir> && docker compose up -d internal-ca nginx-proxy-manager
```

Read what it did:

```bash
docker logs internal-ca
```

To add a name, add the proxy host first as [nginx-proxy-manager.md](nginx-proxy-manager.md#a-proxy-host-per-name) says, then append the name after a comma to the `INTERNAL_DNS_NAMES` line of `<stack-dir>/.env` in an editor. Compose sees the changed value and recreates the job:

```bash
cd <stack-dir> && docker compose up -d internal-ca
```

The log says `issuing a new certificate: the name list changed`, and the proxy needs the restart above.

Nothing renews the certificate by itself. It lasts 397 days, and the job issues a new one only when it runs with fewer than 30 days left. Read the end date on the `notAfter=` line:

```bash
docker logs --tail 2 internal-ca
```

In the last 30 days, run the job and restart the proxy. Apple requires a server certificate to last 825 days or fewer and to carry `serverAuth`, which 397 days and the extensions above meet: "TLS server certificates must have a validity period of 825 days or fewer" at https://support.apple.com/en-us/103769.

---

### Trust the CA

Every device that should open `https://<name>.internal` without a warning needs `ca.crt`, never `ca.key`. Trusting a CA changes the device, so ask first, and on the owner's computer give him the command, because most of these need an administrator. Restart the browser afterwards.

Linux system store on Arch Linux and CachyOS, read by curl and most command line programs. `trust` from p11-kit documents `--store` as "Store one or more anchors to the trust policy store" in `doc/manual/trust.xml` of https://github.com/p11-glue/p11-kit. VERIFIED on the owner's CachyOS desktop: `trust list --filter=ca-anchors` showed the CA with `trust: anchor`, and curl without `--cacert` answered 200 with certificate check 0.

```bash
sudo trust anchor --store <ca-dir>/ca.crt
```

Debian and Ubuntu. The manual page at https://manpages.debian.org/trixie/ca-certificates/update-ca-certificates.8.en.html, says: "Certificates must be in PEM format and have a .crt extension in order to be included by update-ca-certificates." UNVERIFIED by a run.

```bash
sudo cp <ca-dir>/ca.crt /usr/local/share/ca-certificates/<ca-file-name>.crt
```

```bash
sudo update-ca-certificates
```

Chrome and Chromium on Linux read the user NSS database `~/.pki/nssdb`, not the system store. `certutil` comes in the package `nss` on Arch Linux and `libnss3-tools` on Debian and Ubuntu. `C,,` means a CA trusted for websites. VERIFIED on the owner's desktop with certutil from NSS 3 run in a container: `certutil -L` listed the CA as `C,,`, and `vfychain` on a copy of the database printed `Chain is good!` for two names the homelab serves. No browser was opened for the check.

```bash
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "<ca-name>" -i <ca-dir>/ca.crt
```

Firefox has one database per profile. With Firefox closed, run this for each profile folder that holds a `cert9.db`. On the owner's desktop the profiles were under `~/.config/mozilla/firefox/` and `~/.mozilla` did not exist, older releases use `~/.mozilla/firefox/`. VERIFIED the same way as Chrome.

```bash
certutil -d sql:<profile-dir> -A -t "C,," -n "<ca-name>" -i <ca-dir>/ca.crt
```

Windows, from an administrator PowerShell, for every user. Chrome and Edge read this store. https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/certutil, says of `-addstore`: "Adds a certificate to the store." UNVERIFIED by a run.

```powershell
certutil -addstore -f Root <ca-dir>\ca.crt
```

macOS, for every user. Safari and Chrome read the System keychain. The `security` manual page at https://ss64.com/mac/security-cert.html, lists `-d` as "Add to admin cert store", with the user store as the default, and `trustRoot` as a result type. UNVERIFIED by a run.

```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain <ca-dir>/ca.crt
```

iPhone and iPad. Send `ca.crt` to the device by AirDrop or open it in Safari, then Settings, Profile Downloaded, Install. It is not trusted for websites until the switch is on: https://support.apple.com/en-us/102390, says "go to Settings > General > About > Certificate Trust Settings. Under "Enable full trust for root certificates," turn on trust for the certificate." UNVERIFIED by a run.

Android. Copy `ca.crt` to the phone, then Settings, Security, Encryption and credentials, Install a certificate, CA certificate, and the menu names differ between makers. https://developer.android.com/privacy-and-security/security-config, says: "By default, secure connections (using protocols like TLS and HTTPS) from all apps trust the pre-installed system CAs, and apps targeting Android 6.0 (API level 23) and lower also trust the user-added CA store by default." So many apps keep refusing the CA even when the browser accepts it, and nothing on the phone changes that. UNVERIFIED by a run.

---

### Revoke or replace the CA

A local CA has no revocation list, so revoking it means removing it from every trust store. Do it whenever `ca.key` may have leaked, and when the CA is replaced. Every line is UNVERIFIED by a run.

```bash
sudo trust anchor --remove <ca-dir>/ca.crt
```

```bash
sudo rm /usr/local/share/ca-certificates/<ca-file-name>.crt
```

```bash
sudo update-ca-certificates --fresh
```

```bash
certutil -d sql:$HOME/.pki/nssdb -D -n "<ca-name>"
```

```bash
certutil -d sql:<profile-dir> -D -n "<ca-name>"
```

```powershell
certutil -delstore Root "<ca-name>"
```

```bash
sudo security delete-certificate -c "<ca-name>" /Library/Keychains/System.keychain
```

The lines above are, in order: the Arch Linux system store, the two Debian and Ubuntu steps, Chrome on Linux, each Firefox profile with Firefox closed, Windows from an administrator PowerShell, and macOS. On an iPhone: Settings, General, VPN and Device Management, the profile, Remove Profile. On Android: Settings, Security, Encryption and credentials, User credentials, the CA, Remove.

Then make a new CA under a new common name, replace the two `INTERNAL_CA_` lines in `<stack-dir>/.env` in an editor, run the job and restart the proxy. The job sees that the old certificate does not verify against the new CA and logs `issuing a new certificate: the certificate does not verify against the current CA`, VERIFIED in a throwaway container. Trust the new `ca.crt` on every device.

---

### When https fails

| What you see | Cause |
|---|---|
| `required variable INTERNAL_CA_CERT_B64 is missing a value` | The three lines are not in `<stack-dir>/.env` |
| `service "internal-ca" didn't complete successfully: exit 2` | A name is not a plain name under `.internal`, or the list is empty. `docker logs internal-ca` names it |
| Exit 3 | The CA is not a CA, has no critical constraint permitting `DNS:internal`, or the key belongs to another certificate |
| The browser does not trust the certificate | The CA is not in that browser's store. On Linux, Chrome reads `~/.pki/nssdb` and the system store alone is not enough |
| An old certificate, or a new name missing from it | The proxy was not restarted after the job issued a new certificate |
| `unrecognized name` over `https` while `http` works | The name has no proxy host |
| A proxy host turned Offline | A certificate was picked on its SSL tab, see [Keep the SSL tab on None](#keep-the-ssl-tab-on-none) |
