---
name: nextjs-app-router-patterns
description: Next.js App Router architecture covering Server and Client Components, caching, streaming, Server Actions, route handlers, metadata, images, and Turbopack dev tuning. Use when you say "build a Next.js page", "server or client component", "revalidate this fetch", "add a server action", "parallel routes for a dashboard", or "next dev is slow". Not for framework-agnostic React state, hooks, and animation, use `frontend-patterns`.
license: Apache-2.0
---

# Next.js App Router Patterns

Architecture rules for Next.js applications built on the App Router, from the Server and Client Component split down
to caching, mutations, and dev-server tuning. Every rule here is about where code runs and when its output goes stale.

Baseline: current stable Next.js on the App Router, meaning Next.js 16 or newer, where Turbopack is the default dev
bundler and `params` and `searchParams` arrive as promises.

---

### When to activate

- Building or reviewing any route, layout, or component in an `app/` directory.
- Deciding whether a component belongs on the server or the client.
- Choosing a caching or revalidation strategy for fetched data.
- Adding a Server Action, a route handler, or per-route metadata.
- Migrating a Pages Router application to the App Router.
- Diagnosing a slow `next dev` start or a slow hot update.

---

### When not to activate

- Framework-agnostic React work: component composition, hooks, forms, animation. Use `frontend-patterns`.
- Visual direction, typography, and composition decisions. Use `frontend-design`.
- Token architecture and theming. Use `design-system`.
- Keyboard, focus, ARIA, and contrast requirements. Use `web-accessibility`.
- Titles, meta descriptions, structured data, and keyword mapping. Use `seo`.
- Profiling and Core Web Vitals remediation beyond the Next.js primitives. Use `performance-optimization`.

---

### Reference map

| Task | Open |
| --- | --- |
| Server and Client split, streaming, caching layers | [references/rendering-and-data.md](references/rendering-and-data.md) |
| File conventions, parallel and intercepting routes, route handlers, metadata | [references/routing.md](references/routing.md) |
| Server Actions, form mutations, revalidation | [references/server-actions.md](references/server-actions.md) |
| Images, bundle splitting, Turbopack, bundle analysis | [references/performance-and-tooling.md](references/performance-and-tooling.md) |

---

### Keep components on the server until interactivity forces otherwise

A Server Component ships no JavaScript to the browser and can reach the database directly. Add `'use client'` only at
the leaf that needs state, an effect, or a DOM event handler, then keep that leaf small.

```typescript
// PASS: server parent fetches, client leaf handles the click
export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const product = await db.product.findUnique({ where: { id } })
  return <ProductDetail product={product}><AddToCartButton productId={id} /></ProductDetail>
}

// FAIL: the whole page becomes a client bundle for one button
'use client'
export default function ProductPage({ id }: { id: string }) {
  const [product, setProduct] = useState<Product | null>(null)
  useEffect(() => { fetch(`/api/products/${id}`).then(r => r.json()).then(setProduct) }, [id])
  return <ProductDetail product={product} />
}
```

---

### State the cache behaviour on every fetch

An unannotated fetch leaves the freshness of the page to a default that shifts between versions. Say what you mean: a
revalidate window, a cache tag you can invalidate, or no store at all.

```typescript
// PASS: the intent is readable at the call site
const res = await fetch(`${process.env.API_URL}/products`, { next: { revalidate: 3600, tags: ['products'] } })

// FAIL: nothing here says whether this page is static, ISR, or dynamic
const res = await fetch(`${process.env.API_URL}/products`)
```

---

### Stream slow regions behind their own Suspense boundary

Blocking a whole route on its slowest query wastes the fast data. Render what you have, and let each slow region
arrive on its own with a real skeleton.

```typescript
// PASS: header renders immediately, reviews stream in
<ProductHeader product={product} />
<Suspense fallback={<ReviewsSkeleton />}>
  <Reviews productId={id} />
</Suspense>

// FAIL: the page waits for the slowest call before anything paints
const [product, reviews] = await Promise.all([getProduct(id), getReviews(id)])
return <ProductDetail product={product} reviews={reviews} />
```

---

### Mutate through Server Actions, not client fetch calls

A Server Action runs on the server, works without client JavaScript, and invalidates its own caches inside the same
function. A client `fetch` to your own route handler gives up all three.

