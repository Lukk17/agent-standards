# Go Dockerfile

The reference multi-stage Dockerfile for a Go service, on a distroless runtime stage. Like every image in this skill, it pins a specific tag plus its digest, with `<digest>` standing in for the value `docker buildx imagetools inspect <image>:<tag>` prints, builds in stages, drops to a non-root user before the runtime stage ends, and declares a `HEALTHCHECK`. The container rules live in [SKILL.md](../SKILL.md), and the layer rules every Dockerfile shares, apt-get layering, OCI labels and build-time secrets, are in [dockerfiles.md](dockerfiles.md).

---

### Static binary on distroless

```dockerfile
FROM golang:1.27-alpine@sha256:<digest> AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /server ./cmd/server

FROM gcr.io/distroless/static-debian13:nonroot@sha256:<digest> AS runner
COPY --from=builder /server /server
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD ["/server", "healthcheck"]
ENTRYPOINT ["/server"]
```

`CGO_ENABLED=0` produces a static binary, which is what lets the runtime stage be `distroless/static`. That image
already carries CA certificates and tzdata, and the `nonroot` tag runs as an unprivileged user, so no `USER` line is
needed. It has no shell and no `wget`, so `ENTRYPOINT` and `HEALTHCHECK` use the exec form, and the health check calls
a `healthcheck` subcommand the server implements as a probe of its own `/health` endpoint. On `scratch`, copy
`/etc/ssl/certs/ca-certificates.crt` from the builder for outbound TLS and add a `USER` line.
