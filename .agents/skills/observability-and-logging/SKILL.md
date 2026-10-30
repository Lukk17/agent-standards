---
name: observability-and-logging
description: 'Structured logging and production observability: log levels, key-value fields, trace correlation, what liveness and readiness check, metrics, tracing, SLO alerts, and the startup readiness banner. Use when the user says "add logging to this service", "my logs have no trace id", or "alert on our error budget". Not for Kubernetes probe manifests or CI pipelines, use `deployment-patterns`.'
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
An expected, handled condition is not an error. Put every variable in a key-value field rather than in the message
text, so a pipeline can filter on it. Identify the service through the logger's resource (`service.name`), and let the
log appender attach `trace_id` and `span_id` from the active span, so one request can be followed across services.

Pass:

```java
log.atWarn().setMessage("payment declined, retrying").addKeyValue("orderId", orderId).addKeyValue("attempt", attempt).log();
```

Fail, the wrong level and nothing to filter on:

```java
log.error("payment declined");
```

---

### Never log a secret

Mask credentials, tokens, decrypted payloads, and personal data everywhere they could reach a log or a crash dump.

Pass:

```java
log.atInfo().setMessage("token issued").addKeyValue("subject", subject).addKeyValue("tokenSuffix", "***" + tokenSuffix).log();
```

Fail:

```java
log.info("token issued: {}", accessToken);
```

---

### Keep logging out of control flow

Logging is a side effect. Do not branch on a log call, and do not build an expensive message the logger may discard.

Pass:

```java
if (log.isDebugEnabled()) {
    log.atDebug().setMessage("cart snapshot").addKeyValue("snapshot", renderExpensiveSnapshot(cart)).log();
}
```

Fail:

```java
log.debug("cart snapshot=" + renderExpensiveSnapshot(cart));
```

The error-handling rules (specific exception types, chaining to preserve the cause, central handling, structured
error shape) live in the `coding-standards` hub. This skill covers how those errors are logged, not how they are
raised.

---

### Expose two separate health checks

Liveness reports only that the process is alive and never touches a dependency. Readiness reports what this
instance needs to serve: startup finished, pools open, and dependencies it does not share with other instances. A
shared dependency behind a circuit breaker or fallback stays out of readiness and shows up in metrics and alerts
instead, because when every instance checks it, one downstream failure takes every instance out of rotation at once
and turns a degraded service into a total outage. This skill owns that rule, and `api-design` and `backend-patterns`
point to it. Keep both outside the versioned API path, so a version bump cannot move the probe URL. The generic paths are `/health` and `/ready`, defined by
`api-design`. Spring Boot Actuator serves the same two checks under its own paths, shown below. This skill owns what
each endpoint reports. The probe manifests that point Kubernetes at them belong to `deployment-patterns`.

Pass:

```text
GET /actuator/health/liveness    200 while the process runs, touches no dependency
GET /actuator/health/readiness   200 once startup finished and this instance's own pools are open, 503 otherwise
```

Fail:

```text
GET /api/v1/health/full   one versioned endpoint that checks every shared dependency and answers both probes
```

---

### Emit metrics that drive action

Request rate, error rate, latency percentiles, and saturation of the resources that actually constrain the service.
Propagate W3C Trace Context (`traceparent`, `tracestate`) on every hop, and put `trace_id` and `span_id` on every log
record. Define SLOs in terms a user would recognise, a fast response or a
successful request, and alert on the SLO burn rate rather than every transient blip.

Pass:

```promql
sum(rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[5m])) / sum(rate(http_server_request_duration_seconds_count[5m]))
```

The series comes from the stable OpenTelemetry metric `http.server.request.duration` and its attribute
`http.response.status_code`. The exported name depends on the exporter's name translation, so check it against the
service's `/metrics` output before copying the query into an alert.

Fail:

```promql
process_cpu_seconds_total
```

---

### Emit one startup readiness block

Every long-running service prints one canonical multi-line INFO entry the moment it starts accepting traffic, in a
single log call with a leading newline. Per-line emission lets other threads interleave and rips the block apart.
The banner is for the text encoder. Under a JSON encoder the service emits one structured `service.ready` event with
the same fields instead, and either way a dependency URL is printed without its credentials or query string. The full
convention, the ANSI Shadow banner, the section order, the probe timeouts, and the per-stack hooks live in the
reference below.

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
- [ ] Variables are key-value fields, the service is named in the resource, and every record carries `trace_id`.
- [ ] No secret, credential, decrypted payload, or personal field reaches a log.
- [ ] Expensive message construction is guarded or lazy.
- [ ] Liveness and readiness are separate endpoints outside the versioned API path, and readiness leaves out shared
  dependencies that have a fallback.
- [ ] Rate, error, latency, and saturation metrics are exported and an SLO burn-rate alert exists.
- [ ] The startup readiness block is emitted in one log call with a leading newline.
