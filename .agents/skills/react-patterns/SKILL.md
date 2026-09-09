---
name: react-patterns
description: React patterns for component composition, custom hooks, async state, a typed API client, memoisation, code splitting, virtualisation, forms, and animation. Use when you say "build a React component", "write a custom hook", "this list re-renders on every keystroke", "lazy load this chart", or "animate this list on mount". Not for Next.js rendering, routing, and caching, use `nextjs-app-router-patterns`.
license: Apache-2.0
---

# React Development Patterns

React patterns for maintainable, performant user interfaces, covering composition, hooks, async state, data access,
performance, forms, and animation. Everything here is framework-agnostic React that works the same inside or outside a
meta-framework.

Baseline: React 19 with TypeScript. Server Components, streaming, and route-level caching belong to
`nextjs-app-router-patterns`, and this skill defers to it on all three.

---

### When to activate

- Building React components: composition, props, rendering, compound components.
- Managing state with `useState`, `useReducer`, Context, or a store such as Zustand.
- Implementing client-side data fetching with SWR, React Query, or a typed API client.
- Optimising rendering: memoisation, virtualisation, code splitting.
- Working with forms: validation, controlled inputs, schema parsing.
- Handling client-side routing and navigation.
- Adding animation to a React interface.

---

### When not to activate

- Server Components, streaming, route caching, Server Actions, route handlers. Use `nextjs-app-router-patterns`.
- Visual direction, typography, composition, and motion direction. Use `frontend-design`.
- Tokens, theming, and stylesheet architecture. Use `design-system`.
- WCAG conformance, ARIA semantics, and screen-reader behaviour. Use `web-accessibility`.
- Angular components, signals, and RxJS. Use `angular`.
- Profiling and Core Web Vitals work beyond React-level fixes. Use `performance-optimization`.

---

### Reference map

| Task | Open |
| --- | --- |
| Context and reducer stores, custom state hooks, debouncing | [references/state-management.md](references/state-management.md) |
| The typed API client, async data hooks, render props loaders | [references/data-fetching.md](references/data-fetching.md) |
| Controlled forms, validation, error boundaries, i18n wiring | [references/forms.md](references/forms.md) |
| Animation with `motion/react`, reduced motion, timing budgets | [references/animation.md](references/animation.md) |
| Keyboard navigation and focus management in React | [references/accessibility.md](references/accessibility.md) |

---

### Declare components as named functions

Named declarations hoist, give clearer stack traces and DevTools names, and read consistently across a file. Reserve
arrow functions for callbacks and inline handlers.

```typescript
// PASS: named declaration, name survives into DevTools and stack traces
export function MarketCard({ market }: MarketCardProps) {
  return <article className="market-card">{market.name}</article>
}

// FAIL: anonymous arrow assigned to a const, worse traces and no hoisting
export const MarketCard = ({ market }: MarketCardProps) => (
  <article className="market-card">{market.name}</article>
)
```

---

### Compose components, never inherit

Build a family of small pieces that slot into each other. Inheritance in React produces components with a props
surface that only grows.

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
in [references/state-management.md](references/state-management.md).

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

The client module itself is in [references/data-fetching.md](references/data-fetching.md).

---

### Memoise only what you measured

`useMemo`, `useCallback`, and `React.memo` each add a dependency array to maintain and a cache to hold, and a wrong
dependency list is its own class of bug. Reaching for them reflexively on cheap work costs more than it saves. Note
also that `Array.prototype.sort` mutates, so copy before sorting or you mutate a prop.

```typescript
// PASS: a measured expensive transform, and a copy before sorting
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
[references/data-fetching.md](references/data-fetching.md).

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

---

### Doc Comments

Default to none. A doc comment is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named component or hook, rename the props so they carry their own meaning, and tighten
the types. Do that first and most doc comments have nothing left to say, which is the outcome you want. Code that
explains itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@param` and `@returns` and `@throws` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `@param` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or
   who owns the argument afterwards. `@param userId - The user identifier` is noise, delete it, and never restate a
   type TypeScript already declares.
3. `@returns` only when it is non-obvious.
4. `@throws` always, for every error a caller can act on. TypeScript keeps throws out of the signature, so this one is
   genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

```typescript
// PASS: one sentence, then only what the signature cannot say
/**
 * Subscribes to live price updates for one market.
 *
 * @returns null until the first message arrives
 */
export function useMarketPrice(marketId: string): Price | null { ... }

// FAIL: restates the signature and the hook name
/**
 * Hook for market price.
 *
 * @param marketId - The market id
 * @returns The price
 */
export function useMarketPrice(marketId: string): Price | null { ... }
```

---

### Related skills

- `nextjs-app-router-patterns` owns Server Components, streaming, route caching, Server Actions, and route handlers.
  This skill does not cover them.
- `web-accessibility` owns WCAG conformance, ARIA semantics, and screen-reader behaviour. The React mechanics for
  keyboard and focus are in [references/accessibility.md](references/accessibility.md), the requirements are there.
- `frontend-design` for visual direction and motion direction.
- `design-system` for tokens, theming, and stylesheet architecture.
- `performance-optimization` for profiling and Core Web Vitals work beyond React-level fixes.
- `e2e-testing` for driving these components in a browser.
- `coding-standards` for the shared engineering floor these patterns sit on.

---

### Checklist

- Every top-level component is a named function declaration.
- Component families are composed, not configured through a growing flag surface.
- Every async operation exposes one `AsyncState` union, not separate data, loading, and error flags.
- No component or hook calls `fetch` directly, and every endpoint lives in the typed API client.
- Every `useMemo`, `useCallback`, and `React.memo` traces back to a measurement.
- No sort, splice, or reverse mutates a prop or a state value in place.
- Heavy client-only modules are lazy loaded, and lists past a few hundred rows are virtualised.
- Every user-facing string goes through the i18n layer.
- Every animation respects `prefers-reduced-motion`.
- No doc comment restates a signature, and every recoverable error is documented with `@throws`.
