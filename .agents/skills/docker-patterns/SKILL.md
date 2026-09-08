---
name: docker-patterns
description: Docker and Compose standards for multi-stage builds, pinned base images, non-root runtime users, named volumes, network isolation, build-time and runtime secrets, and the Trivy, SBOM and cosign supply-chain gate. Use when you say "write a Dockerfile for this service", "set up compose for local dev", "my container cannot reach the database", "shrink this image", or "scan and sign this image before we push". Not for Kubernetes manifests and rollout strategy, use `deployment-patterns`.
---

# Docker Patterns

How a container image stays small, reproducible, and safe to run: a pinned base, a build split into stages, a
non-root user, no secret baked into a layer, and a scan plus a signature before it is trusted anywhere. Compose then
wires those images into a local stack that behaves like the real one.

Baseline: Docker Engine 29.3 and Docker Compose v5.1 (both verified locally). The Compose v1 `docker-compose`
command is gone, every command below is `docker compose`.

---

### When to activate

- Writing or reviewing a Dockerfile or a Compose file.
- Setting up or debugging a local multi-service development stack.
- Shrinking an image, or fixing one that rebuilds everything on every change.
- Hardening a container: user, capabilities, filesystem, secrets.
- Adding image scanning, an SBOM, or signing to a pipeline.
- Diagnosing container networking, DNS, or volume behaviour.

---

### When not to activate

- Writing Kubernetes manifests, probes, or rollout strategy, use `deployment-patterns`.
- Configuring hosts rather than containers, use `ansible`.
- Writing the entrypoint script itself, use `bash` or `powershell`.
- Instrumenting the application inside the container, use `observability-and-logging`.
- Reviewing the application's own authentication or input handling, use `security-review`.

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
[references/dockerfiles.md](references/dockerfiles.md).

---

### Pin the base image

`:latest` makes a build unreproducible and silently changes the runtime under you. Pin a specific tag, and pin a
digest where the registry supports it.

Pass:

```dockerfile
FROM node:24.11-alpine3.23
```

Fail:

```dockerfile
FROM node:latest
```

Pick the smallest base that can actually run the artefact:

| Workload | Preferred base |
|---|---|
| Compiled binaries (Go, Rust) | `gcr.io/distroless/static` or `scratch` |
| JVM (Spring Boot) | `gcr.io/distroless/java21` |
| Node.js | `node:24-alpine` |
| Python | `python:3.14-slim` |

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
[references/dockerfiles.md](references/dockerfiles.md).

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

This section is canonical for the repository. Other skills point here rather than restating it.

Scan every image in CI before it is pushed, and fail the build on a fixable critical or high finding:

```bash
trivy image --exit-code 1 --severity CRITICAL,HIGH myimage:tag
```

Store the scan report as a CI artifact, so a later question about what was known at release time has an answer.

Generate a Software Bill of Materials and attach it as an OCI referrer:

```bash
syft myimage:tag -o cyclonedx-json > sbom.json
```

Sign every production image after push:

```bash
cosign sign --key cosign.key myregistry/myimage:tag
```

Verify before deploy, in the pipeline, not by hand:

```bash
cosign verify --key cosign.pub myregistry/myimage:tag
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

---

### Reference files

| Open this | For |
|---|---|
| [references/dockerfiles.md](references/dockerfiles.md) | Full multi-stage Dockerfiles for Node, Go and Python, plus apt-get layering, OCI labels, and build-time secrets |
| [references/compose-and-debugging.md](references/compose-and-debugging.md) | A complete local stack, override files, network isolation, volume strategies, and the commands for debugging containers and networking |

---

### Related skills

- `deployment-patterns` for Kubernetes, rollout strategy, and the pipeline these images move through.
- `observability-and-logging` for the health, readiness, and log output the container emits.
- `bash` and `powershell` for entrypoint and healthcheck scripts.
- `ansible` for configuring the hosts the daemon runs on.
- `security-review` before shipping an image that handles credentials or faces the internet.

---

### Checklist

- [ ] Every base image pinned to a specific tag, never `:latest`.
- [ ] Build split into stages, dependency manifests copied before source.
- [ ] Runtime stage runs as a created non-root user.
- [ ] `HEALTHCHECK` declared.
- [ ] `.dockerignore` present next to the Dockerfile and excludes `.git`, `.env`, and tests.
- [ ] No secret in `ENV`, `ARG`, or a committed compose file.
- [ ] Named volumes only, no anonymous volume anywhere.
- [ ] Internal services on their own network, published ports bound to loopback or omitted.
- [ ] `cap_drop: [ALL]`, `no-new-privileges`, and a read-only root filesystem where the process allows it.
- [ ] Trivy scan gates the push, the report is archived, and an SBOM is generated.
- [ ] Production images are signed and the signature is verified by the deploy job.
- [ ] Registry retention enforced by a lifecycle policy.
