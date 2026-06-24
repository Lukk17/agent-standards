---
name: backend-patterns
description: Backend architecture patterns, API design, database optimization, and server-side best practices for Node.js, Express, and Next.js API routes.
origin: ECC
---

# Backend Development Patterns

Backend architecture patterns and best practices for scalable server-side applications.

---

### When to Activate

- Designing REST or GraphQL API endpoints
- Implementing repository, service, or controller layers
- Optimizing database queries (N+1, indexing, connection pooling)
- Adding caching (Redis, in-memory, HTTP cache headers)
- Setting up background jobs or async processing
- Structuring error handling and validation for APIs
- Building middleware (auth, logging, rate limiting)

---

### API Design Patterns

#### RESTful API Structure

```typescript
// PASS: Resource-based URLs
GET    /api/markets                 # List resources
GET    /api/markets/:id             # Get single resource
POST   /api/markets                 # Create resource
PUT    /api/markets/:id             # Replace resource
PATCH  /api/markets/:id             # Update resource
DELETE /api/markets/:id             # Delete resource

// PASS: Query parameters for filtering, sorting, pagination
// Offset pagination shown here is for small, fixed-size sets only.
GET /api/markets?status=active&sort=volume&limit=20&offset=0
```

Pagination default (section 12): unbounded or large lists default to cursor pagination
(a stable, opaque cursor over an indexed sort key), not offset. Use offset only for small,
fixed sets where the total stays bounded and deep paging is not a concern; offset degrades
on large tables (the database must scan and discard skipped rows) and can skip or duplicate
rows when the underlying data changes between page requests.

#### Repository Pattern

```typescript
// Abstract data access logic
interface MarketRepository {
  findAll(filters?: MarketFilters): Promise<Market[]>
  findById(id: string): Promise<Market | null>
  create(data: CreateMarketDto): Promise<Market>
  update(id: string, data: UpdateMarketDto): Promise<Market>
  delete(id: string): Promise<void>
}

class SupabaseMarketRepository implements MarketRepository {
  async findAll(filters?: MarketFilters): Promise<Market[]> {
    let query = supabase.from('markets').select('*')

    if (filters?.status) {
      query = query.eq('status', filters.status)
    }

    if (filters?.limit) {
      query = query.limit(filters.limit)
    }

    const { data, error } = await query

    if (error) throw new Error(error.message)
    return data
  }

  // Other methods...
}
```

#### Service Layer Pattern

```typescript
// Business logic separated from data access
class MarketService {
  constructor(private marketRepo: MarketRepository) {}

  async searchMarkets(query: string, limit: number = 10): Promise<Market[]> {
    // Business logic
    const embedding = await generateEmbedding(query)
    const results = await this.vectorSearch(embedding, limit)

    // Fetch full data
    const markets = await this.marketRepo.findByIds(results.map(r => r.id))

    // Sort by similarity
    return markets.sort((a, b) => {
      const scoreA = results.find(r => r.id === a.id)?.score || 0
      const scoreB = results.find(r => r.id === b.id)?.score || 0
      return scoreA - scoreB
    })
  }

  private async vectorSearch(embedding: number[], limit: number) {
    // Vector search implementation
  }
}
```

#### Middleware Pattern

```typescript
// Request/response processing pipeline
export function withAuth(handler: NextApiHandler): NextApiHandler {
  return async (req, res) => {
    const token = req.headers.authorization?.replace('Bearer ', '')

    // RFC 7807 problem+json bodies for auth failures (matches api-design)
    if (!token) {
      return res.status(401)
        .setHeader('Content-Type', 'application/problem+json')
        .json({
          type: 'https://example.com/errors/unauthorized',
          title: 'Unauthorized',
          status: 401,
          detail: 'Missing authorization token',
        })
    }

    try {
      const user = await verifyToken(token)
      req.user = user
      return handler(req, res)
    } catch (error) {
      return res.status(401)
        .setHeader('Content-Type', 'application/problem+json')
        .json({
          type: 'https://example.com/errors/unauthorized',
          title: 'Unauthorized',
          status: 401,
          detail: 'Invalid token',
        })
    }
  }
}

// Usage
export default withAuth(async (req, res) => {
  // Handler has access to req.user
})
```

