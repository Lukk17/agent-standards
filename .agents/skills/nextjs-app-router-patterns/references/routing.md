# Routing, Route Handlers, and Metadata

File conventions, the advanced routing primitives, HTTP endpoints, and per-route metadata.

---

### File conventions

```text
app/
├── layout.tsx           Shared UI wrapper, persists across navigations
├── page.tsx             Route UI
├── loading.tsx          Suspense fallback for the segment
├── error.tsx            Error boundary for the segment
├── not-found.tsx        404 UI
├── route.ts             API endpoint, mutually exclusive with page.tsx
├── template.tsx         Like layout, but re-mounted on every navigation
├── default.tsx          Parallel route fallback
└── opengraph-image.tsx  Generated Open Graph image
```

---

### Route organisation

| Pattern | What it does |
| --- | --- |
| Route group `(name)` | Groups files for organisation or a shared layout without adding a URL segment |
| Parallel route `@slot` | Renders several independent pages into one layout, each with its own loading state |
| Intercepting route `(.)` | Renders a route in the current layout instead of navigating away, the modal pattern |
| Dynamic segment `[id]` | One route template for many records |
| Catch-all `[...slug]` | One route template for a variable-depth path |

Prefer a route group over a folder nobody navigates to, and reach for parallel routes when two regions of a dashboard
load at genuinely different speeds.

---

### Parallel routes

Each slot is a folder named `@slot` and arrives in the layout as a prop of the same name. Every slot can carry its
own `loading.tsx`, so a slow analytics panel never delays the team list.

```typescript
// app/dashboard/layout.tsx
export default function DashboardLayout({
  children,
  analytics,
  team,
}: {
  children: React.ReactNode
  analytics: React.ReactNode
  team: React.ReactNode
}) {
  return (
    <div className="dashboard-grid">
      <main>{children}</main>
      <aside className="analytics-panel">{analytics}</aside>
      <aside className="team-panel">{team}</aside>
    </div>
  )
}

// app/dashboard/@analytics/page.tsx
export default async function AnalyticsSlot() {
  const stats = await getAnalytics()
  return <AnalyticsChart data={stats} />
}

// app/dashboard/@analytics/loading.tsx
export default function AnalyticsLoading() {
  return <ChartSkeleton />
}
```

Give every slot a `default.tsx`, or a hard navigation into a sibling route renders a 404 for the unmatched slot.

---

### Intercepting routes, the modal pattern

The same photo needs two presentations: a modal when the user clicks a thumbnail inside the gallery, and a full page
when the URL is opened directly or shared. The interceptor handles the first, the real route handles the second, and
both read the same data.

```text
app/
├── @modal/
│   ├── (.)photos/[id]/page.tsx
│   └── default.tsx
├── photos/
│   └── [id]/page.tsx
└── layout.tsx
```

```typescript
// app/@modal/(.)photos/[id]/page.tsx
import { Modal } from '@/components/Modal'
import { PhotoDetail } from '@/components/PhotoDetail'

export default async function PhotoModal({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const photo = await getPhoto(id)

  return (
    <Modal>
      <PhotoDetail photo={photo} />
    </Modal>
  )
}

// app/photos/[id]/page.tsx
export default async function PhotoPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const photo = await getPhoto(id)

  return (
    <div className="photo-page">
      <PhotoDetail photo={photo} />
      <RelatedPhotos photoId={id} />
    </div>
  )
}
```

The root layout renders the modal slot alongside `children`.

```typescript
// app/layout.tsx
export default function RootLayout({
  children,
  modal,
}: {
  children: React.ReactNode
  modal: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        {children}
        {modal}
      </body>
    </html>
  )
}
```

A modal built this way still needs focus moved into it, trapped, and restored on close. See `web-accessibility`.

---

### Route handlers

One `route.ts` per resource, one exported function per HTTP method. Parse the input, return the status code that
matches what happened.

| Method | Meaning | Success status |
| --- | --- | --- |
| GET | Read | 200 |
| POST | Create | 201 |
| PUT or PATCH | Replace or update | 200 |
| DELETE | Remove | 204 |

```typescript
// app/api/products/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

const listQuerySchema = z.object({ category: z.string().optional() })
const createProductSchema = z.object({ name: z.string().min(1), price: z.number().positive() })

export async function GET(request: NextRequest) {
  const parsed = listQuerySchema.safeParse(Object.fromEntries(request.nextUrl.searchParams))
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 })
  }

  const products = await db.product.findMany({
    where: parsed.data.category ? { category: parsed.data.category } : undefined,
    take: 20,
  })

  return NextResponse.json(products)
}

export async function POST(request: NextRequest) {
  const parsed = createProductSchema.safeParse(await request.json())
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 })
  }

  const product = await db.product.create({ data: parsed.data })
  return NextResponse.json(product, { status: 201 })
}
```

Dynamic segments arrive as a promise here too.

```typescript
// app/api/products/[id]/route.ts
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const product = await db.product.findUnique({ where: { id } })

  if (!product) {
    return NextResponse.json({ error: 'Product not found' }, { status: 404 })
  }

  return NextResponse.json(product)
}
```

Run handlers on the Node.js runtime, the default, unless a deployment constraint forces a different one.

---

### Metadata

Static metadata belongs in the root layout, where it sets the title template and the site-wide defaults.

```typescript
// app/layout.tsx
export const metadata = {
  title: { default: 'My App', template: '%s | My App' },
  description: 'Built with Next.js App Router',
}
```

Per-record metadata is generated. Pre-render the known set of dynamic routes with `generateStaticParams` so the pages
build statically and their metadata is ready at request time.

```typescript
// app/products/[slug]/page.tsx
import { Metadata } from 'next'
import { notFound } from 'next/navigation'

type Props = { params: Promise<{ slug: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const product = await getProduct(slug)

  if (!product) return {}

  return {
    title: product.name,
    description: product.description,
    alternates: { canonical: `/products/${slug}` },
    openGraph: {
      title: product.name,
      description: product.description,
      images: [{ url: product.image, width: 1200, height: 630 }],
    },
    twitter: {
      card: 'summary_large_image',
      title: product.name,
      description: product.description,
      images: [product.image],
    },
  }
}

export async function generateStaticParams() {
  const products = await db.product.findMany({ select: { slug: true } })
  return products.map((p) => ({ slug: p.slug }))
}

export default async function ProductPage({ params }: Props) {
  const { slug } = await params
  const product = await getProduct(slug)

  if (!product) notFound()

  return <ProductDetail product={product} />
}
```

Keep the title around 50 to 60 characters and the description around 120 to 160, set a canonical URL, and ship an
Open Graph image. The `seo` skill owns what those strings should say.
