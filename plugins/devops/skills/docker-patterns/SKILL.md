---
name: docker-patterns
description: Docker and Compose standards for multi-stage builds, pinned base images, non-root users, network isolation, secrets, and the Trivy, SBOM and cosign supply-chain gate. Use when the user says "write a Dockerfile for this service", "set up compose for local dev", "shrink this image" or "scan and sign this image". Not for Kubernetes manifests and rollout strategy, use `deployment-patterns`.
---

# Docker Patterns

How a container image stays small, reproducible, and safe to run: a pinned base, a build split into stages, a non-root user, no secret baked into a layer, and a scan plus a signature before it is trusted anywhere. Compose then wires those images into a local stack that behaves like the real one.

Written for Docker Engine 29 and Docker Compose v5. The Compose v1 `docker-compose` command is gone, every command is `docker compose`.

| Task | Open |
|---|---|
| The Pass and Fail form, the commands, and the reasoning behind any rule below, including the base image table | [references/rules-and-examples.md](references/rules-and-examples.md) |
| Full multi-stage Dockerfiles for Node, Go and Python, plus apt-get layering, OCI labels, and build-time secrets | [references/dockerfiles.md](references/dockerfiles.md) |
| A complete local stack, override files, network isolation, volume strategies, and debugging containers and networking | [references/compose-and-debugging.md](references/compose-and-debugging.md) |

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

### Rules

1. Named volumes only. An anonymous volume (`- /app/node_modules`) cannot be backed up, targeted, inspected or shared, survives `docker compose down` as a dangling volume, and in production ties data to a container lifecycle.
2. Build in stages and ship the last one, keeping compilers, dev dependencies and build caches out. Copy dependency manifests before source, so a code change does not invalidate the dependency layer.
3. Never `:latest`. Pin a tag naming the runtime version and OS variant plus `@sha256:<digest>`, read with `docker buildx imagetools inspect <image>:<tag>`, and let Dependabot or Renovate bump tag and digest together.
4. Pick the smallest base that runs the artefact: distroless `static` or `scratch` for Go and Rust, distroless `java25` for the JVM, `node:26-alpine`, `python:3.14-slim`. Distroless has no version tags, so its pin is the Debian suffix plus a digest. Never `ubuntu:latest` or `debian:latest` at runtime.
5. Create a non-root user and switch to it with `USER` before the runtime stage ends, because a container escape from root is a host compromise. Declare a `HEALTHCHECK`.
6. Harden from Compose: `no-new-privileges:true`, `read_only: true` with `tmpfs` for writable paths, `cap_drop: [ALL]`, adding back only what is needed. `NET_BIND_SERVICE` is only for a port below 1024, so listen high and drop it too.
7. No secret in `ENV`, `ARG` or a committed compose file, since image history exposes both to anyone who can pull. Inject at runtime with `environment: - API_KEY` (inherits from the host) or a Docker secret, keep `.env` gitignored, and use `--mount=type=secret` at build time.
8. Put a database on its own network and bind published ports to loopback (`127.0.0.1:5432:5432`). Omit `ports` on internal production services, since service names resolve inside the network.
9. Ship a `.dockerignore` next to the Dockerfile excluding at least `node_modules`, build output, logs, `.git`, `.env*`, coverage and tests, or the whole tree goes into the context and can copy `.env` and `.git` into a layer.
10. Keep the last 10 tagged releases and expire untagged images after 7 days, as a registry lifecycle policy, never a cleanup script or `docker system prune -a`.

---

### Supply chain: scan, bill of materials, signature

This section is canonical for the repository. Other skills point here rather than restating it. The commands are in [references/rules-and-examples.md](references/rules-and-examples.md).

1. Scan every image in CI before push with `trivy image --exit-code 1 --severity CRITICAL,HIGH`, failing on a fixable critical or high finding, and store the report as a CI artifact.
2. Generate a CycloneDX SBOM with `syft` after push, and attach it to the pushed image as a signed attestation with `cosign attest`, so it travels with the image.
3. Sign every production image with `cosign sign`, and sign, attest and verify by the digest the push reported, never by tag, which can move between push and signature. The pipeline form is in `deployment-patterns`.
4. Verify with `cosign verify` in the deploy job, gating it, never by hand, and have a cluster policy reject an unsigned image. A signature nothing verifies proves nothing.

---

### Related skills

- `deployment-patterns` for Kubernetes, rollout strategy, and the pipeline these images move through.
- `observability-and-logging` for the health, readiness, and log output the container emits.
- `bash` and `powershell` for entrypoint and healthcheck scripts.
- `ansible` for configuring the hosts the daemon runs on.
- `security-review` before shipping an image that handles credentials or faces the internet.

---

### Checklist

- [ ] Every base image pinned to a specific tag plus its digest, never `:latest`.
- [ ] Build split into stages, dependency manifests copied before source.
- [ ] Runtime stage runs as a created non-root user.
- [ ] `HEALTHCHECK` declared.
- [ ] `.dockerignore` present next to the Dockerfile and excludes `.git`, `.env`, and tests.
- [ ] No secret in `ENV`, `ARG`, or a committed compose file.
- [ ] Named volumes only, no anonymous volume anywhere.
- [ ] Internal services on their own network, published ports bound to loopback or omitted.
- [ ] `cap_drop: [ALL]`, `no-new-privileges`, and a read-only root filesystem where the process allows it.
- [ ] Trivy scan gates the push, the report is archived, and an SBOM is generated and attested to the image.
- [ ] Production images are signed by digest and the signature is verified by the deploy job.
- [ ] Registry retention enforced by a lifecycle policy.
