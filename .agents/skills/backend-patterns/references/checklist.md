# Backend Patterns Checklist

Run it before calling a backend design, or a review of one, done.

- [ ] Every non-idempotent write accepts and enforces an idempotency key.
- [ ] Every outbound call has a timeout, and every retry has a cap, jitter, and a retryable-error list.
- [ ] Work that may not be lost goes through a durable queue with a dead-letter destination.
- [ ] Messages that must follow a committed write are published from an outbox, not inline.
- [ ] Every cached key has a named invalidation trigger, and cache failure degrades throughput only.
- [ ] Idempotency keys are claimed before the effect, a request still in flight gets 409, and the key goes downstream.
- [ ] Retries honour `Retry-After` on 429 and 503.
- [ ] List endpoints over unbounded data use cursor pagination with a server-side maximum page size.
- [ ] `/health` and `/ready` are separate, and `SIGTERM` drains before exit.
- [ ] Layering follows `hexagonal-architecture` and the contract follows `api-design`.
