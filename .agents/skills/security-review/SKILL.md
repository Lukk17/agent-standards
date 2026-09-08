---
name: security-review
description: Application security review covering secrets, input validation, injection, authentication and session handling, authorization with row-level security, XSS and CSP, CSRF, rate limiting, data exposure, and dependency risk. Use when you say "add login to this app", "review this endpoint before it ships", "we are taking payments now", "is this file upload safe", or "check this for injection". Not for container and image hardening, use `docker-patterns`.
---

# Security Review

Check application code against the failure modes that actually cause incidents, with a concrete pass and fail for each.
This skill covers the application layer. Cloud, container and platform hardening live in the references, and the
`security-auditor` agent takes over for threat modelling and a full assessment.

---

### When to activate

- Adding or changing authentication, session handling, or authorization.
- Creating an API endpoint, especially one that accepts a body or a file.
- Handling secrets, tokens, or credentials in code or configuration.
- Implementing payments, or storing and transmitting personal data.
- Integrating a third-party API that holds or returns sensitive data.
- Reviewing a change that touches any of the above, as the security pillar of `code-reviewer`.

---

### When not to activate

- A full multi-pillar review of a change. Use `code-reviewer`, which pulls this skill in for the security pillar.
- Threat modelling, attack trees, or a formal assessment. Escalate to the `security-auditor` agent.
- Cloud IAM, network, CI/CD and CDN hardening. Open
  [references/cloud-infrastructure-security.md](references/cloud-infrastructure-security.md).
- Container image hardening, base image choice, SBOM generation, and image scanning. Use `docker-patterns`.
- Spring Security wiring specifically. Use `springboot-security`.
- Writing the tests that prove a control works. Use `tdd-workflow`.

---

### Secrets

No credential belongs in source. Read every secret from the environment, and fail fast at startup when one is missing
rather than at the first request that needs it.

Fail:

```typescript
const apiKey = "sk-proj-3f8a2b91c4"
const dbPassword = "password123"
```

Pass:

```typescript
const apiKey = process.env.SEARCH_API_KEY
if (!apiKey) {
  throw new Error('SEARCH_API_KEY is not configured')
}
```

Keep `.env*` files out of version control, check the history as well as the working tree, and hold production secrets in
the hosting platform's secret store rather than in a config file.

---

### Input validation

Validate every input against a schema at the boundary, before anything downstream sees it. Allowlist what is permitted;
a blocklist is a list of the attacks you happened to think of.

Fail: the body is trusted as typed.

```typescript
export async function createUser(input: CreateUserInput) {
  return db.users.create(input)
}
```

Pass: parsed and rejected at the edge.

```typescript
const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  age: z.number().int().min(0).max(150),
})

export async function createUser(input: unknown) {
  const validated = CreateUserSchema.parse(input)
  return db.users.create(validated)
}
```

File uploads need size, declared type, extension, and the binary signature, because the first three are all attacker
controlled.

Fail: extension only.

```python
def validate_upload(filename: str) -> bool:
    return filename.lower().endswith((".jpg", ".png"))
```

Pass: the bytes decide.

```python
import magic

def validate_upload(file_bytes: bytes, filename: str, allowed_types: list[str]) -> bool:
    if len(file_bytes) > 5 * 1024 * 1024:
        return False
    if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
        return False
    return magic.from_buffer(file_bytes, mime=True) in allowed_types
```

Error messages returned to the caller must not leak which field failed for a reason that reveals internal structure.

---

### Injection

Never build a query by concatenating user input. Use parameters, or a query builder that parameterises for you.

Fail:

```typescript
const query = `SELECT * FROM users WHERE email = '${userEmail}'`
await db.query(query)
```

Pass:

```typescript
await db.query('SELECT id, email, name FROM users WHERE email = $1', [userEmail])
```

The same rule covers every interpolated language, not just SQL: shell commands, LDAP filters, NoSQL query documents, and
template expressions. If user input becomes part of a sentence another interpreter parses, it needs the parameterised
form of that interpreter.

---

### Authentication and session handling

Tokens live in `HttpOnly` cookies, never in `localStorage`, because any script that runs on the page can read
`localStorage` and a stolen token is a full account takeover.

