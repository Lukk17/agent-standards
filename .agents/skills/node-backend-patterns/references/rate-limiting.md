# Rate limiting in Node services

Read this when adding a limiter to an Express or Next.js route, or when a limiter behaves differently across instances.

The header names, the tier table, and the 429 body shape are owned by `api-design`. This file covers only the Node
implementation of that contract.

---

### Count in a shared store once you run more than one process

An in-memory counter resets on deploy and counts each instance separately, so a limit of 100 becomes 100 times the
instance count. Use it only for a single-process development server or as a last-resort local circuit breaker.

Pass: a Redis counter keyed by subject and window, shared by every instance.

```typescript
async function hit(redis: RedisClient, subject: string, windowMs: number, max: number) {
  const window = Math.floor(Date.now() / windowMs)
  const key = `rl:${subject}:${window}`

  const count = await redis.incr(key)
  if (count === 1) await redis.pExpire(key, windowMs)

  return { allowed: count <= max, remaining: Math.max(0, max - count), resetMs: (window + 1) * windowMs - Date.now() }
}
```

Fail: `const requests = new Map<string, number[]>()` in a module scope, deployed to four pods behind a load balancer.

---

### Choose the subject before the algorithm

Key on the authenticated user or API key whenever the request carries one, and fall back to the client IP only for
anonymous traffic. Keying everything on IP punishes users behind a shared NAT and lets one account with many addresses
bypass the limit entirely.

Behind a proxy, trust only the hop you control. Set `app.set('trust proxy', 1)` in Express for exactly one trusted
proxy, rather than reading the leftmost `X-Forwarded-For` value, which the client can forge.

---

### Fixed window is fine, sliding window is better at the edges

A fixed window lets a caller send `2 * max` requests across a window boundary. When that burst matters, keep a sorted
set of timestamps per subject and trim it on each hit.

```typescript
async function slidingHit(redis: RedisClient, subject: string, windowMs: number, max: number) {
  const now = Date.now()
  const key = `rl:sw:${subject}`

  await redis.zRemRangeByScore(key, 0, now - windowMs)
  const count = await redis.zCard(key)
  if (count >= max) return { allowed: false, remaining: 0 }

  await redis.zAdd(key, { score: now, value: `${now}:${Math.random()}` })
  await redis.pExpire(key, windowMs)
  return { allowed: true, remaining: max - count - 1 }
}
```

---

### Always emit the headers, not only on rejection

A client cannot back off from a limit it cannot see. Set `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and
`X-RateLimit-Reset` on every rate-limited response, and add `Retry-After` plus an RFC 7807 body on the 429.

```typescript
export async function GET(request: Request) {
  const subject = await subjectFor(request)
  const { allowed, remaining, resetMs } = await hit(redis, subject, 60_000, 100)
  const resetSeconds = Math.ceil(resetMs / 1000)

  const headers = {
    'X-RateLimit-Limit': '100',
    'X-RateLimit-Remaining': String(remaining),
    'X-RateLimit-Reset': String(resetSeconds),
  }

  if (!allowed) {
    return NextResponse.json(
      { type: 'https://example.com/errors/rate-limit', title: 'Too Many Requests', status: 429 },
      { status: 429, headers: { ...headers, 'Content-Type': 'application/problem+json', 'Retry-After': String(resetSeconds) } },
    )
  }

  return NextResponse.json({ data: await listMarkets() }, { headers })
}
```

---

### Limit the expensive endpoints separately

One global limit either throttles cheap reads too hard or lets an expensive write through too often. Give login,
password reset, search, export, and any endpoint that calls a paid third party their own tighter bucket, keyed on the
same subject.

---

### Never let the limiter take the service down

If Redis is unreachable, decide explicitly. Fail open for ordinary read traffic (log at warn, serve the request) and
fail closed for authentication endpoints, where an unbounded retry rate is the attack you were defending against.

---

### Related skills

- `node-backend-patterns` for the hub these rules belong to.
- `api-design` for the canonical header names, the tier table, and the 429 problem body.
- `security-review` for brute-force and credential-stuffing defence beyond a request count.
