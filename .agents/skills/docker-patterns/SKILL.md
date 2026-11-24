---
name: docker-patterns
description: 'Docker and Compose standards: multi-stage builds, pinned images, non-root users, secrets. Use when the user says "write a Dockerfile" or "set up compose for local dev". Not for Kubernetes, use `deployment-patterns`.'
metadata:
  version: "1.1.0"
---

# Docker Patterns

How a container image stays small, reproducible, and safe to run: a pinned base, a build split into stages, a non-root user, no secret baked into a layer, and a scan plus a signature before it is trusted anywhere. Compose then wires those images into a local stack that behaves like the real one.

Written for Docker Engine 29 and Docker Compose v5. The Compose v1 `docker-compose` command is gone, every command is `docker compose`.

| Task | Open |
|---|---|
| The Pass and Fail form and the reasoning behind a rule, or the base image table | [rules-and-examples.md](references/rules-and-examples.md) |
| A full multi-stage Dockerfile for Node.js, Go or Python | [node.md](references/node.md), [go.md](references/go.md), [python.md](references/python.md) |
| apt-get layering, OCI labels, and build-time secrets | [dockerfiles.md](references/dockerfiles.md) |
| A local Compose stack, override files, networks, volumes, debugging | [compose-and-debugging.md](references/compose-and-debugging.md) |
| The Trivy, syft and cosign commands | [supply-chain.md](references/supply-chain.md) |
| Before calling a change done | [checklist.md](references/checklist.md) |

---

### When not to activate

- Writing Kubernetes manifests, probes, or rollout strategy, use `deployment-patterns`.
- Configuring hosts rather than containers, use `ansible`.
- Writing the entrypoint script itself, use `bash` or `powershell`.

---

### Rules

1. Named volumes only. An anonymous volume cannot be backed up, targeted, inspected or shared, and outlives `docker compose down` as a dangling volume.
2. Build in stages and ship the last one. Copy dependency manifests before source, so a code change does not invalidate the dependency layer.
3. Never `:latest`, anywhere: not in a `FROM`, a compose `image:`, a variable default, a CI service or test image, or a tag you publish. Pin every image to an exact version tag plus `@sha256:<digest>`, and bump tag and digest together in a manual pull request, because a floating tag changes what runs without a commit.
4. Pick the smallest base that runs the artefact, from the base image table. Never `ubuntu:latest` or `debian:latest` at runtime.
5. Create a non-root user and switch to it with `USER` before the runtime stage ends, because a container escape from root is a host compromise. Declare a `HEALTHCHECK`.
6. Harden from Compose: no new privileges, a read-only root with `tmpfs` for writable paths, and every capability dropped, adding back only what is needed.
7. No secret in `ENV`, `ARG` or a committed compose file, since image history exposes both to anyone who can pull. Inject at runtime from the host environment or a Docker secret, keep `.env` gitignored, and use a secret mount at build time.
8. Put a database on its own network and bind published ports to loopback. Omit `ports` on internal production services, since service names resolve inside the network.
9. Ship a `.dockerignore` next to the Dockerfile, or the whole tree goes into the context and can copy `.env` and `.git` into a layer.
10. Keep the last 10 tagged releases and expire untagged images after 7 days, as a registry lifecycle policy, never a cleanup script or `docker system prune -a`.

---

### Supply chain: scan, bill of materials, signature

This section is canonical for the repository. Other skills point here rather than restating it.

1. Scan every image in CI before push, failing on a fixable critical or high finding, and store the report as a CI artifact.
2. Generate a bill of materials after push, and attach it to the pushed image as a signed attestation, so it travels with the image.
3. Sign every production image, and sign, attest and verify by the digest the push reported, never by tag, which can move between push and signature.
4. Verify the signature in the deploy job, gating it, never by hand, and have a cluster policy reject an unsigned image.
