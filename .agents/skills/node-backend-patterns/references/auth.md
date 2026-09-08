# Authentication and authorization in Node services

Read this when adding token verification, wiring an authorization check into a route, or reviewing a handler that
trusts the client.

---

### Verify the token, never decode it

`jwt.decode` reads a token without checking the signature, so anything it returns is attacker-controlled. Always call
`jwt.verify`, and always pin the algorithm: leaving it open lets a caller present an `alg: none` or an HMAC token signed
with your public key.

```typescript
import jwt from 'jsonwebtoken'

export function verifyToken(token: string): JwtPayload {
  return jwt.verify(token, config.JWT_PUBLIC_KEY, {
    algorithms: ['RS256'],
    issuer: config.JWT_ISSUER,
    audience: config.JWT_AUDIENCE,
  }) as JwtPayload
}
```

Fail: `const payload = jwt.decode(token) as JwtPayload`, or `jwt.verify(token, secret)` with no `algorithms` option.

For an external identity provider, fetch the signing keys from its JWKS endpoint with a cached key set rather than
pasting a key into configuration. `keycloak-auth-services` covers the Keycloak side of that exchange.

---

### Check issuer, audience, and expiry, then check the subject exists

A structurally valid token from a different realm is still a valid signature. Assert `iss` and `aud` explicitly, let the
library enforce `exp` and `nbf`, and treat a small `clockTolerance` (a few seconds) as the only slack you allow.

For anything destructive, confirm the subject is still active in your own store. A token stays valid until it expires,
including for a user you disabled a minute ago.

---

### Authenticate once at the edge, authorize per resource

Authentication answers who is calling. Authorization answers whether this caller may touch this row. A role check alone
lets any authenticated user read any record by changing the identifier in the URL.

```typescript
export async function GET(request: Request, { params }: { params: { id: string } }) {
  const user = await requireAuth(request)
  const order = await orderRepo.findById(params.id)

  if (!order) throw new ApiError(404, 'Not found')
  if (order.userId !== user.sub) throw new ApiError(403, 'Forbidden')

  return NextResponse.json({ data: order })
}
```

Fail: `requireRole('user')` on the route and nothing comparing `order.userId` to the caller.

---

### Return 404 when disclosing existence is itself a leak

For a resource whose identifier is guessable and whose existence is confidential, answer 404 rather than 403. Otherwise
an attacker enumerates valid identifiers by reading the difference between the two responses.

---

### Keep the permission table in one place

Scatter the role-to-permission mapping across handlers and it drifts. Declare it once, ask it a question, and let the
type system list the roles.

```typescript
type Permission = 'read' | 'write' | 'delete' | 'admin'

const rolePermissions: Record<Role, readonly Permission[]> = {
  admin: ['read', 'write', 'delete', 'admin'],
  moderator: ['read', 'write', 'delete'],
  user: ['read', 'write'],
}

export function can(user: User, permission: Permission): boolean {
  return rolePermissions[user.role].includes(permission)
}
```

---

### Deny by default

A new route with no auth wrapper must not be public by accident. Apply authentication in the router or middleware layer
and mark the public routes explicitly, so the omission fails closed.

```typescript
const PUBLIC_ROUTES = new Set(['/health', '/ready', '/api/v1/auth/login'])

app.use((req, res, next) => (PUBLIC_ROUTES.has(req.path) ? next() : requireAuth(req, res, next)))
```

---

### Store refresh tokens server-side and rotate them

An access token stays short (minutes) and is not revocable. A refresh token is long-lived, so keep a hashed copy in the
database, issue a new one on every use, and revoke the whole family when a used token is presented again, which is the
signature of a stolen token.

Put a refresh token in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie for browser clients. Never put either token in
`localStorage`, where any injected script can read it.

---

### Never log a token, and never put one in a URL

Log the subject and the token identifier (`jti`), not the credential. Query strings land in access logs, proxy logs, and
browser history.

---

### Return RFC 7807 problem bodies for auth failures

401 means the credential is missing or invalid, 403 means the credential is fine and the caller still may not do this.
Use `WWW-Authenticate` on the 401 and keep the detail generic: an error that says which half of the credential was wrong
is a free oracle.

```typescript
return NextResponse.json(
  { type: 'https://example.com/errors/unauthorized', title: 'Unauthorized', status: 401, detail: 'Invalid credentials' },
  { status: 401, headers: { 'Content-Type': 'application/problem+json', 'WWW-Authenticate': 'Bearer' } },
)
```

---

### Related skills

- `node-backend-patterns` for the hub these rules belong to.
- `api-design` for status codes, the problem body shape, and auth headers on the wire.
- `security-review` for threat modelling, session fixation, and input handling.
- `keycloak-auth-services` and `keycloak-administration` when the identity provider is Keycloak.
