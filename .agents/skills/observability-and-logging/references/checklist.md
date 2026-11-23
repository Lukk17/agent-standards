# Observability and Logging Checklist

Run it before calling a logging, health, metrics or startup banner change done.

- [ ] Business code logs through one abstraction, no concrete backend at a call site.
- [ ] Variables are key-value fields, the service is named in the resource, and every record carries `trace_id`.
- [ ] No secret, credential, decrypted payload, or personal field reaches a log.
- [ ] Expensive message construction is guarded or lazy.
- [ ] Liveness and readiness are separate endpoints outside the versioned API path, and readiness leaves out shared dependencies that have a fallback.
- [ ] Rate, error, latency, and saturation metrics are exported and an SLO burn-rate alert exists.
- [ ] The startup readiness block is emitted in one log call with a leading newline.
