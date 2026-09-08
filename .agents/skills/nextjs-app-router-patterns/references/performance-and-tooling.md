# Performance and Tooling

Images, bundle size, and the dev server. Baseline: Next.js 16 or newer, where Turbopack is the default dev bundler.

---

### Images

`next/image` negotiates the format, generates the responsive set, lazy-loads below the fold, and reserves layout
space so the page does not shift when the file lands. A raw `img` tag gives up all of that.

```tsx
import Image from 'next/image'

export function ProductHero({ product }: { product: Product }) {
  return (
    <Image
      src={product.image}
      alt={product.name}
      width={1200}
      height={630}
      priority
      placeholder="blur"
      blurDataURL={product.blurDataUrl}
      sizes="(min-width: 1024px) 50vw, 100vw"
    />
  )
}
```

- `priority` on the largest above-the-fold image, and on nothing else. Marking everything priority defeats it.
- `sizes` whenever the rendered width varies by breakpoint, otherwise the browser downloads the largest candidate.
- `placeholder="blur"` for content images, so the space is filled rather than blank while loading.
- A real `alt` that says what the image conveys, or `alt=""` when it is purely decorative.

---

### Bundle splitting

Route-based code splitting is automatic. What is not automatic is a heavy dependency pulled into a shared client
component, so load it dynamically and let the route render without it.

```typescript
import dynamic from 'next/dynamic'

const RevenueChart = dynamic(() => import('@/components/RevenueChart'), {
  loading: () => <ChartSkeleton />,
})

const MapView = dynamic(() => import('@/components/MapView'), {
  ssr: false,
})
```

Use `ssr: false` only for a component that genuinely cannot render on the server, such as one that touches `window`
at module scope. It costs you the server-rendered markup for that region.

Before splitting anything, check that the module needs to be on the client at all. Moving a formatting or parsing
library into a Server Component removes it from the bundle entirely, which beats deferring it.

---

### Turbopack

Turbopack is an incremental bundler written in Rust and is the default for `next dev`. It keeps a filesystem cache
under `.next`, so a restart reuses previous work instead of rebuilding from scratch. Large projects see the biggest
difference on cold start and on hot updates.

Run the dev server.

```bash
next dev
```

Build for production.

```bash
next build
```

Serve the production build.

```bash
next start
```

Fall back to webpack only for a specific, recorded reason, such as a dev-only plugin with no Turbopack equivalent.

```bash
next dev --webpack
```

When dev feels slow, check these in order.

1. Confirm the dev server is actually on Turbopack and not on a webpack fallback flag left in a script.
2. Confirm the `.next` cache is not being deleted by a watch script, a container mount, or a clean step in the dev
   command.
3. Confirm no client component barrel file is pulling an entire library in for one export.
4. Then look at the bundle.

---

### Bundle analysis

Next.js ships bundle analysis for inspecting output and finding heavy dependencies. Enable it in the project config
for the version you are on, then read it with one question in mind: which module is in a client bundle that has no
business being there. Move it to the server, split it, or replace it.

Check the version-specific configuration in the Next.js documentation before wiring it up, because the flag and the
config key have moved between releases.
