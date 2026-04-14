# Docker Standards

Applies to all Dockerfiles and Docker Compose configurations. Universal rules in `universal-coding-standards.md` apply in addition to these.

> **Note for AI agents**: Never run `docker` commands directly. Present the command to the user and ask them to run it.

---

## Image Versioning

- Never use `latest` tags for base images. Always pin to a specific version (e.g., `eclipse-temurin:21.0.3_9-jre-jammy`).
- Verify the current stable version from the official registry or documentation before pinning.
- Update pinned versions intentionally, not automatically.

---

## Multi-Stage Builds

Always use multi-stage builds for compiled languages to minimize the final image size:

```dockerfile
# Stage 1 — build
FROM eclipse-temurin:21-jdk AS builder
WORKDIR /app
COPY . .
RUN ./gradlew bootJar --no-daemon

# Stage 2 — runtime
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=builder /app/build/libs/app.jar app.jar
```

The runtime stage must not contain build tools, source code, or test dependencies.

---

## Security

- Never run processes as root inside a container. Create a dedicated non-root user:
  ```dockerfile
  RUN groupadd --system appgroup && useradd --system --gid appgroup appuser
  USER appuser
  ```
- Never bake secrets (API keys, passwords, certificates) into images. Use runtime environment variables or secret mounts (`--mount=type=secret`).
- Minimize the number of installed packages in the runtime stage.
- Use `--no-install-recommends` for `apt-get install` to reduce attack surface.

---

## Health Checks

Every service image must declare a `HEALTHCHECK`:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1
```

---

## .dockerignore

Every project with a Dockerfile must have a `.dockerignore` file that excludes:
- `.git/`
- `node_modules/`
- `build/`, `dist/`, `target/`
- `*.log`
- `.env` files
- Test files and directories

---

## Docker Compose

- Use named volumes for persistent data; never use anonymous volumes.
- Define `depends_on` with `condition: service_healthy` when a service depends on another being ready.
- Extract all configurable values to a `.env` file referenced in `compose.yaml`; never hardcode values in `compose.yaml`.
- Use `compose.yaml` (not `docker-compose.yml`) as per the current Compose specification.
- Pin specific image versions in `compose.yaml` the same as in Dockerfiles.

---

## Layer Optimization

- Order Dockerfile instructions from least to most frequently changed to maximize cache reuse.
- Copy dependency manifests and install dependencies before copying application source code.
- Combine related `RUN` commands with `&&` to minimize layer count.
