# Scope

Companion reference for the [nextjs-app-router-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Building or reviewing any route, layout, or component in an `app/` directory.
- The user says "build a Next.js page", "server or client component", "revalidate this fetch", "add a server action", "parallel routes for a dashboard", or "next dev is slow".
- Deciding whether a component belongs on the server or the client.
- Choosing a caching or revalidation strategy for fetched data.
- Adding a Server Action, a route handler, or per-route metadata.
- Serving images through `next/image`, or tuning the Turbopack dev server.
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

### Related skills

- `react-patterns` for React composition, hooks, forms, and animation that do not depend on Next.js.
- `frontend-design` for visual direction and composition.
- `design-system` for tokens, theming, and styling architecture.
- `web-accessibility` for keyboard, focus, ARIA, and contrast requirements.
- `seo` for titles, structured data, and keyword mapping behind `generateMetadata`.
- `performance-optimization` for profiling server code and data access. Core Web Vitals work stays here.
- `api-design` for the contract shape of route handlers exposed to other clients.
