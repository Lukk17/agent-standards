# Universal Coding Standards

Applies to all languages and frameworks. Language-specific standards files do not repeat these rules.

---

## Design Principles

Follow KISS, SOLID, and DRY in every implementation.

Never implement a "quick fix" or patch that relies on hardcoded values or bypasses architectural standards. If a fix requires configuration, implement the full configuration layer immediately. Temporary code is forbidden.

Ensure solutions are long-term, not duct-tape fixes.

---

## Clean Code

### Naming
- Variable and method names must be descriptive (e.g., `calculateTotalRevenue`, not `calc`).
- Boolean variables must start with `is`, `has`, or `can`.
- Never use magic numbers; extract them to properly named constants or application properties.

### Comments
- Comments are allowed only where logic is genuinely non-obvious and cannot be made self-explanatory by extraction or renaming.
- Do not add comments that merely restate what the code does.
- Do not add docstrings or documentation to code you did not change.

### Structure
- Public methods must be concise; extract complex logic into private helpers.
- Avoid deep nesting (arrow code); use guard clauses and early returns.
- Never use fully qualified names; use imports.

---

## Error Handling

- Use global exception handlers instead of local try-catch blocks scattered across methods.
- Extract complicated error handling logic to separate, named methods.
- Implement fail-fast validation at method entry points for external inputs.
- Only validate at system boundaries (user input, external APIs). Do not add validation for scenarios that cannot happen.

---

## Security (OWASP Top 10)

- Validate and sanitize all user input at system boundaries.
- Never store secrets (API keys, passwords, tokens) in source code or committed files.
- Prevent injection vulnerabilities: SQL injection, command injection, XSS.
- Use parameterized queries for all database interactions.
- Apply principle of least privilege for all service accounts and roles.
- Use only trusted dependencies; audit third-party packages before adding them.

---

## General Constraints

- Do not add features, refactor code, or make improvements beyond what was explicitly requested.
- Do not add error handling for scenarios that cannot occur.
- Do not create helpers, utilities, or abstractions for one-time operations.
- Do not design for hypothetical future requirements (YAGNI).
- Extract configuration to environment variables or config files; never hardcode environment-specific values.

---

## Logging

- Use structured logging (JSON format) in all production services. Never use plain concatenated strings as log messages.
- Log levels: `ERROR` for unhandled exceptions and data integrity issues; `WARN` for recoverable problems and deprecations; `INFO` for significant business events (request received, job completed); `DEBUG` for diagnostic detail (disabled in production by default).
- Every log entry on a request path must include a `correlationId` / `traceId` to allow cross-service tracing.
- Never log: passwords, tokens, full credit card numbers, personal identification numbers, or any secret material.
- Do not use `print` / `console.log` for operational output in any language; use the project's configured logging framework.

---

## Observability

- Expose a `/metrics` endpoint (Prometheus format) on all HTTP services.
- Instrument all external I/O (database calls, HTTP requests, queue publishes) with duration histograms and error counters.
- Propagate trace context headers (`traceparent` per W3C Trace Context spec) on all outbound HTTP calls.
- Use OpenTelemetry SDK as the default instrumentation library; do not use vendor-specific SDKs that cannot be swapped.
- Every service must expose a health endpoint (`/health` or `/healthz`) that reflects real readiness (DB connection live, dependencies reachable).

---

## Performance

- Never load an unbounded collection into memory; always paginate or stream large result sets.
- Detect and eliminate N+1 query patterns: use batch loading, joins, or DataLoader patterns instead.
- Avoid blocking I/O on threads that serve synchronous requests; use async I/O or offload to a worker pool.
- Profile before optimising: do not add caching or concurrency complexity without a measured baseline showing a problem.

---

## Dependency Management

- Before adding a new dependency, verify: active maintenance (commit in last 6 months), permissive licence (MIT, Apache-2.0, BSD), no known critical CVEs.
- Prohibited licence types: GPL, AGPL, LGPL (unless legal has approved). Copyleft licences must not appear in production artefacts.
- Pin dependency versions in lock files (`package-lock.json`, `poetry.lock`, `gradle.lockfile`). Never use unbounded version ranges in production.
- Run a Software Composition Analysis (SCA) scan (e.g., `npm audit`, `pip-audit`, OWASP Dependency-Check) in CI on every PR.

---

## Code Review

- Every change to a shared codebase requires at minimum one peer review approval before merging.
- Reviewers must verify: correctness, standards compliance, test coverage, and absence of security issues — not just style.
- Review comments marked `blocking` must be resolved before merge. Comments marked `nit` may be deferred.
- The author must not merge their own PR without at least one external approval.
