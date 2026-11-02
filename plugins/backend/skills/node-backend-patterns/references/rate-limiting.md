# Rate limiting in Node services

Read this when adding a limiter to an Express or Next.js route, or when a limiter behaves differently across instances.

The header names, the tier table, and the 429 body shape are owned by `api-design`. The policy of what to key on and
where to count is owned by the "Rate limiting" section of `security-review`. This file covers only the Node
implementation of both.

---

### Contents

- Count in a shared store once you run more than one process
- Choose the subject before the algorithm
- Fixed window is fine, sliding window is better at the edges
- Always emit the headers, not only on rejection
- Limit the expensive endpoints separately
- Never let the limiter take the service down
- Related skills

---

### Count in a shared store once you run more than one process

An in-memory counter resets on deploy and counts each instance separately, so a limit of 100 becomes 100 times the
instance count. Use it only for a single-process development server or as a last-resort local circuit breaker.

Pass: a Redis counter keyed by subject and window, shared by every instance, with the increment and the expiry sent as one `MULTI` transaction. Sent as two calls, a process that dies between them leaves a key with no expiry behind.

```typescript
async function hit(redis: RedisClient, subject: string, windowMs: number, max: number) {
  const window = Math.floor(Date.now() / windowMs)
  const key = `rl:${subject}:${window}`

  const [reply] = await redis.multi().incr(key).pExpire(key, windowMs).exec()
  const count = Number(reply)

  return { allowed: count <= max, remaining: Math.max(0, max - count), resetMs: (window + 1) * windowMs - Date.now() }
}
```

Fail: `const requests = new Map<string, number[]>()` in a module scope, deployed to four pods behind a load balancer.

---

### Choose the subject before the algorithm

Which subject to key on is the policy in the "Rate limiting" section of `security-review`. In Node that subject becomes
the `subject` part of the Redis key, so one user or one anonymous client address maps to `rl:<subject>:<window>` and
every instance increments the same counter.

When the subject is the client address, behind a proxy trust only the hop you control. Set
`app.set('trust proxy', 1)` in Express for exactly one trusted proxy, rather than reading the leftmost
`X-Forwarded-For` value, which the client can forge.

---

### Fixed window is fine, sliding window is better at the edges

A fixed window lets a caller send `2 * max` requests across a window boundary. When that burst matters, keep a sorted set of timestamps per subject and trim it on each hit. The trim, the count and the add must run as one atomic Redis operation, a Lua script sent with `EVAL`, or N instances that all read `count < max` at once all add, and admit up to N times the limit.

```typescript
const SLIDING_WINDOW = `
local key, now, window, max = KEYS[1], tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= max then return -1 end
redis.call('ZADD', key, now, ARGV[4])
redis.call('PEXPIRE', key, window)
return max - count - 1
`

async function slidingHit(redis: RedisClient, subject: string, windowMs: number, max: number) {
  const now = Date.now()
  const remaining = Number(await redis.eval(SLIDING_WINDOW, {
    keys: [`rl:sw:${subject}`],
    arguments: [String(now), String(windowMs), String(max), `${now}:${crypto.randomUUID()}`],
  }))
  return { allowed: remaining >= 0, remaining: Math.max(0, remaining) }
}
```

Fail: `zRemRangeByScore`, `zCard` and `zAdd` sent as three separate awaits, which reads the count on one round trip and adds on another, so concurrent requests on different instances all pass the check.

---

### Always emit the headers, not only on rejection

A client cannot back off from a limit it cannot see. Set `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` on every rate-limited response, and add `Retry-After` plus an RFC 9457 problem body on the 429. `X-RateLimit-Reset` is the window end as a UTC epoch in seconds, while `Retry-After` is the seconds left.

```typescript
export async function GET(request: Request) {
  const subject = await subjectFor(request)
  const { allowed, remaining, resetMs } = await hit(redis, subject, 60_000, 100)
  const resetSeconds = Math.ceil(resetMs / 1000)
  const resetEpochSeconds = Math.ceil(Date.now() / 1000) + resetSeconds

  const headers = {
    'X-RateLimit-Limit': '100',
    'X-RateLimit-Remaining': String(remaining),
    'X-RateLimit-Reset': String(resetEpochSeconds),
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