---

### Database Patterns

#### Query Optimization

```typescript
// PASS: GOOD: Select only needed columns
const { data } = await supabase
  .from('markets')
  .select('id, name, status, volume')
  .eq('status', 'active')
  .order('volume', { ascending: false })
  .limit(10)

// FAIL: BAD: Select everything
const { data } = await supabase
  .from('markets')
  .select('*')
```

#### N+1 Query Prevention

```typescript
// FAIL: BAD: N+1 query problem
const markets = await getMarkets()
for (const market of markets) {
  market.creator = await getUser(market.creator_id)  // N queries
}

// PASS: GOOD: Batch fetch
const markets = await getMarkets()
const creatorIds = markets.map(m => m.creator_id)
const creators = await getUsers(creatorIds)  // 1 query
const creatorMap = new Map(creators.map(c => [c.id, c]))

markets.forEach(market => {
  market.creator = creatorMap.get(market.creator_id)
})
```

#### Transaction Pattern

```typescript
async function createMarketWithPosition(
  marketData: CreateMarketDto,
  positionData: CreatePositionDto
) {
  // Use Supabase transaction
  const { data, error } = await supabase.rpc('create_market_with_position', {
    market_data: marketData,
    position_data: positionData
  })

  if (error) throw new Error('Transaction failed')
  return data
}

// SQL function in Supabase
CREATE OR REPLACE FUNCTION create_market_with_position(
  market_data jsonb,
  position_data jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
BEGIN
  -- Start transaction automatically
  INSERT INTO markets VALUES (market_data);
  INSERT INTO positions VALUES (position_data);
  RETURN jsonb_build_object('success', true);
EXCEPTION
  WHEN OTHERS THEN
    -- Rollback happens automatically
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;
```

---

### Caching Strategies

#### Redis Caching Layer

```typescript
class CachedMarketRepository implements MarketRepository {
  constructor(
    private baseRepo: MarketRepository,
    private redis: RedisClient
  ) {}

  async findById(id: string): Promise<Market | null> {
    // Check cache first
    const cached = await this.redis.get(`market:${id}`)

    if (cached) {
      return JSON.parse(cached)
    }

    // Cache miss - fetch from database
    const market = await this.baseRepo.findById(id)

    if (market) {
      // Cache for 5 minutes
      await this.redis.setex(`market:${id}`, 300, JSON.stringify(market))
    }

    return market
  }

  async invalidateCache(id: string): Promise<void> {
    await this.redis.del(`market:${id}`)
  }
}
```

#### Cache-Aside Pattern

```typescript
async function getMarketWithCache(id: string): Promise<Market> {
  const cacheKey = `market:${id}`

  // Try cache
  const cached = await redis.get(cacheKey)
  if (cached) return JSON.parse(cached)

  // Cache miss - fetch from DB
  const market = await db.markets.findUnique({ where: { id } })

  if (!market) throw new Error('Market not found')

  // Update cache
  await redis.setex(cacheKey, 300, JSON.stringify(market))

  return market
}
```

---

### Error Handling Patterns

#### Centralized Error Handler

