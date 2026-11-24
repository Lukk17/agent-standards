---
name: node-backend-patterns
description: 'Node.js service patterns for Express and Next.js handlers: layering, RFC 9457 errors, logging, shutdown. Use when the user says "structure my Express API". Not for language-neutral design, use `backend-patterns`.'
metadata:
  version: "1.1.0"
---

# Node Backend Patterns

Server-side patterns for Node.js services built on Express or Next.js route handlers, from request layering down to process shutdown. Everything here is TypeScript on the Node runtime, so the rules assume a single-threaded event loop and the npm ecosystem.

Written for Node.js 26, Express 5, Next.js 16 and TypeScript 7, with Zod 4 for schemas.

---

### When not to activate

- Language-neutral backend design (idempotency, outbox, retries as a concept), use `backend-patterns`.
- HTTP contract questions such as URL shape, status codes, or pagination style, use `api-design`.
- Next.js rendering, Server Components, caching, or Server Actions, use `nextjs-app-router-patterns`.

---

### Reference map

| Task | Open |
| --- | --- |
| A rule below needs its Pass and Fail example, its full reasoning, or the doc comment delta | [core-rules.md](references/core-rules.md) |
| The service is an Express app | [express.md](references/express.md) |
| The service is a Next.js route handler | [nextjs.md](references/nextjs.md) |
| The schema library is Zod: the configuration schema, the 422 branch of the error handler | [zod.md](references/zod.md) |
| The logger is pino: the request-scoped child logger | [pino.md](references/pino.md) |
| Adding a cache, picking a TTL, fixing stale reads or a stampede | [caching.md](references/caching.md) |
| Throttling an endpoint, sharing counters across instances | [rate-limiting.md](references/rate-limiting.md) |
| Moving work off the request path, queues, outbox, retries | [background-jobs.md](references/background-jobs.md) |
| Token verification, per-resource authorization, refresh tokens | [auth.md](references/auth.md) |
| Before calling a change to a Node service or its review done | [checklist.md](references/checklist.md) |

---

### Rules

1. A handler parses and responds, a service holds the business rule, and a repository is the only thing that speaks to the database. This holds for a Next.js route handler as for an Express route.
2. Select named columns with a bound, and batch related reads into one query by id. No `SELECT *` and no query inside a loop.
3. Run every multi-statement write in one transaction owned by the service, never as two repository calls that can fail between them.
4. Parse the whole environment once at startup against a schema and export the result as the only way to read configuration.
5. Every error leaves through one handler as RFC 9457 `application/problem+json`, with 422 for a schema failure and no internal message or stack in the body.
6. Retry only timeouts and 5xx on idempotent calls, never a 4xx, with a capped attempt count, jittered exponential backoff, and a deadline on every outbound call.
7. Await independent calls together under `Promise.all`.
8. Log through one logger, never `console`, with `correlationId` and `requestId` on a request-scoped child logger.
9. Model async state as a discriminated union, never a bag of nullable fields.
10. Emit the `observability-and-logging` startup block in one log call from the listen callback, and on `SIGTERM` stop accepting, drain, close the pools, and keep a hard exit timer.
11. Doc comments follow the Doc Comments rules in `coding-standards`, plus `@throws` for the errors an async function's promise rejects with.
