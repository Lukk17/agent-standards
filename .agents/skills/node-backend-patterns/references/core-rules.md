# Node Backend Core Rules in Depth

The Pass and Fail examples and the reasoning behind each rule the SKILL.md hub states in one or two lines. Open it when a hub rule needs its worked form or its full explanation. Written for Node.js 26, Express 5, Next.js 16 and TypeScript 7, with Zod 4 for schemas.

---

### Contents

- Layer the request path
- Select the columns you need and batch the related reads
- Put every multi-statement write in one transaction
- Validate configuration once, at startup
- Return every error through one handler, as problem+json
- Retry only what is safe to repeat, with a cap and a timeout
- Await independent work concurrently
- Log through pino, with a request-scoped child logger
- Model async state as a discriminated union
- Emit a startup readiness log and shut down gracefully

---

### Layer the request path

A handler parses and responds. A service holds the business rule. A repository is the only thing that speaks to the
database. Keeping the three apart is what lets you test the rule without a server and swap the store without touching
the rule.

```typescript
class MarketService {
  constructor(private readonly repo: MarketRepository) {}

  async publish(id: string): Promise<Market> {
    const market = await this.repo.findById(id)
    if (!market) throw new ApiError(404, 'Market not found')
    if (market.status !== 'draft') throw new ApiError(409, 'Only a draft market can be published')
    return this.repo.update(id, { status: 'open' })
  }
}
```

Fail: a route handler that calls the query builder directly, checks the status inline, and leaves the same rule to be
re-implemented by the next caller.

This skill owns the layering, error responses, logging, and shutdown of a Next.js route handler as well as of an
Express route. `nextjs-app-router-patterns` owns the `route.ts` file convention, the runtime choice, and caching.

---

### Select the columns you need and batch the related reads

Two defects share one cause: asking the database for more rows than the response uses, and asking it once per row. Both
show up as a fast endpoint in development and a timeout in production.

```typescript
// PASS: named columns, bounded result, one extra query for every creator
const markets = await db.selectFrom('markets')
  .select(['id', 'name', 'status', 'creator_id'])
  .where('status', '=', 'active')
  .limit(20)
  .execute()

const byId = new Map((await userRepo.findByIds(markets.map((m) => m.creator_id))).map((c) => [c.id, c]))
const result = markets.map((m) => ({ ...m, creator: byId.get(m.creator_id) ?? null }))

// FAIL: every column, every row, then one query per row
const all = await db.selectFrom('markets').selectAll().execute()
for (const market of all) market.creator = await getUser(market.creator_id)
```

---

### Put every multi-statement write in one transaction

Two writes that must both land, or neither, belong in a single transaction owned by the service, not stitched together
by two repository calls that can fail between them.

```typescript
await db.transaction().execute(async (tx) => {
  const market = await tx.insertInto('markets').values(marketData).returningAll().executeTakeFirstOrThrow()
  await tx.insertInto('positions').values({ ...positionData, market_id: market.id }).execute()
  return market
})
```

Fail: `await createMarket(data)` then `await createPosition(data)`, leaving an orphan market when the second throws.

---

### Validate configuration once, at startup

Reading `process.env` inside business logic means a missing variable surfaces as `undefined` in the middle of a request,
hours after deploy. Parse the whole environment once against a schema so the process refuses to start instead.

```typescript
// PASS: one schema, parsed once, exported as the only way to read configuration
const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  DATABASE_URL: z.url(),
  JWT_SECRET: z.string().min(32),
  PORT: z.coerce.number().default(3000),
})
export const config = schema.parse(process.env)
```

Fail: `const port = Number(process.env.PORT) || 3000` repeated in four files, with no check that `JWT_SECRET` exists.

---

### Return every error through one handler, as problem+json

One function turns a thrown error into a response, so the shape is identical across every route and no stack trace leaks. Use `application/problem+json` per RFC 9457, which obsoletes RFC 7807 and is the contract `api-design` defines.