```typescript
class ApiError extends Error {
  constructor(
    public statusCode: number,
    public message: string,
    public isOperational = true
  ) {
    super(message)
    Object.setPrototypeOf(this, ApiError.prototype)
  }
}

// All error responses use RFC 7807 application/problem+json (matches the
// api-design skill). Shape: type, title, status, detail, instance, and an
// errors[] of { field, message, code } for field-level validation failures.
const PROBLEM_JSON = 'application/problem+json'

export function errorHandler(error: unknown, req: Request): Response {
  if (error instanceof ApiError) {
    return NextResponse.json({
      type: `https://example.com/errors/${error.statusCode}`,
      title: error.message,
      status: error.statusCode,
      detail: error.message,
      instance: new URL(req.url).pathname,
    }, { status: error.statusCode, headers: { 'Content-Type': PROBLEM_JSON } })
  }

  if (error instanceof z.ZodError) {
    // Map each Zod issue to a field-level error object, return 422
    return NextResponse.json({
      type: 'https://example.com/errors/validation',
      title: 'Validation Failed',
      status: 422,
      detail: `${error.errors.length} field(s) failed validation`,
      instance: new URL(req.url).pathname,
      errors: error.errors.map(e => ({
        field: e.path.join('.'),
        message: e.message,
        code: e.code,
      })),
    }, { status: 422, headers: { 'Content-Type': PROBLEM_JSON } })
  }

  // Log unexpected errors via pino (never console.error in production)
  logger.error({ err: error }, 'Unexpected error')

  return NextResponse.json({
    type: 'https://example.com/errors/internal',
    title: 'Internal Server Error',
    status: 500,
    detail: 'An unexpected error occurred',
    instance: new URL(req.url).pathname,
  }, { status: 500, headers: { 'Content-Type': PROBLEM_JSON } })
}

// Usage
export async function GET(request: Request) {
  try {
    const data = await fetchData()
    return NextResponse.json({ success: true, data })
  } catch (error) {
    return errorHandler(error, request)
  }
}
```

#### Retry with Exponential Backoff

```typescript
const BACKOFF_BASE_MS = 1000  // first retry waits 1s, then doubles
const BACKOFF_CAP_MS = 30_000  // upper bound on any single backoff delay

async function fetchWithRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3
): Promise<T> {
  let lastError: Error

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error as Error

      if (i < maxRetries - 1) {
        // Exponential backoff: 1s, 2s, 4s, capped at BACKOFF_CAP_MS
        const delay = Math.min(Math.pow(2, i) * BACKOFF_BASE_MS, BACKOFF_CAP_MS)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
  }

  throw lastError!
}

// Usage
const data = await fetchWithRetry(() => fetchFromAPI())
```

Concurrency (section 23): independent input and output work runs concurrently, not in
sequence. When two awaited calls have no data dependency (for example, fetching a record
and loading the caller's permissions), start both and await together with `Promise.all`
rather than awaiting one then the other.

```typescript
const [market, permissions] = await Promise.all([
  marketRepo.findById(id),
  authService.loadPermissions(userId),
])
```

---

### Authentication & Authorization

#### JWT Token Validation

```typescript
import jwt from 'jsonwebtoken'

interface JWTPayload {
  userId: string
  email: string
  role: 'admin' | 'user'
}

export function verifyToken(token: string): JWTPayload {
  try {
    const payload = jwt.verify(token, config.JWT_SECRET) as JWTPayload
    return payload
  } catch (error) {
    throw new ApiError(401, 'Invalid token')
  }
}

export async function requireAuth(request: Request) {
  const token = request.headers.get('authorization')?.replace('Bearer ', '')

  if (!token) {
    throw new ApiError(401, 'Missing authorization token')
  }

  return verifyToken(token)
}

// Usage in API route
export async function GET(request: Request) {
  const user = await requireAuth(request)

  const data = await getDataForUser(user.userId)

  return NextResponse.json({ success: true, data })
}
```

#### Role-Based Access Control

```typescript
type Permission = 'read' | 'write' | 'delete' | 'admin'

interface User {
  id: string
  role: 'admin' | 'moderator' | 'user'
}

const rolePermissions: Record<User['role'], Permission[]> = {
  admin: ['read', 'write', 'delete', 'admin'],
  moderator: ['read', 'write', 'delete'],
  user: ['read', 'write']
}

export function hasPermission(user: User, permission: Permission): boolean {
  return rolePermissions[user.role].includes(permission)
}

export function requirePermission(permission: Permission) {
  return (handler: (request: Request, user: User) => Promise<Response>) => {
    return async (request: Request) => {
      const user = await requireAuth(request)

      if (!hasPermission(user, permission)) {
        throw new ApiError(403, 'Insufficient permissions')
      }

      return handler(request, user)
    }
  }
}

