# Container rules with examples

Open this for the Pass and Fail form, the commands, and the reasoning behind any rule in [SKILL.md](../SKILL.md). Full Dockerfiles are in [dockerfiles.md](dockerfiles.md), and full Compose stacks in [compose-and-debugging.md](compose-and-debugging.md).

---

### Contents

- [Named volumes only](#named-volumes-only)
- [Build in stages, ship the last one](#build-in-stages-ship-the-last-one)
- [Pin the base image](#pin-the-base-image)
- [Run as a non-root user](#run-as-a-non-root-user)
- [No secret in an image or a compose file](#no-secret-in-an-image-or-a-compose-file)
- [Isolate what should not be reachable](#isolate-what-should-not-be-reachable)
- [.dockerignore](#dockerignore)
- [Supply chain: scan, bill of materials, signature](#supply-chain-scan-bill-of-materials-signature)
- [Registry retention](#registry-retention)

---

### Named volumes only

An anonymous volume (`- /app/node_modules`) gets a random hash for a name. Nothing can back it up, target it,
inspect it, or share it, and it survives `docker compose down` as a dangling volume consuming disk invisibly. In
production it ties data to a container lifecycle instead of a managed resource.

Pass:

```yaml
volumes:
  - node_modules:/app/node_modules
```

Fail:

```yaml
volumes:
  - /app/node_modules
```

---

### Build in stages, ship the last one

A multi-stage build keeps compilers, dev dependencies, and build caches out of the shipped image. Copy dependency
manifests before source so a code change does not invalidate the dependency layer.

Pass:

```dockerfile
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
```

Fail:

```dockerfile
COPY . .
RUN npm ci
```

Full reference Dockerfiles for Node, Go, and Python, plus the apt-get, OCI label, and build-secret rules, are in
[references/dockerfiles.md](dockerfiles.md).

---

### Pin the base image

`:latest` makes a build unreproducible and silently changes the runtime under you. Pin a tag that names the runtime
version and the OS variant, and pin a digest where the registry supports it. The examples show `@sha256:<digest>` in
place of a real digest. Read the digest a tag resolves to with `docker buildx imagetools inspect <image>:<tag>`, and let
Dependabot or Renovate bump the tag and the digest together.

Pass:

```dockerfile
FROM node:26-alpine@sha256:<digest>
```

Fail:

```dockerfile
FROM node:latest
```

Pick the smallest base that can actually run the artefact:

| Workload | Preferred base |
|---|---|
| Compiled binaries (Go, Rust) | `gcr.io/distroless/static-debian13:nonroot` or `scratch` |
| JVM (Spring Boot) | `gcr.io/distroless/java25-debian13:nonroot` |
| Node.js | `node:26-alpine` |
| Python | `python:3.14-slim` |

Distroless publishes no version tags, only `latest`, `nonroot` and their `debug` variants, so its pin is the Debian
suffix in the name plus a digest.

Never use `ubuntu:latest` or `debian:latest` as a runtime base.

---

### Run as a non-root user

Create a user in the image and switch to it before the runtime stage ends. A container escape from root is a host
compromise, from an unprivileged user it usually is not.

Pass:

```dockerfile
RUN addgroup -g 1001 -S appgroup && adduser -S appuser -u 1001
USER appuser
```

Fail:

```dockerfile
CMD ["node", "dist/server.js"]
```

Harden the runtime from Compose as well, dropping every capability and adding back only what the process genuinely
needs:

```yaml
services:
  app:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /app/.cache
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

`NET_BIND_SERVICE` is only needed when the process binds a port below 1024. Listen on a high port and drop it too.

---

### No secret in an image or a compose file

Inject secrets at runtime through the environment or a Docker secret. Anything set with `ENV` or `ARG` is readable
from the image history by anyone who can pull it.

Pass:

```yaml
services:
  app:
    env_file:
      - .env
    environment:
      - API_KEY
```

Fail:

```dockerfile
ENV API_KEY=sk-proj-xxxxx
```

`- API_KEY` with no value inherits the variable from the host environment, so the value never enters a committed
file. `.env` is gitignored. For build-time credentials use `--mount=type=secret`, covered in
[references/dockerfiles.md](dockerfiles.md).

---

### Isolate what should not be reachable

Put a database on its own network rather than relying on nobody connecting to it, and bind published ports to
loopback so they are not exposed to the host's network.

Pass:

```yaml
services:
  db:
    ports:
      - "127.0.0.1:5432:5432"
    networks:
      - backend-net
```

Fail:

```yaml
services:
  db:
    ports:
      - "5432:5432"
```

Omit `ports` on internal services in production entirely. Compose service names resolve inside the network, so
nothing needs a published port to talk to them.

---

### .dockerignore

Without one, the whole working tree goes into the build context, which slows every build and risks copying `.env`
and `.git` into a layer. Create it next to the Dockerfile.

Pass:

```text
node_modules
dist
build
*.log
.git
.gitignore
.env
.env.*
coverage
**/*.test.ts
**/*.spec.ts
tests/
```

Fail:

```text
node_modules
```

---

### Supply chain: scan, bill of materials, signature

The supply-chain rules are canonical for the repository in [SKILL.md](../SKILL.md), and other skills point there. This section carries the commands.

Scan every image in CI before it is pushed, and fail the build on a fixable critical or high finding:

```bash
trivy image --exit-code 1 --severity CRITICAL,HIGH myimage:tag
```

Store the scan report as a CI artifact, so a later question about what was known at release time has an answer.

Generate a Software Bill of Materials after push:

```bash
syft myimage:tag -o cyclonedx-json > sbom.json
```

Sign, attest, and verify the image by the digest the push reported, never by tag. A tag can move between the push and
the signature, so signing by tag can sign a different image, and cosign warns when it is given one. The pipeline
form, which reads the digest from the build step, is in `deployment-patterns`.

Attach the SBOM to the pushed image as a signed attestation, so it travels with the image in the registry:

```bash
cosign attest --key cosign.key --type cyclonedx --predicate sbom.json myregistry/myimage@sha256:<digest>
```

Sign every production image after push:

```bash
cosign sign --key cosign.key myregistry/myimage@sha256:<digest>
```

Verify before deploy, in the pipeline, not by hand:

```bash
cosign verify --key cosign.pub myregistry/myimage@sha256:<digest>
```

A signature nothing verifies proves nothing. The verify step belongs in the deploy job, gating it, and a cluster
policy should reject an unsigned image outright.

---

### Registry retention

Keep the last 10 tagged releases, auto-delete untagged images after 7 days, and implement it as a registry lifecycle
policy rather than a cleanup script somebody remembers to run.

Pass:

```text
ECR lifecycle policy: keep 10 images tagged with prefix "v", expire untagged after 7 days.
```

Fail:

```bash
docker system prune -a
```
