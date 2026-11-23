# Alert Queries in PromQL

The Prometheus form of the metrics rule: an error-ratio query worth alerting on, the OpenTelemetry metric its series comes from, and the check of the exported name. Open this when writing a PromQL alert or a dashboard query. The rule itself is under "Emit metrics that drive action" in [rules-and-examples.md](rules-and-examples.md).

---

### An error ratio that drives action

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
