---
name: node-backend-patterns
description: Node.js server-side patterns for Express and Next.js route handlers, covering repository and service layering, query batching, RFC 7807 errors, typed config, pino logging, and graceful shutdown. Use when you say "structure my Express API", "fix the N+1 in this route", "cache this Prisma query", "rate limit this endpoint", or "my Node app never exits on SIGTERM". Not for language-neutral backend design, use `backend-patterns`.
---

# Node Backend Patterns

Server-side patterns for Node.js services built on Express or Next.js route handlers, from request layering down to
process shutdown. Everything here is TypeScript on the Node runtime, so the rules assume a single-threaded event loop
and the npm ecosystem.

Baseline versions, current as of September 2026: Node.js 24 LTS, Express 5, Next.js 16, TypeScript 5.

---

### When to activate

- Structuring an Express app or a Next.js `app/api` route into handler, service, and repository layers.
- Removing an N+1 query or a `SELECT *` from a Node data-access path.
- Adding Redis caching, a rate limiter, or a background queue to a Node service.
- Wiring typed configuration, pino logging, or a graceful shutdown handler.
- Reviewing a Node service for error-handling and validation gaps.

---

### When not to activate

- Language-neutral backend design (idempotency, outbox, retries as a concept): use `backend-patterns`.
- HTTP contract questions such as URL shape, status codes, or pagination style: use `api-design`.
- Java or Spring services: use `springboot-patterns`. Python: use `python-patterns`. Go: use `golang-patterns`.
- Next.js rendering, Server Components, caching, or Server Actions: use `nextjs-app-router-patterns`.
- Port and adapter boundaries and dependency inversion: use `hexagonal-architecture`.
- SQL schema, index, and query-plan work: use `postgres-patterns`.

---

### Reference map

| Task | Open |
| --- | --- |
| Adding a cache, picking a TTL, fixing stale reads or a stampede | [references/caching.md](references/caching.md) |
| Throttling an endpoint, sharing counters across instances | [references/rate-limiting.md](references/rate-limiting.md) |
| Moving work off the request path, queues, outbox, retries | [references/background-jobs.md](references/background-jobs.md) |
| Token verification, per-resource authorization, refresh tokens | [references/auth.md](references/auth.md) |

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
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  PORT: z.coerce.number().default(3000),
})
export const config = schema.parse(process.env)
```

Fail: `const port = Number(process.env.PORT) || 3000` repeated in four files, with no check that `JWT_SECRET` exists.

---

### Return every error through one handler, as problem+json

One function turns a thrown error into a response, so the shape is identical across every route and no stack trace
leaks. Use `application/problem+json` per RFC 7807, which is the contract `api-design` defines.

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

### Doc comments

Default to none. A doc comment is usually a sign that the code failed to explain itself. Before writing one, extract the
unclear block into a well-named function, rename the parameters so they carry their own meaning, and tighten the types.
Do that first and most doc comments have nothing left to say, which is the outcome you want. Code that explains itself
cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@param` and `@returns` and `@throws` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `@param` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or who
   owns the argument afterwards. `@param userId - The user identifier` is noise, delete it, and never restate a type
   TypeScript already declares.
3. `@returns` only when it is non-obvious.
4. `@throws` always, for every error a caller can act on. TypeScript keeps throws out of the signature, so this one is
   genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you justify
in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete it.

```typescript
// PASS: one sentence, then only what the signature cannot say
/**
 * Charges the saved payment method and records the receipt.
 *
 * @param amountMinor amount in minor units, never a float
 * @throws {PaymentDeclinedError} when the processor declines the charge
 */
export async function chargeCustomer(customerId: string, amountMinor: number): Promise<Receipt> { ... }

// FAIL: restates the signature and leaves the unit of amountMinor a guess
/**
 * Charges a customer.
 *
 * @param customerId - The customer id
 * @param amountMinor - The amount
 * @returns A receipt
 */
export async function chargeCustomer(customerId: string, amountMinor: number): Promise<Receipt> { ... }
```

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

---

### Related skills

- `backend-patterns` for the language-neutral rules these patterns implement.
- `api-design` for URL shape, status codes, pagination, and the canonical rate-limit headers and problem body.
- `hexagonal-architecture` for the port and adapter boundaries behind the repository interface.
- `nextjs-app-router-patterns` for the rendering and caching half of a Next.js app.
- `postgres-patterns` and `database-migrations` for schema, indexes, and safe schema change.
- `observability-and-logging` for the startup banner, log levels, and trace correlation.
- `security-review` before shipping auth, payment, or personal-data handling.

---

### Checklist

- [ ] Handler, service, and repository responsibilities are separate.
- [ ] No `SELECT *` and no query inside a loop on any request path.
- [ ] Multi-statement writes run inside one transaction.
- [ ] Configuration is parsed once at startup against a schema, never read from `process.env` in business logic.
- [ ] Every error leaves through one handler as `application/problem+json`, with no internal detail in the body.
- [ ] Retries are capped, jittered, deadline-bound, and applied only to transient failures.
- [ ] Independent awaits run under `Promise.all`.
- [ ] Logging goes through pino, with `correlationId` and `requestId` on every request-path line.
- [ ] Async state is a discriminated union, not a bag of nullable fields.
- [ ] `SIGTERM` drains the server and closes the pools within a bounded timeout.
