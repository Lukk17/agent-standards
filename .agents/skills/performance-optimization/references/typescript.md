# Performance Examples in TypeScript

The pass and fail code in TypeScript for running independent IO concurrently. Open this when the slow path is TypeScript or JavaScript. The reasoning, and the two rules that hold in any language, are in [worked-examples.md](worked-examples.md).

---

### Run independent IO concurrently

Fail (TypeScript): three independent calls cost the sum of their latencies.

```typescript
const profile = await api.getProfile(userId)
const orders = await api.getOrders(userId)
const preferences = await api.getPreferences(userId)
```

Pass (TypeScript): they cost the slowest one.

```typescript
const [profile, orders, preferences] = await Promise.all([
  api.getProfile(userId),
  api.getOrders(userId),
  api.getPreferences(userId),
])
```
