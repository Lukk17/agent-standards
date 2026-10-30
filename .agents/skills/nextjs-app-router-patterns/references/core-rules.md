# Next.js App Router Core Rules in Depth

The Pass and Fail examples and the reasoning behind each rule the SKILL.md hub states in one or two lines. Open it when a hub rule needs its worked form or its full explanation. Written for Next.js 16 on the App Router.

---

### Contents

- Keep components on the server until interactivity forces otherwise
- State the cache behaviour on every fetch
- Stream slow regions behind their own Suspense boundary
- Mutate through Server Actions, not client fetch calls
- Validate and type every route handler boundary
- Generate metadata from the same data the page renders
- Serve images through next/image and split heavy client modules
- Develop on Turbopack

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

A Server Action runs on the server, works without client JavaScript, and invalidates its own caches inside the same function. A client `fetch` to your own route handler gives up all three. Use `updateTag` there when the user must see their own write on the next request, and `revalidateTag(tag, 'max')` when a stale read during the refresh is fine. The single-argument `revalidateTag(tag)` is deprecated.

```typescript
// PASS: mutation and invalidation live together
'use server'
export async function addToCart(productId: string) {
  const parsed = addToCartSchema.safeParse({ productId })
  if (!parsed.success) return { error: 'Invalid product' }
  await db.cart.create({ data: parsed.data })
  updateTag('cart')
  return { success: true }
}

// FAIL: a client round trip that leaves the cache stale
const handleClick = () => fetch('/api/cart', { method: 'POST', body: JSON.stringify({ productId }) })
```

---

### Validate and type every route handler boundary

A route handler is a public HTTP endpoint. Parse the body and the search params through a schema, hand the work to a
service, and return every error through the shared problem+json handler. The service layering and
`toProblemResponse` are owned by `node-backend-patterns`, which answers a failed schema with 422.

```typescript
// PASS: parsed input, rule in a service, errors through the shared problem+json handler
export async function POST(request: NextRequest) {
  try {
    const input = createProductSchema.parse(await request.json())
    return NextResponse.json(await productService.create(input), { status: 201 })
  } catch (error) {
    return toProblemResponse(error, request.nextUrl.pathname)
  }
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
// PASS: sized, fetched first above the fold, heavy chart deferred
<Image src={product.image} alt={product.name} width={1200} height={630} loading="eager" fetchPriority="high" />
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
