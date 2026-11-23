# Rules and Examples

Contents:

- [Log through one abstraction](#log-through-one-abstraction)
- [Use levels that mean something](#use-levels-that-mean-something)
- [Never log a secret](#never-log-a-secret)
- [Keep logging out of control flow](#keep-logging-out-of-control-flow)
- [Expose two separate health checks](#expose-two-separate-health-checks)
- [Emit metrics that drive action](#emit-metrics-that-drive-action)
- [Emit one startup readiness block](#emit-one-startup-readiness-block)

Each logging, health, metrics and startup rule in SKILL.md in full, with its reasoning and its pass and fail forms. The Java and Spring Boot code is in [java-spring.md](java-spring.md) and the PromQL query in [prometheus.md](prometheus.md). Load this file when applying a rule and the one-line summary in SKILL.md is not enough.

---

### Log through one abstraction

Business code names a logger interface, never a concrete backend. Swapping the backend must not touch a call site.

Pass: the class holds a logger taken from the logging facade.

Fail: the class builds a logger from one backend's own context factory.

Code: [java-spring.md](java-spring.md#log-through-one-abstraction).

---

### Use levels that mean something

Informational for major steps, warning for recoverable trouble, error with the full stack trace for a real failure.
An expected, handled condition is not an error. Put every variable in a key-value field rather than in the message
text, so a pipeline can filter on it. Identify the service through the logger's resource (`service.name`), and let the
log appender attach `trace_id` and `span_id` from the active span, so one request can be followed across services.

Pass: a declined payment that is retried logs at warn, with the order identifier and the attempt as key-value fields.

Fail, the wrong level and nothing to filter on: the same event logs at error with a bare message.

Code: [java-spring.md](java-spring.md#use-levels-that-mean-something).

---

### Never log a secret

Mask credentials, tokens, decrypted payloads, and personal data everywhere they could reach a log or a crash dump.

Pass: a token-issued event logs the subject and a masked token suffix.

Fail: the same event logs the access token itself.

Code: [java-spring.md](java-spring.md#never-log-a-secret).

---

### Keep logging out of control flow

Logging is a side effect. Do not branch on a log call, and do not build an expensive message the logger may discard.

Pass: the expensive snapshot is rendered only inside a check that the debug level is enabled.

Fail: the snapshot is rendered and concatenated into a debug message that is then discarded.

Code: [java-spring.md](java-spring.md#keep-logging-out-of-control-flow).

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
`api-design`. Spring Boot Actuator serves the same two checks under its own paths, shown in
[java-spring.md](java-spring.md#health-checks-under-spring-boot-actuator). This skill owns what
each endpoint reports. The probe manifests that point Kubernetes at them belong to `deployment-patterns`.

Pass:

```text
GET /health   200 while the process runs, touches no dependency
GET /ready    200 once startup finished and this instance's own pools are open, 503 otherwise
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

Pass: the alert reads the share of failed requests over all requests.

Fail: the alert reads a process counter, such as CPU seconds, that no user feels.

The exported series name depends on the exporter's name translation, so check it against the service's `/metrics`
output before copying a query into an alert. The PromQL form of both, and the OpenTelemetry metric the series comes
from, are in [prometheus.md](prometheus.md).

---

### Emit one startup readiness block

Every long-running service prints one canonical multi-line INFO entry the moment it starts accepting traffic, in a
single log call with a leading newline. Per-line emission lets other threads interleave and rips the block apart.
The banner is for the text encoder. Under a JSON encoder the service emits one structured `service.ready` event with
the same fields instead, and either way a dependency URL is printed without its credentials or query string. The full
convention, the ANSI Shadow banner, the section order, the probe timeouts, and the per-stack hooks live in
[startup-readiness-log.md](startup-readiness-log.md).

Pass: the whole block is built first and logged in one call whose message starts with a newline.

Fail: the block is logged one line per call.

Code: [java-spring.md](java-spring.md#emit-one-startup-readiness-block).
