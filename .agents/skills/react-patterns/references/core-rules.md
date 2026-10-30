# React Core Rules in Depth

The Pass and Fail examples and the reasoning behind each rule the SKILL.md hub states in one or two lines. Open it when a hub rule needs its worked form or its full explanation. Written for React 19 with TypeScript and React Compiler.

---

### Contents

- Declare components as named functions
- Compose components, never inherit
- Model async state as one discriminated union
- Route every network call through one typed API client
- Let the compiler memoise, and measure the rest
- Load heavy modules lazily and virtualise long lists
- Send every user-facing string through the i18n layer

---

### Declare components as named functions

Named declarations hoist and read consistently across a file. Reserve arrow functions for callbacks and inline handlers. The component name is not the reason: an arrow assigned to a const infers its name from the variable, so DevTools and stack traces show it either way.

```typescript
// PASS: named declaration, hoisted, and shaped like every other component in the file
export function MarketCard({ market }: MarketCardProps) {
  return <article className="market-card">{market.name}</article>
}

// FAIL: arrow assigned to a const, not hoisted, and inconsistent with the rest of the file
export const MarketCard = ({ market }: MarketCardProps) => (
  <article className="market-card">{market.name}</article>
)
```

---

### Compose components, never inherit

Build a family of small pieces that slot into each other. Inheritance in React produces components with a props
surface that only grows. Error boundaries are the one exception, because React supports them only as class components.

```typescript
// PASS: composed pieces, each with one job
export function Card({ children, variant = 'default' }: CardProps) {
  return <div className={`card card-${variant}`}>{children}</div>
}
export function CardHeader({ children }: { children: React.ReactNode }) {
  return <div className="card-header">{children}</div>
}

// FAIL: one component branching on flags for every caller
export function Card({ children, isHeader, isBody, isOutlined, isCompact, hasIcon }: EverythingProps) { ... }
```

Compound components (Tabs, Accordion, Menu) share state through a context created by the parent. The full pattern is
in [references/state-management.md](state-management.md).

---

### Model async state as one discriminated union

Three loose flags let impossible combinations exist: loading and error and data all set at once. One union value makes
those unrepresentable, and callers switch on `state.status`.

```typescript
// PASS: one value, impossible states cannot be constructed
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; reason: Error }

// FAIL: three flags that can contradict each other
const [data, setData] = useState<T | null>(null)
const [loading, setLoading] = useState(false)
const [error, setError] = useState<Error | null>(null)
```

---

### Route every network call through one typed API client

The base URL, the headers, the auth, and the response typing belong in one module. Components and hooks call the
client, which keeps endpoint strings out of the UI and makes an auth or base-URL change a one-file edit.

```typescript
// PASS: the component asks the client for markets
const markets = await api.markets.list()

// FAIL: a URL, a status check, and an untyped body in a component
const res = await fetch('https://api.example.com/markets')
const markets = await res.json()
```

The client module itself is in [references/data-fetching.md](data-fetching.md).

---

### Let the compiler memoise, and measure the rest

With React Compiler enabled, which is stable and React's recommendation for new code, do not hand-write `useMemo`, `useCallback`, or `React.memo`. The compiler memoises components and values for you. Keep the hooks only as escape hatches for precise control, the common case being a value used as an effect dependency that must not change identity on every render. In existing code, leave current memoisation in place unless a test proves removing it is safe, because removing it can change what the compiler emits.

Without the compiler, memoise only what you measured. `useMemo`, `useCallback`, and `React.memo` each add a dependency array to maintain and a cache to hold, and a wrong dependency list is its own class of bug. Either way, `Array.prototype.sort` mutates, so copy before sorting or you mutate a prop.

```typescript
// PASS: no project compiler, so a measured expensive transform is memoised, and copied before sorting
const sortedMarkets = useMemo(() => [...markets].sort((a, b) => b.volume - a.volume), [markets])

// FAIL: memoising a string concatenation, and sorting the prop in place
const label = useMemo(() => `${market.name} (${market.id})`, [market])
const sorted = markets.sort((a, b) => b.volume - a.volume)
```

---

### Load heavy modules lazily and virtualise long lists

A charting or 3D library in the entry bundle delays every route that does not use it. A list of thousands of rows
renders thousands of DOM nodes the user will never scroll to.

```typescript
// PASS: heavy component split behind Suspense, long list virtualised
const HeavyChart = lazy(() => import('./HeavyChart'))
const virtualizer = useVirtualizer({ count: markets.length, getScrollElement: () => parentRef.current })

// FAIL: the library ships to every route, and 10,000 cards mount at once
import { HeavyChart } from './HeavyChart'
{markets.map((market) => <MarketCard key={market.id} market={market} />)}
```

The full virtualisation and code-splitting examples are in
[references/data-fetching.md](data-fetching.md).

---

### Send every user-facing string through the i18n layer

A literal in JSX is a string that cannot be translated and cannot be changed without a code edit. Every label,
placeholder, button, and message is looked up by key.

```typescript
// PASS: copy lives in the catalogue
<button type="submit">{t('common.save')}</button>

// FAIL: copy welded into the component
<button type="submit">Save</button>
```