Fail:

```typescript
localStorage.setItem('token', token)
```

Pass:

```typescript
res.setHeader('Set-Cookie', `token=${token}; HttpOnly; Secure; SameSite=Strict; Max-Age=3600`)
```

Hash passwords with Argon2id as the primary choice (`argon2-cffi` in Python, `Argon2PasswordEncoder` in Spring). BCrypt
with a cost factor of 12 or more is an acceptable fallback. MD5, SHA-1, unsalted SHA-256, and PBKDF2 under 100,000
iterations are prohibited.

```python
from argon2 import PasswordHasher

hasher = PasswordHasher()
stored = hasher.hash(password)
hasher.verify(stored, password)
```

```java
PasswordEncoder encoder = new Argon2PasswordEncoder(16, 32, 1, 65536, 3);
String stored = encoder.encode(rawPassword);
encoder.matches(rawPassword, stored);
```

OAuth, PKCE and JWT validation rules are in [references/platform-security.md](references/platform-security.md).

---

### Authorization

Check authorization before the operation, on the server, against the authenticated identity rather than an identifier
the client sent.

Fail: the caller names their own role.

```typescript
export async function deleteUser(userId: string, role: string) {
  if (role !== 'admin') return forbidden()
  await db.users.delete({ where: { id: userId } })
}
```

Pass: the role is looked up from the session identity.

```typescript
export async function deleteUser(userId: string, session: Session) {
  const requester = await db.users.findUnique({ where: { id: session.userId } })
  if (requester?.role !== 'admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }
  await db.users.delete({ where: { id: userId } })
}
```

Where the database supports row-level security, enable it on every table holding user data and write the policy per
operation. It is defence in depth: a missing check in one handler no longer exposes another user's rows.

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_select_own ON users
  FOR SELECT
  USING (id = current_setting('app.current_user_id')::uuid);

CREATE POLICY users_update_own ON users
  FOR UPDATE
  USING (id = current_setting('app.current_user_id')::uuid);
```

The session variable is set per connection from the authenticated identity. Managed platforms expose their own
equivalent, such as an `auth.uid()` function, and the policy shape is the same either way. Row-level security is an
addition to application authorization checks, never a replacement for them.

---

### XSS and content security policy

Sanitise any user-provided HTML before rendering it, with an explicit tag and attribute allowlist.

```typescript
const clean = DOMPurify.sanitize(html, {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p'],
  ALLOWED_ATTR: [],
})
```

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

The full set of required response headers is in [references/platform-security.md](references/platform-security.md).

---

### CSRF

Every state-changing request needs either a CSRF token or a `SameSite` cookie strong enough to prevent cross-site
submission, and in practice both.

Fail: a cookie-authenticated POST with no origin defence.

```typescript
export async function POST(request: Request) {
  const session = await getSession(request)
  return updateProfile(session.userId, await request.json())
}
```

Pass:

```typescript
export async function POST(request: Request) {
  if (!csrf.verify(request.headers.get('X-CSRF-Token'))) {
    return NextResponse.json({ error: 'Invalid CSRF token' }, { status: 403 })
  }
  const session = await getSession(request)
  return updateProfile(session.userId, await request.json())
}
```

```typescript
res.setHeader('Set-Cookie', `session=${sessionId}; HttpOnly; Secure; SameSite=Strict`)
```

A token-in-header API that never authenticates from a cookie is not CSRF-exposed in the same way, but say so
deliberately rather than by omission.

---

### Rate limiting

Rate limit every endpoint, and limit expensive endpoints harder. Key on the authenticated user where there is one and on
the client address where there is not, because an address-only limit punishes shared networks and an identity-only limit
does nothing to anonymous abuse.

Fail: the expensive path shares the global limit.

```typescript
app.use('/api/', rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }))
```

Pass: the expensive path gets its own, tighter budget.

```typescript
app.use('/api/', rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }))
app.use('/api/search', rateLimit({ windowMs: 60 * 1000, max: 10 }))
app.use('/api/auth/login', rateLimit({ windowMs: 60 * 1000, max: 5 }))
```

---

### Sensitive data exposure

Nothing secret reaches a log, and nothing internal reaches a client.

Fail:

```typescript
logger.info({ email, password }, 'user login')
return NextResponse.json({ error: error.message, stack: error.stack }, { status: 500 })
```

Pass:

```typescript
logger.info({ email, userId }, 'user login')
logger.error({ err: error }, 'internal error')
return NextResponse.json({ error: 'An error occurred. Please try again.' }, { status: 500 })
```

Redact card numbers to the last four digits, never log a token or a password even at debug level, and keep stack traces
on the server. Audit logging, encryption at rest, and privacy obligations are in
[references/platform-security.md](references/platform-security.md).

---

### Dependency risk

Scan dependencies on every pull request and block the build on a critical or high severity finding that has a fix
available. Commit the lock file and install from it in CI so the build is reproducible.

```bash
npm audit --audit-level=high
```

```bash
npm ci
```

Run `npm audit fix` deliberately rather than in CI: it rewrites the lock file, so the diff needs reviewing before it is
committed. A scheduled dependency review belongs in the process. Turning on an automated update bot is a decision to
take with approval, not a default.

SBOM generation, container image signing, and image vulnerability scanning belong to the container pipeline. Use
`docker-patterns` for those.

---

### Test the controls

A control nobody tests is a control nobody has. Assert the rejection, not just the success path.

```typescript
test('rejects an unauthenticated request', async () => {
  const response = await fetch('/api/protected')
  expect(response.status).toBe(401)
})

