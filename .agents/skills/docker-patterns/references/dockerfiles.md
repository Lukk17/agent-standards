# Dockerfile layer rules

The layer-level rules that apply to every Dockerfile, whatever the runtime. The container rules themselves live in [SKILL.md](../SKILL.md), and the full reference Dockerfile for each runtime is in [node.md](node.md), [go.md](go.md) and [python.md](python.md).

Every image in those files pins a specific tag plus its digest, with `<digest>` standing in for the value `docker buildx imagetools inspect <image>:<tag>` prints, builds in stages, drops to a non-root user before the runtime stage ends, and declares a `HEALTHCHECK`.

---

### Contents

- [apt-get in one layer](#apt-get-in-one-layer)
- [OCI image labels](#oci-image-labels)
- [Build-time secrets](#build-time-secrets)

---

### apt-get in one layer

Install and clean in a single `RUN`, or the cleanup lands in a later layer and the package lists stay in the image.

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

---

### OCI image labels

Every published image carries the labels that let a running container be traced back to a commit.

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}"
```

---

### Build-time secrets

Use a secret mount, never `ARG` or `ENV`. Both persist in the image history and can be read back out of a published
image.

```dockerfile
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) npm install
```

Pass it at build time:

```bash
docker build --secret id=npm_token,src=.npmrc .
```
