# Next.js Route Handlers

The Next.js 16 form of the core rules. Open it when the service is a Next.js route handler. The reasoning behind each rule is in [core-rules.md](core-rules.md).

---

### Layering

This skill owns the layering, error responses, logging, and shutdown of a Next.js route handler as well as of an Express route. `nextjs-app-router-patterns` owns the `route.ts` file convention, the runtime choice, and caching.

---

### Logging

A route handler that builds the request-scoped child logger is shown in [pino.md](pino.md#request-scoped-child-logger).

---

### Startup hook

The startup readiness block is emitted from the post-bind callback of a custom Next.js server, in one log call.
