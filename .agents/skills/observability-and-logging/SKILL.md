---
name: observability-and-logging
description: Structured logging and production observability for services. Logging discipline (one abstraction, levels, correlation IDs, never log secrets), health and metrics and tracing, SLOs, resilient outbound calls (timeouts, retry with backoff, circuit breaker), graceful shutdown, and the canonical startup-readiness log. Use when adding logging, instrumenting a service, or making it operable in production.
---

# Observability and Logging

The operability layer every long-running service needs: how it logs, how it reports health, and how it survives a
failing dependency. The cross-cutting principles hub is the `coding-standards` skill; this skill is the detailed
playbook for the logging and observability rules it points to.

---

### When to activate

- Adding or reviewing logging in a service.
- Instrumenting a service with health checks, metrics, or tracing.
- Defining SLOs, alerts, or dashboards.
- Making outbound calls resilient (timeouts, retries, circuit breakers).
- Implementing graceful shutdown.
- Writing the startup-readiness log block (see the last section).

---

### Logging

- Log through a single logging abstraction, never a concrete logging backend in business code. Swapping the backend
  must not touch the call sites.
- Use structured logging with meaningful levels: informational for major steps, warning for recoverable trouble, and
  error with the full stack trace for failures. Do not log at error for an expected, handled condition.
- Begin each log line with a clear service or component tag, and carry a correlation or trace identifier so a single
  request can be followed end to end across services.
- Never log secrets, credentials, decrypted data, or personal data. Mask sensitive fields anywhere they could be
  printed or logged.
- Logging is a side effect, not control flow. Do not branch on a log call, and do not build a message the logger may
  never emit at that level when building it is expensive; guard it or let the logger evaluate lazily.

The error-handling rules (specific exception types, chaining to preserve the cause, central handling, structured
error shape) live in the `coding-standards` hub. This skill covers how those errors are logged, not how they are
raised.

---

### Observability

- Build in observability from the start. Every service exposes health, metrics, and tracing; they are not a later
  bolt-on.
- Expose two separate health checks. A liveness check reports only that the process is alive and never touches
  dependencies. A readiness check verifies the database, cache, and external dependencies and reports unhealthy when
  one is degraded. Keep both outside the versioned API path.
- Emit metrics that drive action: request rate, error rate, latency percentiles, and saturation of the resources that
  actually constrain the service. A dashboard nobody acts on is noise.
- Propagate a trace context across every hop so a slow request can be attributed to the span that caused it.
- Define SLOs in terms a user would recognise (a fast response, a successful request) and alert on the SLO burn rate,
  not on every transient blip.

---

### Resilient outbound calls

- Set a connect and read timeout on every outbound call. A call with no timeout is an outage waiting for a slow
  dependency.
- Retry a transient failure with exponential backoff and jitter, capped at a maximum delay and a maximum attempt
  count. Never retry a non-idempotent operation without an idempotency key.
- Add a circuit breaker where a dependency can fail for a sustained period, so a degraded dependency sheds load
  instead of exhausting the caller's threads and connections.
- Run independent outbound calls concurrently rather than one after another.

---

### Graceful shutdown

Handle shutdown deliberately: stop accepting new work, finish or cancel in-flight work, close connections and flush
buffers, then exit. Set a hard timeout as a backstop so a stuck task cannot block the shutdown forever.

---

### Startup readiness log

Every long-running service emits one canonical multi-line INFO log entry the moment it starts accepting traffic, not the
moment the process boots. Use the latest-possible startup hook for the framework. This single line is the most-read log
entry in any service: first thing on-call sees when paging, first thing CI inspects when smoke-testing, first thing a
new contributor sees when running locally. Investing in its clarity pays back every shift.

The log block contains, in order:

