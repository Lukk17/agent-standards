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
- Extract all configurable values to a `.env` file referenced in `docker-compose.yaml`; never hardcode values in `docker-compose.yaml`.
- Use `docker-compose.yaml`.
- Pin specific image versions in `docker-compose.yaml` the same as in Dockerfiles.

---

## Layer Optimization

- Order Dockerfile instructions from least to most frequently changed to maximize cache reuse.
- Copy dependency manifests and install dependencies before copying application source code.
- Combine related `RUN` commands with `&&` to minimize layer count.

---

## Image Scanning

- Run **Trivy** (`trivy image`) on every built image in CI before pushing to any registry.
- Block the push and deployment pipeline if the scan finds any `CRITICAL` or `HIGH` severity CVE that has an available fix.
- Store the scan report as a CI artifact for audit purposes.

---

## SBOM Generation

- Generate a Software Bill of Materials (SBOM) in **CycloneDX** or **SPDX** format for every published image using `syft` or `docker buildx build --sbom=true`.
- Attach the SBOM as an OCI artifact referrer to the image manifest in the registry.
- Store the SBOM as a CI build artifact alongside the scan report.

---

## Container Signing

- Sign every image pushed to a production registry using **cosign** (Sigstore):
  ```bash
  cosign sign --key cosign.key registry/image:tag
  ```
- Verify the signature in the deployment pipeline before pulling the image:
  ```bash
  cosign verify --key cosign.pub registry/image:tag
  ```
- Use keyless signing (OIDC-based) for CI environments that support it (GitHub Actions, GitLab CI).

---

## Preferred Base Images

- For compiled languages (Java, Go, Rust), prefer **distroless** (`gcr.io/distroless/...`) or **scratch** base images for the runtime stage to minimise the attack surface.
- For interpreted languages (Python, Node.js) that require a shell or package manager at runtime, use official `-slim` or `-alpine` variants.
- Never use generic `ubuntu:latest` or `debian:latest` as a runtime base; always use the smallest viable image.

---

## OCI Image Labels

- Every published image must include standard OCI annotations:
  ```dockerfile
  LABEL org.opencontainers.image.title="my-service"
  LABEL org.opencontainers.image.version="1.2.3"
  LABEL org.opencontainers.image.source="https://github.com/org/repo"
  LABEL org.opencontainers.image.revision="<git-sha>"
  LABEL org.opencontainers.image.created="<build-timestamp>"
  ```

---

## Registry Retention Policy

- Define a tag retention policy in the container registry: keep the last 10 tagged releases and all tags matching `v*.*.*`; automatically delete untagged (dangling) images after 7 days.
- Never accumulate unlimited untagged images; they consume storage and obscure the image history.