// Usage - HOF wraps the handler
export const DELETE = requirePermission('delete')(
  async (request: Request, user: User) => {
    // Handler receives authenticated user with verified permission
    return new Response('Deleted', { status: 200 })
  }
)
```

---

### Rate Limiting

#### Simple In-Memory Rate Limiter

```typescript
class RateLimiter {
  private requests = new Map<string, number[]>()

  async checkLimit(
    identifier: string,
    maxRequests: number,
    windowMs: number
  ): Promise<boolean> {
    const now = Date.now()
    const requests = this.requests.get(identifier) || []

    // Remove old requests outside window
    const recentRequests = requests.filter(time => now - time < windowMs)

    if (recentRequests.length >= maxRequests) {
      return false  // Rate limit exceeded
    }

    // Add current request
    recentRequests.push(now)
    this.requests.set(identifier, recentRequests)

    return true
  }

  // Requests still allowed in the current window, for X-RateLimit-Remaining
  remaining(identifier: string, maxRequests: number, windowMs: number): number {
    const now = Date.now()
    const recent = (this.requests.get(identifier) || []).filter(time => now - time < windowMs)
    return Math.max(0, maxRequests - recent.length)
  }
}

const limiter = new RateLimiter()

export async function GET(request: Request) {
  const ip = request.headers.get('x-forwarded-for') || 'unknown'

  const limit = 100
  const windowMs = 60_000  // 100 req/min
  const allowed = await limiter.checkLimit(ip, limit, windowMs)
  const remaining = await limiter.remaining(ip, limit, windowMs)
  const resetSeconds = Math.ceil(windowMs / 1000)

  // Always advertise the standard rate-limit headers; on 429 add Retry-After
  // and return an RFC 7807 problem+json body (matches api-design)
  const rateLimitHeaders = {
    'X-RateLimit-Limit': String(limit),
    'X-RateLimit-Remaining': String(remaining),
    'X-RateLimit-Reset': String(resetSeconds),
  }

  if (!allowed) {
    return NextResponse.json({
      type: 'https://example.com/errors/rate-limit',
      title: 'Too Many Requests',
      status: 429,
      detail: 'Rate limit exceeded',
    }, {
      status: 429,
      headers: {
        ...rateLimitHeaders,
        'Content-Type': 'application/problem+json',
        'Retry-After': String(resetSeconds),
      },
    })
  }

  // Continue with request, echoing rate-limit headers on the success path
}
```

---

### Background Jobs & Queues

#### Simple Queue Pattern

```typescript
class JobQueue<T> {
  private queue: T[] = []
  private processing = false

  async add(job: T): Promise<void> {
    this.queue.push(job)

    if (!this.processing) {
      this.process()
    }
  }

  private async process(): Promise<void> {
    this.processing = true

    while (this.queue.length > 0) {
      const job = this.queue.shift()!

      try {
        await this.execute(job)
      } catch (error) {
        console.error('Job failed:', error)
      }
    }

    this.processing = false
  }

  private async execute(job: T): Promise<void> {
    // Job execution logic
  }
}

// Usage for indexing markets
interface IndexJob {
  marketId: string
}

const indexQueue = new JobQueue<IndexJob>()

export async function POST(request: Request) {
  const { marketId } = await request.json()

  // Add to queue instead of blocking
  await indexQueue.add({ marketId })

  return NextResponse.json({ success: true, message: 'Job queued' })
}
```

---

### Logging & Monitoring

#### Structured Logging with pino

Use pino for structured JSON logging, never use `console.log` in production code.
Every log entry on a request path must include `correlationId` and `requestId`.

```typescript
import pino from 'pino'
import { z } from 'zod'

// config.ts — typed config object; never access process.env directly in business logic
const configSchema = z.object({
  LOG_LEVEL: z.enum(['trace', 'debug', 'info', 'warn', 'error']).default('info'),
  JWT_SECRET: z.string().min(32),
  DATABASE_URL: z.string().url(),
  PORT: z.coerce.number().default(3000),
})
export const config = configSchema.parse(process.env)