```typescript
export function toProblemResponse(error: unknown, path: string): Response {
  if (error instanceof ApiError) return problem(error.statusCode, error.title, error.detail, path)

  if (error instanceof z.ZodError) {
    const errors = error.issues.map((i) => ({ field: i.path.join('.'), message: i.message, code: i.code }))
    return problem(422, 'Validation Failed', `${errors.length} field(s) failed validation`, path, { errors })
  }

  logger.error({ err: error }, 'unhandled error')
  return problem(500, 'Internal Server Error', 'An unexpected error occurred', path)
}
```

Fail: `res.status(500).json({ error: err.message })`, which ships the database error text to the caller.

---

### Retry only what is safe to repeat, with a cap and a timeout

A retry without an upper bound turns a slow dependency into an outage, and a retry on a non-idempotent write duplicates
the effect. Retry timeouts and 5xx responses, never a 4xx, and give every outbound call a deadline.

```typescript
async function withRetry<T>(fn: (signal: AbortSignal) => Promise<T>, attempts = 3): Promise<T> {
  for (let i = 0; ; i++) {
    try {
      return await fn(AbortSignal.timeout(5_000))
    } catch (err) {
      if (i >= attempts - 1 || !isTransient(err)) throw err
      await new Promise((r) => setTimeout(r, Math.min(2 ** i * 1_000 + Math.random() * 1_000, 30_000)))
    }
  }
}
```

Fail: a `while (true)` loop around a POST with no timeout, no jitter, and no check on whether the failure was a 400.

---

### Await independent work concurrently

Two calls with no data dependency should not run in sequence. On a single event loop this is free latency.

```typescript
// PASS
const [market, permissions] = await Promise.all([marketRepo.findById(id), authService.loadPermissions(userId)])

// FAIL: the second request waits for the first for no reason
const market = await marketRepo.findById(id)
const permissions = await authService.loadPermissions(userId)
```

---

### Log through pino, with a request-scoped child logger

`console.log` writes unstructured text that no aggregator can query, and it blocks the event loop on some transports.
Use pino, and put `correlationId` and `requestId` on a child logger so every line from one request joins up.

```typescript
export async function GET(request: Request) {
  const correlationId = request.headers.get('x-correlation-id') ?? crypto.randomUUID()
  const log = logger.child({ correlationId, requestId: crypto.randomUUID() })

  log.info({ path: '/api/markets' }, 'fetching markets')
  return NextResponse.json({ data: await fetchMarkets() })
}
```

Fail: `console.error('failed', error)` inside a catch block, with no request identifier anywhere in the line.

---

### Model async state as a discriminated union

Three independent nullable fields allow states that cannot happen, such as loading and error at once. A tagged union
makes the impossible states unrepresentable and forces the caller to handle every arm.

```typescript
type UserState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: User }
  | { status: 'error'; error: Error }
```

Fail: `type UserState = { loading: boolean; error: Error | null; user: User | null }`.

---

### Emit a startup readiness log and shut down gracefully

See `observability-and-logging` for the universal startup banner convention (sections, 2-second probe timeouts, and the
`<url> [Connected|Warning|FAILED]` result format). The Node hook is the `app.listen` callback, the post-`app.listen()`
line in a NestJS `bootstrap()`, or the post-bind callback of a custom Next.js server. Emit the whole block in one log
call with a leading newline, because a logger stamps a timestamp per call and would shred the banner across many.

On `SIGTERM`, stop accepting connections, drain in-flight requests, close the pools, and keep a hard timer so a stuck
drain cannot hold the container past its grace period.

```typescript
async function shutdown(signal: string) {
  logger.info({ signal }, 'shutdown received')
  setTimeout(() => { logger.error('forced shutdown'); process.exit(1) }, 30_000).unref()

  await new Promise<void>((resolve) => server.close(() => resolve()))
  await db.destroy()
  await redis.quit()
  process.exit(0)
}

process.on('SIGTERM', () => void shutdown('SIGTERM'))
```

Fail: no signal handler at all, so the orchestrator kills the process mid-transaction on every deploy.
