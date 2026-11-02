---
name: security-review
description: 'Application security review: secrets, input validation, injection, authentication and sessions, authorization with row-level security, XSS and CSP, CSRF, rate-limit policy, data exposure, and dependency risk. Use when the user says "review this endpoint before it ships", "is this file upload safe", or "check this for injection". Not for container and image hardening, use `docker-patterns`.'
---

# Security Review

Check application code against the failure modes that actually cause incidents, with a concrete pass and fail for each.
This skill covers the application layer. Cloud and platform hardening live in the references, container hardening
lives in `docker-patterns`, and the `security-auditor` agent takes over for threat modelling and a full assessment.

---

### When to activate

- Adding or changing authentication, session handling, or authorization.
- Creating an API endpoint, especially one that accepts a body or a file.
- Handling secrets, tokens, or credentials in code or configuration.
- Implementing payments, or storing and transmitting personal data.
- Integrating a third-party API that holds or returns sensitive data.
- Reviewing a change that touches any of the above, as the security pillar of `code-reviewer`.
- The user says "add login to this app", "review this endpoint before it ships", "we are taking payments now", "is
  this file upload safe", or "check this for injection".
- Hardening cloud IAM, network rules, pipeline scanning, or a CDN, through the cloud reference below.

---

### When not to activate

- A full multi-pillar review of a change. Use `code-reviewer`, which pulls this skill in for the security pillar.
- Threat modelling, attack trees, or a formal assessment. Escalate to the `security-auditor` agent.
- Pipeline OIDC, job permissions, and action pinning. Use `deployment-patterns`.
- Container image hardening, base image choice, SBOM generation, and image scanning. Use `docker-patterns`.
- Spring Security wiring specifically. Use `springboot-patterns`.
- Writing the tests that prove a control works. Use `tdd-workflow`.

---

### Rules

1. Secrets. No credential in source. Read each from the environment and fail fast at startup when one is missing. Keep `.env*` out of version control, check the history too, and hold production secrets in the platform's secret store.
2. Input validation. Validate every input against an allowlist schema at the boundary. Uploads check size, declared type, extension and binary signature, none sufficient alone, with the body capped by the server or proxy first. Store under a generated name outside the web root, re-encode images, and leak no internal structure in errors.
3. Injection. Never concatenate user input into a query. Parameterise SQL, shell commands, LDAP filters, NoSQL documents and template expressions alike.
4. Authentication and sessions. Tokens in `HttpOnly`, `Secure`, `SameSite` cookies, never `localStorage`. Hash passwords with Argon2id; BCrypt at cost 12 or more is a fallback; PBKDF2-HMAC-SHA256 at 600,000 or more iterations only where FIPS-140 requires it; MD5, SHA-1 and unsalted SHA-256 are prohibited.
5. Authorization. Check on the server, before the operation, against the session identity, never a role the client sent. Row-level security, enabled and forced, is defence in depth: identity set per transaction, read through `nullif(current_setting(..., true), '')`, connecting as a non-owner role without `BYPASSRLS`.
6. XSS and CSP. Sanitise user HTML with an explicit tag and attribute allowlist. Ship a CSP with no `unsafe-inline` and no `unsafe-eval`, using a per-request nonce where inline code must exist.
7. CSRF. Every cookie-authenticated state change carries a CSRF token bound to the session and a strong `SameSite` cookie. Say deliberately when a header-token API is exempt.
8. Sensitive data exposure. No password, token or full card number in a log at any level, card numbers redacted to the last four, no stack trace or internal message in a response.
9. Dependency risk. Scan on every pull request and block on a fixable critical or high finding. Commit the lock file and install from it in CI. Run `npm audit fix` deliberately, and turn on an update bot only with approval.
10. Test the controls. Assert the rejections, 401, 403 and 400, not only the success path.

---

### Rate limiting

This section owns the rate-limit policy. Limit every endpoint, expensive ones harder. Key on the authenticated user where there is one and on the client address where there is not, and keep counters in a store every instance shares once there is more than one process. Login also counts failures per target account, because credential stuffing spreads across addresses and OWASP says the counter "should be associated with the account itself, rather than the source IP address". Back off on it and alert when one address tries many accounts. The tiers live in the tiers table in `api-design`, the values belong to each application from its measured load, and `springboot-patterns` (`references/security.md`) and `node-backend-patterns` (`references/rate-limiting.md`) implement both.

---

### Reference map

| Task | Open |
| --- | --- |
| Implementing or reviewing a rule above: its reasoning, OWASP quotes, and pass and fail code | [references/application-controls.md](references/application-controls.md) |
| OAuth 2.1 and PKCE, JWT validation, mTLS, required response headers, zero trust, supply chain, audit logging, privacy, encryption at rest, SAST and DAST | [references/platform-security.md](references/platform-security.md) |
| Cloud IAM, secrets managers, network rules, pipeline scanning, CDN and WAF, backup and recovery | [references/cloud-infrastructure-security.md](references/cloud-infrastructure-security.md) |
| Wallet signature verification and on-chain transaction validation | [references/blockchain-security.md](references/blockchain-security.md) |

---

### Related skills

- `code-reviewer` is the parent review, and its security findings escalate to the `security-auditor` agent.
- `api-design` owns the contract and error shape validation asserts against, `observability-and-logging` the log structure redaction applies to, and `tdd-workflow` the discipline behind the control tests.

---

### Checklist

Run before any production deployment.

- [ ] No hardcoded secret in the working tree or the git history.
- [ ] Every secret read from the environment, with a startup check.
- [ ] Every input validated against a schema at the boundary.
- [ ] File uploads checked on size, extension, declared type, and magic bytes, stored under a generated name outside
  the web root.
- [ ] Every query parameterised, in SQL and in every other interpreted target.
- [ ] Tokens in `HttpOnly`, `Secure`, `SameSite` cookies.
- [ ] Passwords hashed with Argon2id, or BCrypt at cost 12 or higher, or PBKDF2-HMAC-SHA256 at 600,000 iterations
  where FIPS-140 requires it.
- [ ] Authorization checked server-side against the session identity, before the operation.
- [ ] Row-level security enabled and forced where the database supports it, identity set per transaction, as defence
  in depth.
- [ ] User HTML sanitised with an explicit allowlist.
- [ ] CSP shipped with no `unsafe-inline` and no `unsafe-eval`.
- [ ] CSRF defence on every cookie-authenticated state change, with the token bound to the session.
- [ ] Rate limits on every endpoint at the `api-design` tiers, tighter on expensive and auth endpoints, with a
  per-account failed-login counter.
- [ ] No secret in a log, no stack trace in a response.
- [ ] Dependency scan clean at high and critical, lock file committed, CI installs from it.
- [ ] Rejection paths covered by tests, not only the happy path.
- [ ] HTTPS enforced, security headers set, CORS scoped to known origins.
- [ ] Auth, payment and personal-data findings escalated to the `security-auditor` agent.
