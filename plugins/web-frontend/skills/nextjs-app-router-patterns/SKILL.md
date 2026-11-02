---
name: nextjs-app-router-patterns
description: "Next.js 16 App Router architecture, covering the Server and Client Component split, caching and revalidation, streaming, Server Actions, route handlers, metadata, images and Turbopack dev tuning. Use when the user says \"build a Next.js page\", \"server or client component\" or \"add a server action\". Not for framework-agnostic React state, hooks and animation, use `react-patterns`."
license: Apache-2.0
---

# Next.js App Router Patterns

Architecture rules for Next.js applications built on the App Router, from the Server and Client Component split down to caching, mutations, and dev-server tuning. Every rule here is about where code runs and when its output goes stale.

Written for Next.js 16 on the App Router, where Turbopack is the default dev bundler and `params` and `searchParams` arrive as promises.

---

### When to activate

- Building or reviewing any route, layout, or component in an `app/` directory.
- The user says "build a Next.js page", "server or client component", "revalidate this fetch", "add a server action", "parallel routes for a dashboard", or "next dev is slow".
- Deciding whether a component belongs on the server or the client.
- Choosing a caching or revalidation strategy for fetched data.
- Adding a Server Action, a route handler, or per-route metadata.
- Migrating a Pages Router application to the App Router.
- Diagnosing a slow `next dev` start or a slow hot update.
- Fixing a Core Web Vitals regression in a Next.js app. This skill owns that work.

---

### When not to activate

- Framework-agnostic React work: component composition, hooks, forms, animation. Use `react-patterns`.
- Visual direction, typography, and composition decisions. Use `frontend-design`.
- Token architecture and theming. Use `design-system`.
- Keyboard, focus, ARIA, and contrast requirements. Use `web-accessibility`.
- Titles, meta descriptions, structured data, and keyword mapping. Use `seo`.
- Profiling the server code and data access behind a slow route. Use `performance-optimization`.
- Layering, error responses, logging, and shutdown inside a route handler. Use `node-backend-patterns`.

---

### Reference map

| Task | Open |
| --- | --- |
| A hub rule needs its Pass and Fail example or its full reasoning | [references/core-rules.md](references/core-rules.md) |
| Server and Client split, streaming, caching layers | [references/rendering-and-data.md](references/rendering-and-data.md) |
| File conventions, parallel and intercepting routes, route handlers, metadata | [references/routing.md](references/routing.md) |
| Server Actions, form mutations, revalidation | [references/server-actions.md](references/server-actions.md) |
| Images, bundle splitting, Turbopack, bundle analysis | [references/performance-and-tooling.md](references/performance-and-tooling.md) |

---

### Rules

1. Keep components on the server, and put `'use client'` only on the small leaf that needs state, an effect, or a DOM event handler.
2. State the cache behaviour on every fetch: a revalidate window, a cache tag, or `no-store`.
3. Stream each slow region behind its own `Suspense` boundary with a real skeleton, rather than blocking the route on its slowest query.
4. Mutate through Server Actions that invalidate their own caches: `updateTag` when the user must see the write on the next request, `revalidateTag(tag, 'max')` when a stale read is fine. The single-argument `revalidateTag(tag)` is deprecated.
5. Parse every route handler input through a schema, hand the work to a service, and return errors through the `node-backend-patterns` problem+json handler, with 422 for a failed schema.
6. Run route handlers and pages on the Node.js runtime unless a specific deployment constraint says otherwise.
7. Derive metadata with `generateMetadata` from the data the page renders, and pre-render the known set with `generateStaticParams`.
8. Serve images through `next/image` with explicit dimensions, the LCP image with `loading="eager"` and `fetchPriority="high"`, and load heavy below-the-fold modules with `dynamic`.
9. Develop on Turbopack, and fall back to `next dev --webpack` only for a specific bug, with the reason written down.

---

### Doc Comments

Doc comments follow the Doc Comments rules in `coding-standards`, whose TSDoc examples already cover TypeScript. Next.js delta: a Server Action returns its failure as a value rather than throwing it across the network boundary, so its error contract goes in `@returns`, for example `@returns { error } when the form fails validation`.

---

### Related skills

- `react-patterns` for React composition, hooks, forms, and animation that do not depend on Next.js.
- `frontend-design` for visual direction and composition.
- `design-system` for tokens, theming, and styling architecture.
- `web-accessibility` for keyboard, focus, ARIA, and contrast requirements.
- `seo` for titles, structured data, and keyword mapping behind `generateMetadata`.
- `performance-optimization` for profiling server code and data access. Core Web Vitals work stays here.
- `api-design` for the contract shape of route handlers exposed to other clients.

---

### Checklist

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