// logger.ts
export const logger = pino({ level: config.LOG_LEVEL })

export function createRequestLogger(correlationId: string, requestId: string) {
  return logger.child({ correlationId, requestId })
}

// Usage in handler
export async function GET(request: Request) {
  const correlationId = request.headers.get('x-correlation-id') ?? crypto.randomUUID()
  const requestId = crypto.randomUUID()
  const log = createRequestLogger(correlationId, requestId)

  log.info({ method: 'GET', path: '/api/markets' }, 'Fetching markets')

  try {
    const markets = await fetchMarkets()
    return NextResponse.json({ success: true, data: markets })
  } catch (error) {
    log.error({ err: error }, 'Failed to fetch markets')
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}
```

Rules:
- Never use `console.log`, `console.error`, or `console.warn` in production code: use pino
- Never access `process.env` directly in business logic: use a validated typed config object
- Every log entry on a request path must carry `correlationId` and `requestId`
```

Remember: Backend patterns enable scalable, maintainable server-side applications. Choose patterns that fit your complexity level.

---

## State Modeling

### Discriminated Unions (Required)

Model async state as discriminated unions — never as nullable optional fields:

```typescript
// BAD — nullable fields for loading state
type UserState = {
  loading: boolean
  error: Error | null
  user: User | null
}

// GOOD — discriminated union
type UserState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: User }
  | { status: 'error'; error: Error }

// Usage forces exhaustive handling:
switch (state.status) {
  case 'idle': return null
  case 'loading': return <Spinner />
  case 'success': return <UserCard user={state.data} />
  case 'error': return <ErrorMessage error={state.error} />
}
```

---

### Environment & Configuration

Never access `process.env` directly in business logic. Always use a validated typed config object:

```typescript
import { z } from 'zod'

const schema = z.object({
  JWT_SECRET: z.string().min(32),
  DATABASE_URL: z.string().url(),
  PORT: z.coerce.number().default(3000),
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
})

export const config = schema.parse(process.env)
// Throws at startup if env vars are missing or invalid — fail fast
```

---

### Startup readiness log

See [observability-and-logging](../observability-and-logging/SKILL.md) → "Startup readiness log" for the universal
convention (ANSI Shadow
banner, URL + profile + dependency + observability sections, 2-second probe timeouts, `<url> [Connected|Warning|FAILED]`
result format).

Node / Express hook: `server.on('listening', ...)` after `app.listen()`. For NestJS, the post-`app.listen()` line in
`bootstrap()`. For Next.js custom server, the post-bind callback.

```typescript
const server = app.listen(config.PORT, () => {
  // One log call, leading '\n'. Pino / Winston stamp a timestamp + level per call;
  // splitting the banner across many log calls would shred the art. See canonical
  // rule in coding-standards "Emit the whole block in ONE log call with a leading \n".
  logger.info('\n' + buildStartupLog())
})
```

Probe timeouts: `fetch(url, { signal: AbortSignal.timeout(2000) })` so unreachable dependencies don't stall the banner.
Catch with `.catch(...)`, log the detail at debug, surface only `[FAILED]`.

```typescript
async function probe(url: string): Promise<string> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(2000) })
    return res.ok ? `${url} [Connected]` : `${url} [Warning] (status=${res.status})`
  } catch (err) {
    logger.debug({ url, err }, 'startup probe failed')
    return `${url} [FAILED]`
  }
}
```

---

### Graceful Shutdown

```typescript
const shutdown = async (signal: string) => {
  logger.info({ signal }, 'Shutdown received')
  server.close(async () => {
    await db.end()
    await redis.quit()
    process.exit(0)
  })
  // Force exit if drain takes too long
  setTimeout(() => { logger.error('Forced shutdown'); process.exit(1) }, 30_000)
}

process.on('SIGTERM', () => shutdown('SIGTERM'))
process.on('SIGINT', () => shutdown('SIGINT'))
