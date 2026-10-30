# TypeScript and JavaScript Examples

Contents:

- [Variable naming](#variable-naming)
- [Function naming](#function-naming)
- [Immutability](#immutability)
- [Error handling](#error-handling)
- [Independent async calls](#independent-async-calls)
- [Type safety](#type-safety)

Worked pass and fail pairs for the language-neutral rules in SKILL.md, written in TypeScript. Load this file when you
want a concrete example of a rule rather than its statement, or when the code under review is TypeScript or
JavaScript. Every pass example compiles under `strict`, given the domain types it names.

---

### Variable naming

Pass:

```typescript
const marketSearchQuery = 'election'
const isUserAuthenticated = session !== null
const totalRevenueCents = orders.reduce((sum, order) => sum + order.totalCents, 0)
```

Fail:

```typescript
const q = 'election'
const flag = session !== null
const x = orders.reduce((sum, order) => sum + order.totalCents, 0)
```

---

### Function naming

Verb then noun, and a boolean-returning function reads as a question.

Pass:

```typescript
async function fetchMarketData(marketId: string): Promise<Market> {
  return marketClient.get(marketId)
}

function isValidEmail(email: string): boolean {
  return EMAIL_PATTERN.test(email)
}
```

Fail:

```typescript
async function market(id: string): Promise<Market> {
  return marketClient.get(id)
}

function email(e: string): boolean {
  return EMAIL_PATTERN.test(e)
}
```

---

### Immutability

Return a new value instead of mutating state that other code holds. Spread is a shallow copy, so a nested object
still shared with the original needs its own copy.

Pass:

```typescript
const renamedUser = { ...user, name: 'New Name' }
const movedUser = { ...user, address: { ...user.address, city: 'Lyon' } }
const extendedItems = [...items, newItem]
```

Fail, for state another component or caller still holds:

```typescript
user.name = 'New Name'
user.address.city = 'Lyon'
items.push(newItem)
```

A local array built and returned inside one function is not shared state, and pushing to it is fine.

---

### Error handling

Throw a specific error type, keep no local `try` unless it translates a failure into a domain error, and let the caller
or the global handler decide what happens next.

Pass:

```typescript
async function fetchMarket(url: string): Promise<Market> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new MarketFetchError(response.status, url)
  }
  return MarketSchema.parse(await response.json())
}
```

Fail, a generic error, caught by its own function and wrapped a second time:

```typescript
async function fetchMarket(url: string): Promise<Market> {
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return await response.json()
  } catch (error) {
    throw new Error('Failed to fetch data', { cause: error })
  }
}
```

---

### Independent async calls

Run calls that do not depend on each other concurrently.

Pass:

```typescript
const [users, markets, stats] = await Promise.all([fetchUsers(), fetchMarkets(), fetchStats()])
```

Fail:

```typescript
const users = await fetchUsers()
const markets = await fetchMarkets()
const stats = await fetchStats()
```

---

### Type safety

Model the domain with precise types, and keep `any` out of every signature.

Pass:

```typescript
interface Market {
  id: string
  name: string
  status: 'active' | 'resolved' | 'closed'
  createdAt: Date
}

async function getMarket(id: string): Promise<Market> {
  return MarketSchema.parse(await marketClient.get(id))
}
```

Fail:

```typescript
async function getMarket(id: any): Promise<any> {
  return marketClient.get(id)
}
```
