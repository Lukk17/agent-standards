---
name: application-security-review
description: 'Application security review: secrets, input validation, injection, auth, XSS, CSRF and rate limits. Use when the user says "review this endpoint before it ships". Not for container hardening, use `docker-patterns`.'
metadata:
  version: "1.1.0"
---

# Application Security Review

Check application code against the failure modes that actually cause incidents. Threat modelling and a full assessment go to the `security-auditor` agent.

---

### When not to activate

- A full multi-pillar review of a change, use `code-reviewer`.
- Container image hardening, base image choice, SBOM generation and image scanning, use `docker-patterns`.
- Pipeline OIDC, job permissions and action pinning, use `deployment-patterns`.

---

### Rules

1. Secrets. No credential in source or its history. Read each from the environment, fail fast at startup when one is missing, and hold production secrets in the platform's secret store.
2. Input validation. Validate every input against an allowlist schema at the boundary. Check an upload on size, declared type, extension and binary signature, and store it under a generated name outside the web root.
3. Injection. Never concatenate user input into a query. Parameterise SQL, shell commands, LDAP filters, NoSQL documents and template expressions alike.
4. Authentication and sessions. Tokens in `HttpOnly`, `Secure`, `SameSite` cookies, never `localStorage`. Hash passwords with Argon2id. BCrypt at cost 12 or more is a fallback, PBKDF2-HMAC-SHA256 at 600,000 or more iterations only where FIPS-140 requires it, and MD5, SHA-1 and unsalted SHA-256 are prohibited.
5. Authorization. Check on the server, before the operation, against the session identity, never a role the client sent. Row-level security is defence in depth on top.
6. XSS and CSP. Sanitise user HTML with an explicit tag and attribute allowlist. Ship a CSP with no `unsafe-inline` and no `unsafe-eval`, with a per-request nonce for inline code.
7. CSRF. Every cookie-authenticated state change carries a CSRF token bound to the session and a strong `SameSite` cookie.
8. Sensitive data exposure. No password, token or full card number in a log at any level, and no stack trace or internal message in a response.
9. Dependency risk. Scan on every pull request, block on a fixable critical or high finding, commit the lock file and install from it in CI. Run `npm audit fix` deliberately, and turn on an update bot only with approval.
10. Test the controls. Assert the rejections, 401, 403 and 400, not only the success path.

---

### Rate limiting

This section owns the rate-limit policy. Limit every endpoint, expensive ones harder, keyed on the authenticated user or else the client address, with counters in a store every instance shares. Login also counts failures per target account. The tiers are in `api-design`.

---

### Reference map

| Task | Open |
| --- | --- |
| A rule or the rate-limit policy in full, with reasoning and OWASP quotes | [application-controls.md](references/application-controls.md) |
| The code under review is TypeScript, JavaScript or uses npm | [typescript.md](references/typescript.md) |
| The code under review is Python | [python.md](references/python.md) |
| The code under review is Java with Spring | [java-spring.md](references/java-spring.md) |
| Row-level security in PostgreSQL | [postgresql.md](references/postgresql.md) |
| OAuth and PKCE, JWT, mTLS, response headers, zero trust, supply chain, audit logging, privacy, encryption at rest, SAST and DAST | [platform-security.md](references/platform-security.md) |
| Cloud IAM, secrets managers, network rules, pipeline scanning, CDN and WAF, backups | [cloud-infrastructure-security.md](references/cloud-infrastructure-security.md) |
| The cloud under review is AWS | [aws.md](references/aws.md) |
| The CDN or WAF under review is Cloudflare | [cloudflare.md](references/cloudflare.md) |
| Wallet signatures and on-chain transactions | [blockchain-security.md](references/blockchain-security.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before any production deployment | [checklist.md](references/checklist.md) |
