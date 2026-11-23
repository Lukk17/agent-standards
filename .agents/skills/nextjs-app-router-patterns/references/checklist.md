# Next.js App Router Checklist

Run it before calling a Next.js change or a Next.js review done.

- Every `'use client'` sits at the smallest leaf that needs it.
- Every fetch declares a revalidate window, a cache tag, or `no-store`.
- Every slow region has a Suspense boundary with a real skeleton, and every route has `loading.tsx` or an equivalent.
- Every mutation is a Server Action that invalidates the caches it dirties.
- Every route handler parses its input through a schema and returns a meaningful status code.
- Every dynamic route derives its metadata from its own data.
- Every image goes through `next/image` with explicit dimensions, and the above-the-fold LCP image sets `loading="eager"` and `fetchPriority="high"`, never the deprecated `priority`.
- Every heavy client-only module is loaded dynamically.
- `next dev` runs on Turbopack, with any webpack fallback justified in writing.
- Doc comments follow `coding-standards`, and a Server Action that returns its error documents that in `@returns`.
