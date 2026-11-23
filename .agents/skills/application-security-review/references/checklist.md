# Application Security Checklist

Run before any production deployment.

- [ ] No hardcoded secret in the working tree or the git history.
- [ ] Every secret read from the environment, with a startup check.
- [ ] Every input validated against a schema at the boundary.
- [ ] File uploads checked on size, extension, declared type, and magic bytes, stored under a generated name outside the web root.
- [ ] Every query parameterised, in SQL and in every other interpreted target.
- [ ] Tokens in `HttpOnly`, `Secure`, `SameSite` cookies.
- [ ] Passwords hashed with Argon2id, or BCrypt at cost 12 or higher, or PBKDF2-HMAC-SHA256 at 600,000 iterations where FIPS-140 requires it.
- [ ] Authorization checked server-side against the session identity, before the operation.
- [ ] Row-level security enabled and forced where the database supports it, identity set per transaction, as defence in depth.
- [ ] User HTML sanitised with an explicit allowlist.
- [ ] CSP shipped with no `unsafe-inline` and no `unsafe-eval`.
- [ ] CSRF defence on every cookie-authenticated state change, with the token bound to the session.
- [ ] Rate limits on every endpoint at the `api-design` tiers, tighter on expensive and auth endpoints, with a per-account failed-login counter.
- [ ] No secret in a log, no stack trace in a response.
- [ ] Dependency scan clean at high and critical, lock file committed, CI installs from it.
- [ ] Rejection paths covered by tests, not only the happy path.
- [ ] HTTPS enforced, security headers set, CORS scoped to known origins.
- [ ] Auth, payment and personal-data findings escalated to the `security-auditor` agent.
