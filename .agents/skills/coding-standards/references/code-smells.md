# Code Smells

Contents:

- [1. Long Functions](#1-long-functions)
- [2. Deep Nesting](#2-deep-nesting)
- [3. Magic Numbers](#3-magic-numbers)
- [4. Oversized Files](#4-oversized-files)

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

A named constant is right for a value the algorithm or the protocol fixes. A value someone would tune per environment, such as a retry count against a flaky upstream, a schedule, a timeout, a bucket size or a business maximum, goes to validated configuration instead, so changing it needs no release. `java-coding-standards` shows the Spring form.

---

### 4. Oversized Files

A class, module, component, hook or test file past about 300 lines is almost always doing several jobs, and no reader holds it in their head. Split it by responsibility, the reason each part would change, not by line count: a parser, a validator and a writer become three modules, a page component loses its form and its table to their own files, and a test file splits by the behaviour each group of tests covers, sharing one fixtures module.

Fail: `lib/api/expenses.ts` at 600 lines holding the types, the request builders, the response mappers and every endpoint call, and `eml_to_md.py` doing argument parsing, MIME walking, HTML cleanup and file output in one module.

Pass: a folder per API area with one file per concern, and a thin command-line entry point that calls pure helper modules.

```text
lib/api/expenses/
  types.ts
  requests.ts
  mappers.ts
  index.ts
```

Add an `index.ts` barrel only when something needs one stable import path, such as existing imports across the app or a test that mocks the whole module by path. Otherwise import the file directly, because a barrel nobody needs hides where a symbol lives and widens what every importer loads.

A generated file, such as API types emitted by `openapi-typescript`, is the exception: it is not read or edited by hand, so it is not split, and `git-workflow` marks it as generated instead.
