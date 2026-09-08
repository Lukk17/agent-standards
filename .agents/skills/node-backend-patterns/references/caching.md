# Caching in Node services

Read this when adding a cache in front of a repository, choosing a TTL, or debugging stale reads.

---

### Decorate the repository, do not scatter cache calls

Keep the cache in one decorator that implements the same port as the real repository. Callers stay unaware, and the
invalidation rule lives next to the read that populates the entry.

```typescript
class CachedMarketRepository implements MarketRepository {
  constructor(private readonly inner: MarketRepository, private readonly redis: RedisClient) {}

  async findById(id: string): Promise<Market | null> {
    const key = `market:${id}`
    const cached = await this.redis.get(key)
    if (cached) return JSON.parse(cached) as Market

    const market = await this.inner.findById(id)
    if (market) await this.redis.set(key, JSON.stringify(market), { EX: 300 })
    return market
  }

  async update(id: string, data: UpdateMarketDto): Promise<Market> {
    const market = await this.inner.update(id, data)
    await this.redis.del(`market:${id}`)
    return market
  }
}
```

Fail: a `getMarket()` helper that reads Redis inline, plus three write paths that each forget a different key.

---

### Key naming

Use `<entity>:<version>:<identifier>`, for example `market:v2:abc-123`. The version segment lets a shape change roll out
without a flush: bump it, and every old entry ages out on its own TTL. Never build a key from an unvalidated request
parameter, because an attacker controls what you write into shared memory.

---

### Pick the TTL from the tolerated staleness

Write the number the product accepts, not a round number that felt safe.

| Data | TTL | Reason |
| --- | --- | --- |
| Reference data (countries, plans) | hours | changes on deploy, not on traffic |
| User profile | 60 to 300 seconds | visible staleness annoys the owner of the record |
| Prices, balances, permissions | do not cache, or cache under 5 seconds | a stale read is a correctness bug |
| Rendered list pages | 30 to 60 seconds | absorbs bursts without hiding new rows for long |

---

### Invalidate on write, never on a timer alone

Every write path that changes a cached entity deletes its keys in the same function that performs the write. A TTL is
the backstop for the key you forgot, not the mechanism.

Pass: the update method above deletes `market:${id}` before returning.

Fail: a nightly job that flushes the whole cache to "keep it fresh", which produces a daily thundering herd against the
database.

---

### Guard against the stampede

When a hot key expires under load, every in-flight request misses at once and hits the database together. Collapse
concurrent misses onto one in-flight promise per key.

```typescript
const inFlight = new Map<string, Promise<Market | null>>()

function loadOnce(key: string, load: () => Promise<Market | null>): Promise<Market | null> {
  const existing = inFlight.get(key)
  if (existing) return existing

  const promise = load().finally(() => inFlight.delete(key))
  inFlight.set(key, promise)
  return promise
}
```

For a multi-process deployment this only collapses misses inside one process. Add a short Redis lock, or accept the
remaining fan-out, when the origin query is expensive enough to matter.

---

### Never let a cache failure fail the request

Redis being down must degrade throughput, not availability. Wrap the cache read and the cache write in their own
try/catch, log at warn, and continue to the origin.

```typescript
async function readCache(redis: RedisClient, key: string): Promise<string | null> {
  try {
    return await redis.get(key)
  } catch (err) {
    logger.warn({ err, key }, 'cache read failed, falling through to origin')
    return null
  }
}
```

---

### Do not cache what belongs to one user in a shared key

An authorization-dependent response cached under a key that omits the subject leaks one user's data to the next. Either
put the subject in the key, or cache the unfiltered rows and apply authorization after the read.

---

### HTTP caching is a separate layer

`Cache-Control`, `ETag`, and `304 Not Modified` live on the response, not in Redis. They are covered by `api-design`
under conditional requests. Set both when the resource is public and cheap to revalidate.

---

### Related skills

- `node-backend-patterns` for the hub these rules belong to.
- `api-design` for `ETag`, `Cache-Control`, and conditional requests on the wire.
- `postgres-patterns` when the right fix is an index rather than a cache.
