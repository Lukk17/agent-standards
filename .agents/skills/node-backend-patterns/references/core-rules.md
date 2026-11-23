# Node Backend Core Rules in Depth

The Pass and Fail examples and the reasoning behind each rule the SKILL.md hub states in one or two lines. Open it when a hub rule needs its worked form or its full explanation. The code that belongs to one library is in that library's file: [express.md](express.md), [nextjs.md](nextjs.md), [zod.md](zod.md) and [pino.md](pino.md). Written for Node.js 26, Express 5, Next.js 16 and TypeScript 7, with Zod 4 for schemas.

---

### Contents

- [Layer the request path](#layer-the-request-path)
- [Select the columns you need and batch the related reads](#select-the-columns-you-need-and-batch-the-related-reads)
- [Put every multi-statement write in one transaction](#put-every-multi-statement-write-in-one-transaction)
- [Validate configuration once, at startup](#validate-configuration-once-at-startup)
- [Return every error through one handler, as problem+json](#return-every-error-through-one-handler-as-problemjson)
- [Retry only what is safe to repeat, with a cap and a timeout](#retry-only-what-is-safe-to-repeat-with-a-cap-and-a-timeout)
- [Await independent work concurrently](#await-independent-work-concurrently)
- [Log through one logger, with a request-scoped child logger](#log-through-one-logger-with-a-request-scoped-child-logger)
- [Model async state as a discriminated union](#model-async-state-as-a-discriminated-union)
- [Emit a startup readiness log and shut down gracefully](#emit-a-startup-readiness-log-and-shut-down-gracefully)
- [Doc comments](#doc-comments)

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
Express route. What `nextjs-app-router-patterns` owns instead is in [nextjs.md](nextjs.md).

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

Pass: one schema, parsed once, exported as the only way to read configuration. The Zod form is in [zod.md](zod.md#configuration-schema).

Fail: `const port = Number(process.env.PORT) || 3000` repeated in four files, with no check that `JWT_SECRET` exists.

---

### Return every error through one handler, as problem+json

One function turns a thrown error into a response, so the shape is identical across every route and no stack trace leaks. Use `application/problem+json` per RFC 9457, which obsoletes RFC 7807 and is the contract `api-design` defines.

```typescript
export function toProblemResponse(error: unknown, path: string): Response {
  if (error instanceof ApiError) return problem(error.statusCode, error.title, error.detail, path)

  logger.error({ err: error }, 'unhandled error')
  return problem(500, 'Internal Server Error', 'An unexpected error occurred', path)
}
```

A schema failure gets its own branch before the last two lines and answers 422. The Zod form of that branch is in [zod.md](zod.md#schema-failure-in-the-error-handler).

Fail: a handler that puts the error's own message in the body, which ships the database error text to the caller. The Express form is in [express.md](express.md#error-responses).

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

### Log through one logger, with a request-scoped child logger

`console.log` writes unstructured text that no aggregator can query, and it blocks the event loop on some transports.
Put `correlationId` and `requestId` on a child logger so every line from one request joins up. The logger is pino, and its code is in [pino.md](pino.md).

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
`<url> [Connected|Warning|FAILED]` result format). The Node hook is the callback that runs once the server is bound:
the `app.listen` callback in Express ([express.md](express.md#startup-hook)), the post-`app.listen()` line in a NestJS
`bootstrap()`, or the post-bind callback of a custom Next.js server ([nextjs.md](nextjs.md#startup-hook)). Emit the whole block in one log
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

---

### Doc comments

Doc comments follow the Doc Comments rules in `coding-standards`, whose TSDoc examples already cover TypeScript on Node. Node delta: an async function documents the errors its promise rejects with under `@throws`, because a rejection is the Node form of a throw and the signature says only `Promise<T>`.
