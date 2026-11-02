# Code Smells

Shapes that mean the code needs restructuring rather than a comment. Each entry gives the failing form and the
repair. Load this file during a review pass, or when a function feels wrong and you need a name for why.

---

### 1. Long Functions

Fail, one function doing every phase:

```typescript
function processMarketData(raw: RawMarket[]): void {
  // validation, transformation and persistence, 100 lines in one body
}
```

Pass, one function per phase, and the top level reads as the summary:

```typescript
function processMarketData(raw: RawMarket[]): Promise<void> {
  const validated = validateMarkets(raw)
  const transformed = toMarketRecords(validated)
  return saveMarketRecords(transformed)
}
```

---

### 2. Deep Nesting

Fail, five levels before the work starts:

```typescript
function closeMarket(user: User | null, market: Market | null, hasPermission: boolean): void {
  if (user) {
    if (user.isAdmin) {
      if (market) {
        if (market.isActive) {
          if (hasPermission) {
            marketService.close(market.id)
          }
        }
      }
    }
  }
}
```

Pass, guard clauses and early returns:

```typescript
function closeMarket(user: User | null, market: Market | null, hasPermission: boolean): void {
  if (!user?.isAdmin) {
    return
  }
  if (!market?.isActive) {
    return
  }
  if (!hasPermission) {
    return
  }

  marketService.close(market.id)
}
```

---

### 3. Magic Numbers

Fail:

```typescript
if (retryCount > 3) {
  giveUp()
}
setTimeout(callback, 500)
```

Pass:

```typescript
const MAX_RETRIES = 3
const DEBOUNCE_DELAY_MS = 500

if (retryCount > MAX_RETRIES) {
  giveUp()
}
setTimeout(callback, DEBOUNCE_DELAY_MS)
```