1. ASCII banner with the application name in ANSI Shadow FIGlet font (Unicode box-drawing: `█▀▄╔╗╚╝═║`). Width ~120
   chars, 6 lines. Modern terminals, container stdout, Loki, JsonEncoder-escaped JSON logs all render it. The bold
   weight makes "we're up" unmistakable when scrolling startup output. Do not use Standard / Big / Slant / Small / Block
   ASCII FIGlet: they pack too tightly to scan from a `kubectl logs` flood, and look indistinguishable from any other
   log line. Plain-ASCII fallback is acceptable only when the deployment target is a known UTF-8-hostile environment
   (legacy `cmd.exe`, embedded serial console).

   Generate the banner once at build time, paste it into a string constant. Do NOT compute it at runtime, do NOT have
   the agent "draw" it freehand (the agent will silently pick a different FIGlet font, usually Standard, every time).
   Use one of:

   - CLI: `figlet -f 'ANSI Shadow' 'EXAMPLE'`
   - Web: <https://patorjk.com/software/taag/#p=display&f=ANSI%20Shadow&t=EXAMPLE>

   This is the canonical look for the app name `EXAMPLE`:

   ```text
   ███████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██╗     ███████╗
   ██╔════╝╚██╗██╔╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝
   █████╗   ╚███╔╝ ███████║██╔████╔██║██████╔╝██║     █████╗
   ██╔══╝   ██╔██╗ ██╔══██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝
   ███████╗██╔╝ ██╗██║  ██║██║ ╚═╝ ██║██║     ███████╗███████╗
   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝
   ```

   Tells that the wrong font was used: the banner is ~3 lines tall instead of 6, uses `/ \ _ |` ASCII slashes instead of
   Unicode box-drawing, looks like `_ _____ _____ ____ ____` patterns, or fits inside a single 80-column line.
   Regenerate with the FIGlet font explicitly set to `ANSI Shadow`.
2. Access URLs: `Local: http://localhost:port/...` and `Hostname: http://<resolved-hostname>:port/...`. Both are
   diagnostic: in Kubernetes the real external URL comes from ingress / service definitions, not the app's self-report.
3. Active profile / environment: whatever the framework exposes (`local`, `docker`, `prod`, `staging`).
4. External dependencies: each one probed with a 2-second connect + read timeout so an unreachable dependency cannot
   stall the banner. Result format: `<url> [Connected | Warning (status=N) | FAILED]`: URL first, status marker last.
   Never include the exception detail in the banner; log it at `DEBUG` for diagnostics.
5. Observability endpoints: one URL per line: health / readiness / liveness / metrics / prometheus, plus OpenAPI /
   Swagger UI / tracing endpoint + sampling, plus the logging encoder mode by profile.

Canonical full output, what a real service should print when it accepts traffic. Match this layout precisely; omit
sections that don't apply (e.g. no `Auth` section if the service is unauthenticated), but keep the ones that do in this
order:

```text
███████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██╗     ███████╗
██╔════╝╚██╗██╔╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝
█████╗   ╚███╔╝ ███████║██╔████╔██║██████╔╝██║     █████╗
██╔══╝   ██╔██╗ ██╔══██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝
███████╗██╔╝ ██╗██║  ██║██║ ╚═╝ ██║██║     ███████╗███████╗
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝
----------------------------------------------------------
    Application 'example' is running!

    Access URLs:
      Local:     http://localhost:8080/example
      Hostname:  http://hostname:8080/example

    Profile(s): local

    Auth (OAuth2 Resource Server):
      Issuer:   https://keycloak.example/realms/main
      JWK Set:  https://keycloak.example/realms/main/protocol/openid-connect/certs [Connected]
      Roles:    @MainUser → hasAnyRole('USER','ADMIN')

    Service Discovery:
      Eureka:   [Disabled] (spring.cloud.discovery.enabled=false)

    Database:
      Postgres: jdbc:postgresql://db.internal:5432/example [Connected]

    Actuator:
      Health:     http://localhost:8080/example/actuator/health
      Readiness:  http://localhost:8080/example/actuator/health/readiness
      Prometheus: http://localhost:8080/example/actuator/prometheus
      Metrics:    http://localhost:8080/example/actuator/metrics

    API documentation:
      OpenAPI:    http://localhost:8080/example/openapi/v3/api-docs
      Swagger UI: http://localhost:8080/example/openapi/swagger-ui.html

    Observability:
      Tracing:  OTel bridge enabled, no OTLP endpoint set (sampling=1.0)
      Logging:  text pattern [traceId,spanId,jwt] (local/test profile)
----------------------------------------------------------
```

Format rules:

- Top and bottom separator: 58 dashes (`-` repeated). Same character, same count.
- 4-space indent for every line inside the block. Section labels are 1-indented (`    Section name:`), keys inside a
  section are 3-indented (`      Key: value`).
