# Application Controls in TypeScript

Contents:

- [Secrets](#secrets)
- [Input validation](#input-validation)
- [Injection](#injection)
- [Session cookies](#session-cookies)
- [Authorization](#authorization)
- [HTML sanitising](#html-sanitising)
- [CSRF](#csrf)
- [Sensitive data exposure](#sensitive-data-exposure)
- [Dependency risk with npm](#dependency-risk-with-npm)
- [Test the controls](#test-the-controls)
- [Reading](#reading)

The pass and fail code for the application controls in TypeScript on Node, with the npm commands for dependency risk. Open this when the code under review is TypeScript or JavaScript, or the project installs with npm. The reasoning behind each control is in [application-controls.md](application-controls.md).

---

### Secrets

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

---

### Input validation

Fail: the body is trusted as typed.

```typescript
export async function createUser(input: CreateUserInput) {
  return db.users.create(input)
}
```

Pass: parsed and rejected at the edge.

```typescript
const CreateUserSchema = z.object({
  email: z.email(),
  name: z.string().min(1).max(100),
  age: z.number().int().min(0).max(150),
})

export async function createUser(input: unknown) {
  const validated = CreateUserSchema.parse(input)
  return db.users.create(validated)
}
```

---

### Injection

Fail:

```typescript
const query = `SELECT * FROM users WHERE email = '${userEmail}'`
await db.query(query)
```

Pass:

```typescript
await db.query('SELECT id, email, name FROM users WHERE email = $1', [userEmail])
```

---

### Session cookies

Fail:

```typescript
localStorage.setItem('token', token)
```

Pass:

```typescript
res.setHeader('Set-Cookie', `token=${token}; HttpOnly; Secure; SameSite=Strict; Max-Age=3600`)
```

---

### Authorization

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

---

### HTML sanitising

Sanitise any user-provided HTML before rendering it, with an explicit tag and attribute allowlist.

```typescript
const clean = DOMPurify.sanitize(html, {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p'],
  ALLOWED_ATTR: [],
})
```

---

### CSRF

Fail: a cookie-authenticated POST with no origin defence.

```typescript
export async function POST(request: Request) {
  const session = await getSession(request)
  return updateProfile(session.userId, await request.json())
}
```

Pass: the session is loaded first, so the token is checked against the session it was issued for.

```typescript
export async function POST(request: Request) {
  const session = await getSession(request)
  if (!csrf.verify(session.id, request.headers.get('X-CSRF-Token'))) {
    return NextResponse.json({ error: 'Invalid CSRF token' }, { status: 403 })
  }
  return updateProfile(session.userId, await request.json())
}
```

```typescript
res.setHeader('Set-Cookie', `session=${sessionId}; HttpOnly; Secure; SameSite=Strict`)
```

---

### Sensitive data exposure

Fail:

```typescript
logger.info({ email, password }, 'user login')
return NextResponse.json({ error: error.message, stack: error.stack }, { status: 500 })
```

Pass:

```typescript
logger.info({ userId }, 'user login')
logger.error({ err: error }, 'internal error')
return NextResponse.json({ error: 'An error occurred. Please try again.' }, { status: 500 })
```

---

### Dependency risk with npm

Scan on every pull request and block on a high or critical finding:

```bash
npm audit --audit-level=high
```

Install from the committed lock file in CI:

```bash
npm ci
```

Run `npm audit fix` deliberately rather than in CI: it rewrites the lock file, so the diff needs reviewing before it is
committed.

The package scripts for a local audit. `install` is not redefined, because npm runs that lifecycle script during
every install.

```json
{
  "scripts": {
    "audit": "npm audit --audit-level=high",
    "check": "npm outdated"
  }
}
```

---

### Test the controls

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

### Reading

- [Security in Next.js Server Components and Actions](https://nextjs.org/blog/security-nextjs-server-components-actions)
