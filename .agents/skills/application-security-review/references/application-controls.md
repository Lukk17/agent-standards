# Application Controls

Contents:

- [Secrets](#secrets)
- [Input validation](#input-validation)
- [Injection](#injection)
- [Authentication and session handling](#authentication-and-session-handling)
- [Authorization](#authorization)
- [XSS and content security policy](#xss-and-content-security-policy)
- [CSRF](#csrf)
- [Rate limiting](#rate-limiting)
- [Sensitive data exposure](#sensitive-data-exposure)
- [Dependency risk](#dependency-risk)
- [Test the controls](#test-the-controls)

Every application-layer control in SKILL.md in full, with its reasoning and the OWASP quotes. The pass and fail code sits in one file per technology: [typescript.md](typescript.md) for TypeScript on Node with npm, [python.md](python.md), [java-spring.md](java-spring.md) and [postgresql.md](postgresql.md). Load this file when implementing or reviewing a control and the one-line summary in SKILL.md is not enough.

---

### Secrets

No credential belongs in source. Read every secret from the environment, and fail fast at startup when one is missing
rather than at the first request that needs it.

Keep `.env*` files out of version control, check the history as well as the working tree, and hold production secrets in
the hosting platform's secret store rather than in a config file.

Pass and fail code: [typescript.md](typescript.md#secrets).

---

### Input validation

Validate every input against a schema at the boundary, before anything downstream sees it. Allowlist what is permitted,
because a blocklist is a list of the attacks you happened to think of.

Fail: the body is trusted as typed. Pass: parsed and rejected at the edge. Code: [typescript.md](typescript.md#input-validation).

File uploads need size, declared type, extension, and the binary signature, and no one of them is sufficient alone. The
first three are attacker controlled, and OWASP's File Upload Cheat Sheet says of signature validation that it "should
not be used on its own, as bypassing it is pretty common and easy".

Fail: extension only. Pass: every check, none sufficient alone. The server or proxy caps the request body before it is
read, so an oversized upload never reaches the validation, and the signature is read from the first bytes only. Code:
[python.md](python.md#upload-validation).

Store the file under a generated name outside the web root and serve it through a handler, so an attacker-chosen
filename never reaches the filesystem or a URL. Re-encode images where the type allows it, which drops any payload
hidden in the original.

Error messages returned to the caller must not leak which field failed for a reason that reveals internal structure.

---

### Injection

Never build a query by concatenating user input. Use parameters, or a query builder that parameterises for you.

The same rule covers every interpolated language, not just SQL: shell commands, LDAP filters, NoSQL query documents, and
template expressions. If user input becomes part of a sentence another interpreter parses, it needs the parameterised
form of that interpreter.

Pass and fail code: [typescript.md](typescript.md#injection).

---

### Authentication and session handling

Tokens live in `HttpOnly` cookies, never in `localStorage`, because any script that runs on the page can read
`localStorage` and a stolen token is a full account takeover.

Fail:

```text
The token is written to localStorage.
```

Pass:

```http
Set-Cookie: token=<token>; HttpOnly; Secure; SameSite=Strict; Max-Age=3600
```

Code: [typescript.md](typescript.md#session-cookies).

Hash passwords with Argon2id as the primary choice. BCrypt
with a cost factor of 12 or more is an acceptable fallback. PBKDF2 is allowed only where FIPS-140 requires it, at
600,000 or more iterations of HMAC-SHA-256, the OWASP Password Storage Cheat Sheet floor. MD5, SHA-1 and unsalted
SHA-256 are prohibited.

Code: [python.md](python.md#password-hashing) and [java-spring.md](java-spring.md#password-hashing).

OAuth, PKCE and JWT validation rules are in [platform-security.md](platform-security.md).

---

### Authorization

Check authorization before the operation, on the server, against the authenticated identity rather than an identifier
the client sent.

Fail: the caller names their own role. Pass: the role is looked up from the session identity. Code:
[typescript.md](typescript.md#authorization).

Where the database supports row-level security, enable and force it on every table holding user data and write the
policy per operation. It is defence in depth: a missing check in one handler no longer exposes another user's rows.

Set the identity per transaction, never per connection, because a pooled connection serves the next user with whatever
value it still holds. A request with no identity must match no row instead of raising. The application connects as a
role that does not own the table and cannot bypass the policy. The policies, the setting calls and the role rules for
PostgreSQL are in [postgresql.md](postgresql.md).

Row-level security is an addition to application authorization checks, never a replacement for them.

---

### XSS and content security policy

Sanitise any user-provided HTML before rendering it, with an explicit tag and attribute allowlist. Code:
[typescript.md](typescript.md#html-sanitising).

Ship a Content Security Policy with no `unsafe-inline` and no `unsafe-eval`. Inline scripts and styles that genuinely
have to exist get a per-request cryptographic nonce.

Fail: the policy permits exactly what it exists to prevent.

```text
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'
```

Pass:

```text
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{random}'; style-src 'self' 'nonce-{random}'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; base-uri 'self'
```

The full set of required response headers is in [platform-security.md](platform-security.md).

---

### CSRF

Every state-changing request needs either a CSRF token or a `SameSite` cookie strong enough to prevent cross-site
submission, and in practice both.

Fail: a cookie-authenticated POST with no origin defence. Pass: the session is loaded first, so the token is checked
against the session it was issued for, and the session cookie is `HttpOnly; Secure; SameSite=Strict`. Code:
[typescript.md](typescript.md#csrf).

A token-in-header API that never authenticates from a cookie is not CSRF-exposed in the same way, but say so
deliberately rather than by omission.

---

### Rate limiting

Rate limit every endpoint, and limit expensive endpoints harder. Key on the authenticated user where there is one and on
the client address where there is not, because an address-only limit punishes shared networks and an identity-only limit
does nothing to anonymous abuse. Keep the counters in a store every instance shares once the service runs more than
one process, because a per-process counter multiplies the limit by the instance count.

Login needs a second counter keyed on the target account, because credential stuffing spreads its attempts across many
addresses and stays under any per-address limit. OWASP's Authentication Cheat Sheet says the failed-login counter
"should be associated with the account itself, rather than the source IP address". Back off on that counter, and
alert when one address tries many accounts.

The "Rate limiting" section of SKILL.md owns that policy. The tiers and what each one keys on are in the tiers table in `api-design`, and the
values belong to each application, set from its own measured load. The
implementations follow both: Spring in `springboot-patterns` under `references/security.md`, and Node in
`node-backend-patterns` under `references/rate-limiting.md`.

Fail: search and login share the global budget, and the only login counter is keyed on the client address.

Pass: search and login each get their own tier from `api-design`, and login also counts failures per target account.

---

### Sensitive data exposure

Nothing secret reaches a log, and nothing internal reaches a client.

Redact card numbers to the last four digits, never log a token or a password even at debug level, and keep stack traces
on the server. Audit logging, encryption at rest, and privacy obligations are in
[platform-security.md](platform-security.md).

Pass and fail code: [typescript.md](typescript.md#sensitive-data-exposure).

---

### Dependency risk

Scan dependencies on every pull request and block the build on a critical or high severity finding that has a fix
available. Commit the lock file and install from it in CI so the build is reproducible.

Run a fix command that rewrites the lock file deliberately rather than in CI, so the diff is reviewed before it is
committed. A scheduled dependency review belongs in the process. Turning on an automated update bot is a decision to
take with approval, not a default.

The npm commands are in [typescript.md](typescript.md#dependency-risk-with-npm).

SBOM generation, container image signing, and image vulnerability scanning belong to the container pipeline. Use
`docker-patterns` for those.

---

### Test the controls

A control nobody tests is a control nobody has. Assert the rejection, not just the success path: 401 for an
unauthenticated request, 403 for a caller without the role, 400 for a malformed payload. Code:
[typescript.md](typescript.md#test-the-controls).
