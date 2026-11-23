# Scope

Companion reference for the [observability-and-logging](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

The cross-cutting principles hub is the `coding-standards` skill, and this skill is the detailed playbook for the logging and observability rules it points to. It applies when:

- Adding or reviewing logging in a service.
- Instrumenting a service with health checks, metrics, or tracing.
- Defining SLOs, alerts, or dashboards.
- Writing the startup readiness banner.
- The user says "add logging to this service", "my logs have no trace id", "add a readiness endpoint", "alert on our error budget", or "print a startup banner when the app is up".

---

### When not to activate

- Building the CI/CD pipeline or the release gate that ships the service, use `deployment-patterns`.
- Writing the Kubernetes liveness, readiness, and startup probe manifests, use `deployment-patterns`.
- Designing timeouts, capped retries, circuit breakers, and graceful shutdown, use `backend-patterns`.
- Writing the Dockerfile or Compose file the service runs in, use `docker-patterns`.
- Chasing a specific slow endpoint or query with a profiler, use `performance-optimization`.
- Deciding how exceptions are raised, typed, and chained, use `coding-standards`.
- Writing shell or PowerShell logging helpers, use `bash` or `powershell`.

---

### Related skills

- `coding-standards` for the error-handling and design principles this skill logs against.
- `backend-patterns` for timeouts, capped retries, circuit breakers, and graceful shutdown.
- `deployment-patterns` for the probe manifests, rollout gating, and the pipeline that ships the service.
- `docker-patterns` for the container the service logs from.
- `performance-optimization` for turning a latency metric into a fix.
- `springboot-patterns`, `python-patterns`, `golang-patterns`, `node-backend-patterns` for the per-stack hook.