```typescript
// PASS: mutation and invalidation live together
'use server'
export async function addToCart(productId: string) {
  const parsed = addToCartSchema.parse({ productId })
  await db.cart.create({ data: parsed })
  revalidateTag('cart')
}

// FAIL: a client round trip that leaves the cache stale
const handleClick = () => fetch('/api/cart', { method: 'POST', body: JSON.stringify({ productId }) })
```

---

### Validate and type every route handler boundary

A route handler is a public HTTP endpoint. Parse the body and the search params through a schema, and return a status
code the caller can act on.

```typescript
// PASS: parsed input, explicit status
export async function POST(request: NextRequest) {
  const parsed = createProductSchema.safeParse(await request.json())
  if (!parsed.success) return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 })
  return NextResponse.json(await db.product.create({ data: parsed.data }), { status: 201 })
}

// FAIL: unvalidated body written straight to the database, always 200
export async function POST(request: NextRequest) {
  return NextResponse.json(await db.product.create({ data: await request.json() }))
}
```

Run route handlers and pages on the Node.js runtime unless a specific deployment constraint says otherwise. It is the
default and it supports the full API surface most database drivers and SDKs need.

---

### Generate metadata from the same data the page renders

Hardcoded metadata in a dynamic route means every product shares one title. Derive it with `generateMetadata`, and
pre-render the known set with `generateStaticParams`.

```typescript
// PASS: title and description follow the record
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const product = await getProduct((await params).slug)
  return { title: product.name, description: product.description }
}

// FAIL: one title for every product in the catalogue
export const metadata = { title: 'Product', description: 'A product page' }
```

---

### Serve images through next/image and split heavy client modules

`next/image` handles format negotiation, responsive sizing, and lazy loading, and reserves layout space so the page
does not shift. Anything heavy and below the fold loads dynamically instead of riding in the first bundle.

```typescript
// PASS: sized, prioritised above the fold, heavy chart deferred
<Image src={product.image} alt={product.name} width={1200} height={630} priority />
const Chart = dynamic(() => import('./RevenueChart'))

// FAIL: unsized raw tag plus a charting library in the entry bundle
<img src={product.image} />
import { RevenueChart } from './RevenueChart'
```

---

### Develop on Turbopack

Turbopack is the default `next dev` bundler and keeps a filesystem cache, so a restart reuses previous work. Fall back
to webpack only to work around a specific bug, and record why.

```bash
next dev
```

```bash
next dev --webpack
```

The first command is the normal path. The second is the escape hatch, and a project that needs it permanently has a
plugin problem worth fixing rather than a default worth changing.

---

### Doc Comments

Default to none. A doc comment is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named function, rename the parameters so they carry their own meaning, and tighten the
types. Do that first and most doc comments have nothing left to say, which is the outcome you want. Code that explains
itself cannot go stale, a comment can.

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
 * Creates a product and revalidates every cached listing that shows it.
 *
 * @throws {ZodError} when the submitted form fails validation
 */
export async function createProduct(formData: FormData): Promise<Product> { ... }

// FAIL: restates the signature and the file name
/**
 * Server action that creates a product.
 *
 * @param formData - The form data
 * @returns The created product
 */
export async function createProduct(formData: FormData): Promise<Product> { ... }
```

---

### Related skills

- `frontend-patterns` for React composition, hooks, forms, and animation that do not depend on Next.js.
- `frontend-design` for visual direction and composition.
- `design-system` for tokens, theming, and styling architecture.
- `web-accessibility` for keyboard, focus, ARIA, and contrast requirements.
- `seo` for titles, structured data, and keyword mapping behind `generateMetadata`.
- `performance-optimization` for profiling and Core Web Vitals work.
- `api-design` for the contract shape of route handlers exposed to other clients.

---

### Checklist

- Every `'use client'` sits at the smallest leaf that needs it.
- Every fetch declares a revalidate window, a cache tag, or `no-store`.
- Every slow region has a Suspense boundary with a real skeleton, and every route has `loading.tsx` or an equivalent.
- Every mutation is a Server Action that invalidates the caches it dirties.
- Every route handler parses its input through a schema and returns a meaningful status code.
- Every dynamic route derives its metadata from its own data.
- Every image goes through `next/image` with explicit dimensions, and above-the-fold images set `priority`.
- Every heavy client-only module is loaded dynamically.
- `next dev` runs on Turbopack, with any webpack fallback justified in writing.
- No doc comment restates a signature, and every recoverable error is documented with `@throws`.
