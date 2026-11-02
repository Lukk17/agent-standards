---
name: node-backend-patterns
description: "Node.js server-side patterns for Express and Next.js route handlers, covering service and repository layering, query batching, RFC 9457 errors, typed config, pino logging, caching, rate limiting and graceful shutdown. Use when the user says \"structure my Express API\" or \"my Node app never exits on SIGTERM\". Not for language-neutral backend design, use `backend-patterns`."
---

# Node Backend Patterns

Server-side patterns for Node.js services built on Express or Next.js route handlers, from request layering down to process shutdown. Everything here is TypeScript on the Node runtime, so the rules assume a single-threaded event loop and the npm ecosystem.

Written for Node.js 26, Express 5, Next.js 16 and TypeScript 7, with Zod 4 for schemas.

---

### When to activate

- Structuring an Express app or a Next.js `app/api` route into handler, service, and repository layers.
- The user says "structure my Express API", "fix the N+1 in this route", "cache this Prisma query", "rate limit this endpoint", or "my Node app never exits on SIGTERM".
- Removing an N+1 query or a `SELECT *` from a Node data-access path.
- Adding Redis caching, a rate limiter, or a background queue to a Node service.
- Wiring typed configuration, pino logging, or a graceful shutdown handler.
- Reviewing a Node service for error-handling and validation gaps.

---

### When not to activate

- Language-neutral backend design (idempotency, outbox, retries as a concept): use `backend-patterns`.
- HTTP contract questions such as URL shape, status codes, or pagination style: use `api-design`.
- Java or Spring services: use `springboot-patterns`. Python: use `python-patterns`. Go: use `golang-patterns`.
- Next.js rendering, Server Components, caching, or Server Actions: use `nextjs-app-router-patterns`.
- Port and adapter boundaries and dependency inversion: use `hexagonal-architecture`.
- SQL schema, index, and query-plan work: use `postgres-patterns`.

---

### Reference map

| Task | Open |
| --- | --- |
| A hub rule needs its Pass and Fail example or its full reasoning | [references/core-rules.md](references/core-rules.md) |
| Adding a cache, picking a TTL, fixing stale reads or a stampede | [references/caching.md](references/caching.md) |
| Throttling an endpoint, sharing counters across instances | [references/rate-limiting.md](references/rate-limiting.md) |
| Moving work off the request path, queues, outbox, retries | [references/background-jobs.md](references/background-jobs.md) |
| Token verification, per-resource authorization, refresh tokens | [references/auth.md](references/auth.md) |

---

### Rules

1. A handler parses and responds, a service holds the business rule, and a repository is the only thing that speaks to the database. This holds for a Next.js route handler as for an Express route.
2. Select named columns with a bound, and batch related reads into one query by id. No `SELECT *` and no query inside a loop.
3. Run every multi-statement write in one transaction owned by the service, never as two repository calls that can fail between them.
4. Parse the whole environment once at startup against a Zod schema and export the result as the only way to read configuration.
5. Every error leaves through one handler as RFC 9457 `application/problem+json`, with 422 for a schema failure and no internal message or stack in the body.
6. Retry only timeouts and 5xx on idempotent calls, never a 4xx, with a capped attempt count, jittered exponential backoff, and a deadline on every outbound call.
7. Await independent calls together under `Promise.all`.
8. Log through pino, never `console`, with `correlationId` and `requestId` on a request-scoped child logger.
9. Model async state as a discriminated union, never a bag of nullable fields.
10. Emit the `observability-and-logging` startup block in one log call from the listen callback, and on `SIGTERM` stop accepting, drain, close the pools, and keep a hard exit timer.

---

### Doc comments

Doc comments follow the Doc Comments rules in `coding-standards`, whose TSDoc examples already cover TypeScript on Node. Node delta: an async function documents the errors its promise rejects with under `@throws`, because a rejection is the Node form of a throw and the signature says only `Promise<T>`.

---

### Related skills

- `backend-patterns` for the language-neutral rules these patterns implement.
- `api-design` for URL shape, status codes, pagination, and the canonical rate-limit headers and problem body.
- `hexagonal-architecture` for the port and adapter boundaries behind the repository interface.
- `nextjs-app-router-patterns` for the rendering and caching half of a Next.js app.
- `postgres-patterns` and `database-migrations` for schema, indexes, and safe schema change.
- `observability-and-logging` for the startup banner, log levels, and trace correlation.
- `security-review` before shipping auth, payment, or personal-data handling.

---

### Checklist

- [ ] Handler, service, and repository responsibilities are separate.
- [ ] No `SELECT *` and no query inside a loop on any request path.
- [ ] Multi-statement writes run inside one transaction.
- [ ] Configuration is parsed once at startup against a schema, never read from `process.env` in business logic.
- [ ] Every error leaves through one handler as `application/problem+json`, with no internal detail in the body.
- [ ] Retries are capped, jittered, deadline-bound, and applied only to transient failures.
- [ ] Independent awaits run under `Promise.all`.
- [ ] Logging goes through pino, with `correlationId` and `requestId` on every request-path line.
- [ ] Async state is a discriminated union, not a bag of nullable fields.
- [ ] `SIGTERM` drains the server and closes the pools within a bounded timeout.