test('rejects a non-admin caller', async () => {
  const response = await fetch('/api/admin', { headers: { Authorization: `Bearer ${userToken}` } })
  expect(response.status).toBe(403)
})

test('rejects a malformed payload', async () => {
  const response = await fetch('/api/users', {
    method: 'POST',
    body: JSON.stringify({ email: 'not-an-email' }),
  })
  expect(response.status).toBe(400)
})
```

---

### Reference map

| Task | Open |
| --- | --- |
| OAuth 2.1 and PKCE, JWT validation, mTLS, required response headers, zero trust, supply chain, audit logging, privacy, encryption at rest, SAST and DAST | [references/platform-security.md](references/platform-security.md) |
| Cloud IAM, secrets managers, network rules, pipeline hardening, CDN and WAF, backup and recovery | [references/cloud-infrastructure-security.md](references/cloud-infrastructure-security.md) |
| Wallet signature verification and on-chain transaction validation | [references/blockchain-security.md](references/blockchain-security.md) |

---

### Related skills

- `code-reviewer` is the parent review workflow, and findings from it feed its security pillar and escalate to the
  `security-auditor` agent.
- `docker-patterns` owns container hardening, SBOM generation, and image scanning.
- `springboot-security` owns Spring Security configuration specifically.
- `api-design` owns the contract and error shape the validation rules above assert against.
- `observability-and-logging` owns the log structure the redaction rules apply to.
- `tdd-workflow` owns the discipline behind the control tests.

---

### Checklist

Run before any production deployment.

- [ ] No hardcoded secret in the working tree or the git history.
- [ ] Every secret read from the environment, with a startup check.
- [ ] Every input validated against a schema at the boundary.
- [ ] File uploads checked on size, extension, declared type, and magic bytes.
- [ ] Every query parameterised, in SQL and in every other interpreted target.
- [ ] Tokens in `HttpOnly`, `Secure`, `SameSite` cookies.
- [ ] Passwords hashed with Argon2id, or BCrypt at cost 12 or higher.
- [ ] Authorization checked server-side against the session identity, before the operation.
- [ ] Row-level security enabled where the database supports it, as defence in depth.
- [ ] User HTML sanitised with an explicit allowlist.
- [ ] CSP shipped with no `unsafe-inline` and no `unsafe-eval`.
- [ ] CSRF defence on every cookie-authenticated state change.
- [ ] Rate limits on every endpoint, tighter on expensive and auth endpoints.
- [ ] No secret in a log, no stack trace in a response.
- [ ] Dependency scan clean at high and critical, lock file committed, CI installs from it.
- [ ] Rejection paths covered by tests, not only the happy path.
- [ ] HTTPS enforced, security headers set, CORS scoped to known origins.
- [ ] Auth, payment and personal-data findings escalated to the `security-auditor` agent.
