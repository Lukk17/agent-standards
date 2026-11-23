# Scope

Companion reference for the [docker-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing a Dockerfile or a Compose file.
- Setting up or debugging a local multi-service development stack.
- Shrinking an image, or fixing one that rebuilds everything on every change.
- Hardening a container: user, capabilities, filesystem, secrets.
- Adding image scanning, an SBOM, or signing to a pipeline.
- Diagnosing container networking, DNS, or volume behaviour.
- The user says "write a Dockerfile for this service", "set up compose for local dev", "shrink this image" or "scan and sign this image".

---

### When not to activate

- Writing Kubernetes manifests, probes, or rollout strategy, use `deployment-patterns`.
- Configuring hosts rather than containers, use `ansible`.
- Writing the entrypoint script itself, use `bash` or `powershell`.
- Instrumenting the application inside the container, use `observability-and-logging`.
- Reviewing the application's own authentication or input handling, use `application-security-review`.

---

### Related skills

- `deployment-patterns` for Kubernetes, rollout strategy, and the pipeline these images move through.
- `observability-and-logging` for the health, readiness, and log output the container emits.
- `bash` and `powershell` for entrypoint and healthcheck scripts.
- `ansible` for configuring the hosts the daemon runs on.
- `application-security-review` before shipping an image that handles credentials or faces the internet.
