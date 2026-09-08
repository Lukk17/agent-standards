# Multi-stage Dockerfiles

Reference Dockerfiles for the runtimes this repository's skills cover, plus the layer-level rules that apply to all
of them. The container rules themselves live in [SKILL.md](../SKILL.md).

Every image below pins a specific tag, builds in stages, drops to a non-root user before the runtime stage ends, and
declares a `HEALTHCHECK`.

---

### Node.js, development and production from one file

```dockerfile
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS dev
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build && npm prune --production

FROM node:24-alpine AS production
WORKDIR /app
RUN addgroup -g 1001 -S appgroup && adduser -S appuser -u 1001
USER appuser
COPY --from=build --chown=appuser:appgroup /app/dist ./dist
COPY --from=build --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=build --chown=appuser:appgroup /app/package.json ./
ENV NODE_ENV=production
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/server.js"]
```

The `dev` stage exists so Compose can target it with `build.target: dev` and get hot reload, while production builds
target `production` from the same file. Two Dockerfiles drift, one file with two stages cannot.

---

### Go

```dockerfile
FROM golang:1.27-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /server ./cmd/server

FROM alpine:3.23 AS runner
RUN apk --no-cache add ca-certificates
RUN adduser -D -u 1001 appuser
USER appuser
COPY --from=builder /server /server
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:8080/health || exit 1
CMD ["/server"]
```

`CGO_ENABLED=0` produces a static binary, which is what lets the runtime stage be Alpine or, better still,
`gcr.io/distroless/static`. Adding `ca-certificates` is the one thing a scratch or distroless-static image still
needs for outbound TLS.

---

### Python

```dockerfile
FROM python:3.14-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

FROM python:3.14-slim AS runner
WORKDIR /app
RUN useradd -r -u 1001 appuser
USER appuser
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

The `site-packages` path carries the minor version, so it changes when the base image's minor version does. Bump
both lines together or the copy silently produces an image with no dependencies installed.

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
