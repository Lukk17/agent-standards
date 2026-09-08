# Rendering and Data

Where a component runs, when its output is produced, and how long that output stays valid.

---

### Rendering modes

| Mode | Where it runs | Reach for it when |
| --- | --- | --- |
| Server Component | Server only | Data fetching, heavy computation, anything touching a secret |
| Client Component | Browser | State, effects, event handlers, browser APIs |
| Static | Build time | Content that rarely changes |
| Dynamic | Request time | Personalised or real-time data |
| Streaming | Progressive | Large pages, slow data sources |

---

### Choosing the boundary

Walk the component top down and ask what it actually needs.

1. Does it need `useState`, `useEffect`, a ref, or a DOM event handler? It is a Client Component.
2. Does it read the database, a secret, or the filesystem? It is a Server Component, and it must stay one.
3. Does it need both? Split it. The server parent fetches and passes plain serialisable props to a client child.

A client parent cannot render a server child, but a server parent can pass a server-rendered subtree to a client
component as `children`. Use that when a client wrapper needs to provide layout or interactivity around server
content.

---

### Server Component with search params

`searchParams` is a promise. Awaiting it opts the route into dynamic rendering, which is what you want on a filtered
listing. Keying the Suspense boundary on the params forces a fresh fallback whenever the filters change.

```typescript
// app/products/page.tsx
import { Suspense } from 'react'
import { ProductList, ProductListSkeleton } from '@/components/products'
import { FilterSidebar } from '@/components/filters'

interface SearchParams {
  category?: string
  sort?: 'price' | 'name' | 'date'
  page?: string
}

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}) {
  const params = await searchParams

  return (
    <div className="flex gap-8">
      <FilterSidebar />
      <Suspense key={JSON.stringify(params)} fallback={<ProductListSkeleton />}>
        <ProductList
          category={params.category}
          sort={params.sort}
          page={Number(params.page) || 1}
        />
      </Suspense>
    </div>
  )
}
```

The list component fetches its own data. Colocating the fetch with the component that renders it is what makes the
Suspense boundary above meaningful.

```typescript
// components/products/ProductList.tsx
async function getProducts(filters: ProductFilters) {
  const res = await fetch(
    `${process.env.API_URL}/products?${new URLSearchParams(filters)}`,
    { next: { tags: ['products'] } }
  )
  if (!res.ok) throw new Error('Failed to fetch products')
  return res.json()
}

export async function ProductList({ category, sort, page }: ProductFilters) {
  const { products, totalPages } = await getProducts({ category, sort, page })

  return (
    <div>
      <div className="grid grid-cols-3 gap-4">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
      <Pagination currentPage={page} totalPages={totalPages} />
    </div>
  )
}
```

---

### Client Component at the leaf

`useTransition` keeps the button responsive while the Server Action runs and gives you a pending flag without an
extra state variable.

```typescript
// components/products/AddToCartButton.tsx
'use client'

import { useState, useTransition } from 'react'
import { addToCart } from '@/app/actions/cart'

export function AddToCartButton({ productId }: { productId: string }) {
  const [isPending, startTransition] = useTransition()
  const [error, setError] = useState<string | null>(null)

  const handleClick = () => {
    setError(null)
    startTransition(async () => {
      const result = await addToCart(productId)
      if (result.error) setError(result.error)
    })
  }

  return (
    <div>
      <button onClick={handleClick} disabled={isPending} className="btn-primary">
        {isPending ? 'Adding...' : 'Add to Cart'}
      </button>
      {error && <p className="text-red-500 text-sm">{error}</p>}
    </div>
  )
}
```

---

### Streaming with Suspense

Fetch the data the page cannot render without, then let everything else stream. Each boundary gets its own skeleton
so the layout never jumps when the content lands.

```typescript
// app/product/[id]/page.tsx
import { Suspense } from 'react'

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const product = await getProduct(id)

  return (
    <div>
      <ProductHeader product={product} />

      <Suspense fallback={<ReviewsSkeleton />}>
        <Reviews productId={id} />
      </Suspense>

      <Suspense fallback={<RecommendationsSkeleton />}>
        <Recommendations productId={id} />
      </Suspense>
    </div>
  )
}

async function Reviews({ productId }: { productId: string }) {
  const reviews = await getReviews(productId)
  return <ReviewList reviews={reviews} />
}

async function Recommendations({ productId }: { productId: string }) {
  const products = await getRecommendations(productId)
  return <ProductCarousel products={products} />
}
```

---

### Caching layers

Three layers decide freshness, and each has its own control.

| Layer | Controlled by |
| --- | --- |
| Request | `fetch` options on the individual call |
| Data | `revalidate` windows and cache tags |
| Full route | Route segment config in the page or layout |

```typescript
fetch(url, { cache: 'no-store' })

fetch(url, { cache: 'force-cache' })

fetch(url, { next: { revalidate: 60 } })

fetch(url, { next: { tags: ['products'] } })
```

Time-based revalidation suits data that goes stale on a schedule. Tag-based invalidation suits data that goes stale
when something specific happens, and the mutation that causes it is the right place to trigger it.

```typescript
'use server'
import { revalidateTag, revalidatePath } from 'next/cache'

export async function updateProduct(id: string, data: ProductData) {
  await db.product.update({ where: { id }, data })
  revalidateTag('products')
  revalidatePath('/products')
}
```