- Key column inside each section right-padded to 10-12 characters so values align vertically (`Local:     `,
  `Hostname:  `).
- Status markers in brackets at end of line: `[Connected]`, `[Warning (status=N)]`, `[FAILED]`, `[Disabled]`. Never
  include the exception detail in the banner; log it at DEBUG.
- Blank line between every section, no blank line inside a section.

#### Emit the whole block in ONE log call with a leading `\n`

The banner plus the readiness body must be a single log statement whose message starts with `\n`. The leading newline
pushes the first line of the banner (and every line after it) below the framework's prefix, so the banner art renders
cleanly from column 0.

Bad: one log call per line of the banner. Every line gets its own timestamp / level / logger prefix, which destroys the
art:

```text
2026-05-22 09:28:36.586 INFO  c.l.s.i.config.StartupLogConfig [Example] : ███████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██╗     ███████╗
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : ██╔════╝╚██╗██╔╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : █████╗   ╚███╔╝ ███████║██╔████╔██║██████╔╝██║     █████╗
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : ██╔══╝   ██╔██╗ ██╔══██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : ███████╗██╔╝ ██╗██║  ██║██║ ╚═╝ ██║██║     ███████╗███████╗
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝
```

Good: one log call, leading `\n`, banner art rendered cleanly underneath the single prefix line:

```text
2026-05-22 09:28:36.586 INFO  c.l.s.i.config.StartupLogConfig [Example] :
███████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██╗     ███████╗
██╔════╝╚██╗██╔╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝
█████╗   ╚███╔╝ ███████║██╔████╔██║██████╔╝██║     █████╗
██╔══╝   ██╔██╗ ██╔══██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝
███████╗██╔╝ ██╗██║  ██║██║ ╚═╝ ██║██║     ███████╗███████╗
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝
----------------------------------------------------------
    Application 'example' is running!
...
```

Stack-by-stack:

- Java / SLF4J: `log.info("\n{}", buildStartupLog());` (placeholder substitutes the entire string).
- Node / Pino / Winston: `logger.info('\n' + buildStartupLog())`.
- Python / `logging`: `logger.info("\n" + build_startup_log())`.
- Go / `slog`: `logger.Info("\n" + buildStartupLog())`.
- Bash / PowerShell: no framework prefix at all; `cat <<'EOF'` / `Write-Host` print directly to stdout.

Never split the banner across multiple log calls. Never call `println` / `fmt.Print` / `Write-Host` from inside a log
handler that adds a prefix per call.

Equally important: the builder must return one multi-line String. Building it via repeated `log.info(line)` calls is the
same bug from a different angle. Per-call emission is non-atomic, so other threads' logs (background pools, Axon
coordinators, scheduled jobs) can interleave between your readiness lines and rip the block apart visually.

Wrong (Java, per-line emission):

```java
log.info("----------------------------------------------------------");
log.info("    Application '{}' is running!", appName);
log.info("");
log.info("    Access URLs:");
log.info("      Local:     {}", localUrl);
log.info("      Hostname:  {}", hostnameUrl);
// ...one log call per line, each gets its own timestamp + level + logger prefix,
// and a Coordinator / scheduler / pool thread can log between any two of these.
```

Right (Java, build then emit once):

```java
String block = String.join("\n",
    "----------------------------------------------------------",
    "    Application '" + appName + "' is running!",
    "",
    "    Access URLs:",
    "      Local:     " + localUrl,
    "      Hostname:  " + hostnameUrl,
    // ... rest of sections
    "----------------------------------------------------------"
);
log.info("\n{}", block);
// One prefix line, the rest of the block flows under it at column 0. Atomic;
// nothing can interleave between sections.
```

Same shape for every framework: build the whole block first (StringBuilder, `String.join`, template literal, Python
f-string, Go `strings.Builder`), then emit once. If the builder needs to probe dependencies asynchronously, do that work
first, collect the results, then assemble the string, then log.

Pick the framework's "we're really up" hook from its own skill: [springboot-patterns](../springboot-patterns/SKILL.md),
[backend-patterns](../backend-patterns/SKILL.md), [python-patterns](../python-patterns/SKILL.md),
[golang-patterns](../golang-patterns/SKILL.md), [bash](../bash/SKILL.md), [powershell](../powershell/SKILL.md). The hook
differs per stack; the convention above is identical.
