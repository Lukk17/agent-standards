# pino

The pino form of the logging rule. Open it when the service logs through pino. The reasoning is in [core-rules.md](core-rules.md#log-through-one-logger-with-a-request-scoped-child-logger).

---

### Request-scoped child logger

Use pino, never `console`, and put `correlationId` and `requestId` on a child logger so every line from one request joins up. The example sits in a Next.js route handler.

```typescript
export async function GET(request: Request) {
  const correlationId = request.headers.get('x-correlation-id') ?? crypto.randomUUID()
  const log = logger.child({ correlationId, requestId: crypto.randomUUID() })

  log.info({ path: '/api/markets' }, 'fetching markets')
  return NextResponse.json({ data: await fetchMarkets() })
}
```

Fail: `console.error('failed', error)` inside a catch block, with no request identifier anywhere in the line.
