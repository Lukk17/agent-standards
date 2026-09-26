---
name: observability-and-logging
description: Structured logging and production observability for services, covering log levels, correlation IDs, health checks, metrics, tracing, SLOs, and the startup readiness banner. Use when you say "add logging to this service", "my logs have no trace id", "add a readiness endpoint", "alert on our error budget", or "print a startup banner when the app is up". Not for CI/CD pipelines, release gating, or Kubernetes probe manifests, use `deployment-patterns`.
---

# Observability and Logging

The operability layer every long-running service needs: how it logs, how it reports health, and how its metrics
and traces show a failing dependency. The cross-cutting principles hub is the `coding-standards` skill, this skill
is the detailed playbook for the logging and observability rules it points to.

Baseline: OpenTelemetry is the reference instrumentation API for traces, metrics, and logs. Prometheus exposition is
the reference metrics format. Both are language-neutral, so pick the current stable SDK for your stack.

---

### When to activate

- Adding or reviewing logging in a service.
- Instrumenting a service with health checks, metrics, or tracing.
- Defining SLOs, alerts, or dashboards.
- Writing the startup readiness banner.

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

### Log through one abstraction

Business code names a logger interface, never a concrete backend. Swapping the backend must not touch a call site.

Pass:

```java
private static final Logger log = LoggerFactory.getLogger(OrderService.class);
```

Fail:

```java
private static final org.apache.logging.log4j.core.Logger log = new Log4jContextFactory().getContext().getLogger("x");
```

---

### Use levels that mean something

Informational for major steps, warning for recoverable trouble, error with the full stack trace for a real failure.
An expected, handled condition is not an error. Begin each line with a service or component tag and carry a
correlation or trace identifier so one request can be followed across services.

Pass:

```java
log.warn("[orders] payment declined, retrying, orderId={} attempt={}", orderId, attempt);
```

Fail:

```java
log.error("payment declined");
```

---

### Never log a secret

Mask credentials, tokens, decrypted payloads, and personal data everywhere they could reach a log or a crash dump.

Pass:

```java
log.info("[auth] token issued, subject={} tokenSuffix=***{}", subject, tokenSuffix);
```

Fail:

```java
log.info("[auth] token issued: {}", accessToken);
```

---

### Keep logging out of control flow

Logging is a side effect. Do not branch on a log call, and do not build an expensive message the logger may discard.

Pass:

```java
if (log.isDebugEnabled()) {
    log.debug("[cart] snapshot={}", renderExpensiveSnapshot(cart));
}
```

Fail:

```java
log.debug("[cart] snapshot=" + renderExpensiveSnapshot(cart));
```

The error-handling rules (specific exception types, chaining to preserve the cause, central handling, structured
error shape) live in the `coding-standards` hub. This skill covers how those errors are logged, not how they are
raised.

---

### Expose two separate health checks

Liveness reports only that the process is alive and never touches a dependency. Readiness verifies the database,
cache, and external dependencies and reports unhealthy when one is degraded. Keep both outside the versioned API
path, so a version bump cannot move the probe URL. The generic paths are `/health` and `/ready`, defined by
`api-design`. Spring Boot Actuator serves the same two checks under its own paths, shown below. This skill owns what
each endpoint reports. The probe manifests that point Kubernetes at them belong to `deployment-patterns`.

Pass:

```text
GET /actuator/health/liveness    200 while the process runs, touches no dependency
GET /actuator/health/readiness   200 when the database, cache, and downstream services answer, 503 otherwise
```

Fail:

```text
GET /api/v1/health/full   one versioned endpoint that checks every dependency and answers both probes
```

---

### Emit metrics that drive action

Request rate, error rate, latency percentiles, and saturation of the resources that actually constrain the service.
Propagate a trace context across every hop. Define SLOs in terms a user would recognise, a fast response or a
successful request, and alert on the SLO burn rate rather than every transient blip.

Pass:

```promql
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))
```

Fail:

```promql
process_cpu_seconds_total
```

---

### Emit one startup readiness block

Every long-running service prints one canonical multi-line INFO entry the moment it starts accepting traffic, in a
single log call with a leading newline. Per-line emission lets other threads interleave and rips the block apart.
The full convention, the ANSI Shadow banner, the section order, the probe timeouts, and the per-stack hooks live in
the reference below.

Pass:

```java
log.info("\n{}", buildStartupLog());
```

Fail:

```java
buildStartupLog().lines().forEach(log::info);
```

---

### Reference files

| Open this | For |
|---|---|
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
- [ ] Every log line carries a component tag and a correlation or trace identifier.
- [ ] No secret, credential, decrypted payload, or personal field reaches a log.
- [ ] Expensive message construction is guarded or lazy.
- [ ] Liveness and readiness are separate endpoints outside the versioned API path.
- [ ] Rate, error, latency, and saturation metrics are exported and an SLO burn-rate alert exists.
- [ ] The startup readiness block is emitted in one log call with a leading newline.
