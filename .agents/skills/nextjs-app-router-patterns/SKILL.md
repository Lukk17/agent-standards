---
name: nextjs-app-router-patterns
description: 'Next.js 16 App Router rules for Server and Client Components, caching, streaming and Server Actions. Use when the user says "build a Next.js page" or "add a server action". Not for plain React, use `react-patterns`.'
license: Apache-2.0
metadata:
  version: "1.1.0"
---

# Next.js App Router Patterns

Architecture rules for Next.js applications built on the App Router, from the Server and Client Component split down to caching, mutations, and dev-server tuning. Every rule here is about where code runs and when its output goes stale.

Written for Next.js 16 on the App Router, where Turbopack is the default dev bundler and `params` and `searchParams` arrive as promises.

---

### When not to activate

- Framework-agnostic React work: component composition, hooks, forms and animation, use `react-patterns`.
- Titles, meta descriptions, structured data and keyword mapping, use `seo`.
- Profiling the server code and data access behind a slow route, use `performance-optimization`, while a Core Web Vitals regression in a Next.js app stays here.

---

### Rules

1. Keep components on the server, and put `'use client'` only on the small leaf that needs state, an effect, or a DOM event handler.
2. State the cache behaviour on every fetch: a revalidate window, a cache tag, or `no-store`.
3. Stream each slow region behind its own `Suspense` boundary with a real skeleton, rather than blocking the route on its slowest query.
4. Mutate through Server Actions that invalidate their own caches: `updateTag` when the user must see the write on the next request, `revalidateTag(tag, 'max')` when a stale read is fine. The single-argument `revalidateTag(tag)` is deprecated.
5. Parse every route handler input through a schema, hand the work to a service, and return errors through the `node-backend-patterns` problem+json handler, with 422 for a failed schema.
6. Run route handlers and pages on the Node.js runtime unless a specific deployment constraint says otherwise.
7. Derive metadata with `generateMetadata` from the data the page renders, titles from the message catalogue per the i18n rule in `react-patterns`, and pre-render the known set with `generateStaticParams`.
8. Serve images through `next/image` with explicit dimensions, the LCP image with `loading="eager"` and `fetchPriority="high"`, and load heavy below-the-fold modules with `dynamic`.
9. Develop on Turbopack, and fall back to `next dev --webpack` only for a specific bug, with the reason written down.
10. Doc comments follow the Doc Comments rules in `coding-standards`, plus: a Server Action that returns its failure as a value documents that error contract in `@returns`.

---

### Reference map

| Task | Open |
| --- | --- |
| A rule above needs its Pass and Fail example, its full reasoning or the doc comment delta | [references/core-rules.md](references/core-rules.md) |
| Server and Client split, streaming, caching layers | [references/rendering-and-data.md](references/rendering-and-data.md) |
| File conventions, parallel and intercepting routes, route handlers, metadata | [references/routing.md](references/routing.md) |
| Server Actions, form mutations, revalidation | [references/server-actions.md](references/server-actions.md) |
| Images, bundle splitting, Turbopack, bundle analysis | [references/performance-and-tooling.md](references/performance-and-tooling.md) |
| Before calling a Next.js change or a Next.js review done | [references/checklist.md](references/checklist.md) |
