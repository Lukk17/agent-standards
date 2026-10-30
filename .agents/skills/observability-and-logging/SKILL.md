---
name: observability-and-logging
description: 'Structured logging and production observability: log levels, key-value fields, trace correlation, what liveness and readiness check, metrics, tracing, SLO alerts, and the startup readiness banner. Use when the user says "add logging to this service", "my logs have no trace id", or "alert on our error budget". Not for Kubernetes probe manifests or CI pipelines, use `deployment-patterns`.'
---

# Observability and Logging

The operability layer every long-running service needs: how it logs, how it reports health, and how its metrics
and traces show a failing dependency. The cross-cutting principles hub is the `coding-standards` skill, this skill
is the detailed playbook for the logging and observability rules it points to.

Baseline: OpenTelemetry is the reference instrumentation API for traces, metrics, and logs. Prometheus exposition is
the reference metrics format. Both are language-neutral. Written for the OpenTelemetry 1.x API and SDKs.

---

### When to activate

- Adding or reviewing logging in a service.
- Instrumenting a service with health checks, metrics, or tracing.
- Defining SLOs, alerts, or dashboards.
- Writing the startup readiness banner.
- The user says "add logging to this service", "my logs have no trace id", "add a readiness endpoint", "alert on our
  error budget", or "print a startup banner when the app is up".

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

### Rules

1. Log through one abstraction. Business code names a logger interface, never a concrete backend, so swapping the backend touches no call site.
2. Use levels that mean something: info for major steps, warn for recoverable trouble, error with the full stack trace for a real failure, never error for an expected, handled condition. Every variable goes in a key-value field, the service is named by the resource's `service.name`, and the appender attaches `trace_id` and `span_id` from the active span.
3. Never log a secret. Mask credentials, tokens, decrypted payloads and personal data wherever they could reach a log or a crash dump.
4. Keep logging out of control flow. Never branch on a log call, and guard or defer an expensive message the logger may discard. How errors are raised, typed and chained is `coding-standards`; this skill covers how they are logged.
5. Expose two separate health checks, outside the versioned API path. Liveness touches no dependency. Readiness reports what this instance needs: startup finished, pools open, unshared dependencies. A shared dependency behind a breaker or fallback stays out of readiness and shows in metrics, or one downstream failure pulls every instance. This skill owns that rule; `api-design` defines `/health` and `/ready`, Spring Boot Actuator serves its own paths, and `deployment-patterns` owns the probe manifests.
6. Emit metrics that drive action: request rate, error rate, latency percentiles, saturation of the constraining resources. Propagate W3C Trace Context (`traceparent`, `tracestate`) on every hop, define SLOs in user terms, and alert on burn rate. Check the exported series name against the service's `/metrics` before writing the alert.
7. Emit one startup readiness block, the moment the service accepts traffic, in a single INFO call with a leading newline. Under a JSON encoder it is one structured `service.ready` event with the same fields, and a dependency URL prints without credentials or query string.

---

### Reference files

| Open this | For |
|---|---|
| [references/rules-and-examples.md](references/rules-and-examples.md) | Applying a rule above: its reasoning, the Actuator paths, the PromQL query and its OpenTelemetry source metric, and pass and fail forms |
| [references/startup-readiness-log.md](references/startup-readiness-log.md) | Writing or reviewing the startup readiness banner, its layout, probe rules, and per-stack emission hooks |

---

### Related skills

- `coding-standards` for the error-handling and design principles this skill logs against.
- `backend-patterns` for timeouts, capped retries, circuit breakers, and graceful shutdown.
- `deployment-patterns` for the probe manifests, rollout gating, and the pipeline that ships the service.
- `docker-patterns` for the container the service logs from.
- `performance-optimization` for turning a latency metric into a fix.
- `springboot-patterns`, `python-patterns`, `golang-patterns`, `node-backend-patterns` for the per-stack hook.

---

### Checklist

- [ ] Business code logs through one abstraction, no concrete backend at a call site.
- [ ] Variables are key-value fields, the service is named in the resource, and every record carries `trace_id`.
- [ ] No secret, credential, decrypted payload, or personal field reaches a log.
- [ ] Expensive message construction is guarded or lazy.
- [ ] Liveness and readiness are separate endpoints outside the versioned API path, and readiness leaves out shared
  dependencies that have a fallback.
- [ ] Rate, error, latency, and saturation metrics are exported and an SLO burn-rate alert exists.
- [ ] The startup readiness block is emitted in one log call with a leading newline.
