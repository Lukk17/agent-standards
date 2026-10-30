# Data Fetching and Rendering Cost

The typed API client, the hooks and loaders that consume it, and the two rendering costs worth engineering around.

---

### Contents

- The API client
- The async data hook
- Render props loader
- Code splitting
- Virtualisation

---

### The API client

One module owns the base URL, the headers, the auth, and the response typing. Components and hooks call it. Nothing
else calls `fetch`.

```typescript
// lib/api/client.ts
async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`)
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  markets: {
    list: () => request<Market[]>('/markets'),
    get: (id: string) => request<Market>(`/markets/${id}`),
  },
}
```

```typescript
const markets = await api.markets.list()
```

Changing the auth scheme, adding a request id header, or swapping the base URL for a test environment is then one
edit rather than a search across the component tree.

---

### The async data hook

The hook exposes one `state` value of the `AsyncState<T>` union, not separate data, loading, and error flags. The
fetcher passed in is a method on the API client.

```typescript
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; reason: Error }

interface UseQueryOptions<T> {
  onSuccess?: (data: T) => void
  onError?: (error: Error) => void
  enabled?: boolean
}

export function useQuery<T>(
  key: string,
  fetcher: () => Promise<T>,
  options?: UseQueryOptions<T>
) {
  const [state, setState] = useState<AsyncState<T>>({ status: 'idle' })
  const [attempt, setAttempt] = useState(0)
  const latest = useRef({ fetcher, options })
  const enabled = options?.enabled !== false

  useEffect(() => {
    latest.current = { fetcher, options }
  })

  useEffect(() => {
    if (!enabled) return
    let active = true
    setState({ status: 'loading' })

    latest.current
      .fetcher()
      .then((data) => {
        if (!active) return
        setState({ status: 'success', data })
        latest.current.options?.onSuccess?.(data)
      })
      .catch((err: unknown) => {
        if (!active) return
        const reason = err instanceof Error ? err : new Error(String(err))
        setState({ status: 'error', reason })
        latest.current.options?.onError?.(reason)
      })

    return () => {
      active = false
    }
  }, [key, enabled, attempt])

  const refetch = useCallback(() => setAttempt((n) => n + 1), [])
  return { state, refetch }
}
```

The `active` flag, set to false in the cleanup, drops a response that lands after `key` changed, because network responses can arrive in a different order than they were sent, and without it a slow answer for the old key overwrites the new one. `fetcher` and the callbacks sit in a ref, so an inline arrow or an options object literal does not re-run the effect on every render. Only `key`, `enabled`, and an explicit `refetch` do.

Fail: the fetch started from a `useCallback` that depends on `[fetcher, options]`, with no cleanup flag, so every render with an inline `options` object builds a new callback and an old response can still win the race.

Write this yourself only for something small. Caching across components, deduplication, and background revalidation
are why SWR and React Query exist, and reimplementing them is not a good use of a sprint.

---

### Render props loader

Useful when the caller needs to control the markup for each status rather than accept a fixed layout. The `active`
flag stops a resolved promise from writing state into an unmounted component.

```typescript
interface DataLoaderProps<T> {
  load: () => Promise<T>
  children: (state: AsyncState<T>) => React.ReactNode
}

export function DataLoader<T>({ load, children }: DataLoaderProps<T>) {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading' })

  useEffect(() => {
    let active = true
    load()
      .then((data) => active && setState({ status: 'success', data }))
      .catch((reason: Error) => active && setState({ status: 'error', reason }))
    return () => {
      active = false
    }
  }, [load])

  return <>{children(state)}</>
}
```

```typescript
<DataLoader<Market[]> load={() => api.markets.list()}>
  {(state) => {
    switch (state.status) {
      case 'loading':
        return <Spinner />
      case 'error':
        return <ErrorMessage error={state.reason} />
      case 'success':
        return <MarketList markets={state.data} />
      default:
        return null
    }
  }}
</DataLoader>
```

---

### Code splitting

Route-level splitting is usually handled by the router. What is left is the heavy component inside a route: a chart
library, a rich text editor, a 3D scene. Split those and give each a fallback that holds the layout.

```typescript
import { lazy, Suspense } from 'react'

const HeavyChart = lazy(() => import('./HeavyChart'))
const ThreeJsBackground = lazy(() => import('./ThreeJsBackground'))

export function Dashboard() {
  return (
    <div>
      <Suspense fallback={<ChartSkeleton />}>
        <HeavyChart data={data} />
      </Suspense>

      <Suspense fallback={null}>
        <ThreeJsBackground />
      </Suspense>
    </div>
  )
}
```

A `null` fallback is right only for decoration that nobody waits for. Content regions get a skeleton sized like the
content, so the layout does not jump when it arrives.

---

### Virtualisation

Past a few hundred rows, mounting every row costs more than the scroll it enables. A virtualiser renders the visible
window plus a small overscan and positions the rows absolutely inside a spacer of the full height.

```typescript
import { useVirtualizer } from '@tanstack/react-virtual'

export function VirtualMarketList({ markets }: { markets: Market[] }) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: markets.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,
    overscan: 5,
  })

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            <MarketCard market={markets[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  )
}
```

Virtualised lists hide rows from find-in-page and can confuse a screen reader if the container is not described. Set
the list semantics and the item count explicitly, and check the result against `web-accessibility`.
