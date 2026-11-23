---
name: observability-and-logging
description: 'Structured logging and observability: log levels, trace ids, health checks, metrics, SLO alerts, startup banner. Use when the user says "add logging to this service". Not for probe manifests, use `deployment-patterns`.'
metadata:
  version: "1.1.0"
---

# Observability and Logging

The operability layer every long-running service needs: how it logs, how it reports health, and how its metrics and traces show a failing dependency. Baseline: the OpenTelemetry 1.x API and SDKs for traces, metrics and logs, and Prometheus exposition for metrics, both language-neutral.

---

### When not to activate

- Kubernetes probe manifests, or the CI/CD pipeline and release gate that ship the service, use `deployment-patterns`.
- Timeouts, capped retries, circuit breakers and graceful shutdown, use `backend-patterns`.
- Chasing a specific slow endpoint or query with a profiler, use `performance-optimization`.

---

### Rules

1. Log through one abstraction. Business code names a logger interface, never a concrete backend, so swapping the backend touches no call site.
2. Use levels that mean something: info for major steps, warn for recoverable trouble, error with the full stack trace for a real failure, never error for an expected, handled condition. Every variable goes in a key-value field, the service is named by the resource's `service.name`, and the appender attaches `trace_id` and `span_id` from the active span.
3. Never log a secret. Mask credentials, tokens, decrypted payloads and personal data wherever they could reach a log or a crash dump.
4. Keep logging out of control flow. Never branch on a log call, and guard or defer an expensive message the logger may discard.
5. Expose two separate health checks, outside the versioned API path. Liveness touches no dependency. Readiness reports what this instance needs: startup finished, pools open, unshared dependencies. A shared dependency behind a breaker or fallback stays out of readiness and shows in metrics, or one downstream failure pulls every instance. This skill owns that rule. `api-design` defines `/health` and `/ready`, Spring Boot Actuator serves its own paths, and `deployment-patterns` owns the probe manifests.
6. Emit metrics that drive action: request rate, error rate, latency percentiles, saturation of the constraining resources. Propagate W3C Trace Context (`traceparent`, `tracestate`) on every hop, define SLOs in user terms, and alert on burn rate.
7. Emit one startup readiness block, the moment the service accepts traffic, in a single INFO call with a leading newline. Under a JSON encoder it is one structured `service.ready` event with the same fields, and a dependency URL prints without credentials or query string.

---

### Reference files

| Open this | For |
|---|---|
| [rules-and-examples.md](references/rules-and-examples.md) | A rule above in full, with its reasoning and its pass and fail form |
| [java-spring.md](references/java-spring.md) | Java with SLF4J or Spring Boot: the log call forms, the Actuator health paths, the startup hook |
| [prometheus.md](references/prometheus.md) | A PromQL alert query, its OpenTelemetry source metric, the exported series name |
| [startup-readiness-log.md](references/startup-readiness-log.md) | The startup readiness banner: its layout, probe rules and the emission hook per stack |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job |
| [checklist.md](references/checklist.md) | Before calling the work done |
