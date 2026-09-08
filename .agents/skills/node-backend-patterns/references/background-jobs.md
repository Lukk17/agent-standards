# Background jobs in Node services

Read this when moving work off the request path, choosing a queue, or fixing a job that runs twice or silently
disappears.

---

### An in-process array is not a queue

A module-level array loses every pending job when the process restarts, and a serverless function may be frozen the
moment the response is returned. Use a durable broker (BullMQ on Redis, pg-boss on Postgres, SQS) whenever losing the
job would be a defect.

Fail:

```typescript
const queue: IndexJob[] = []
export function enqueue(job: IndexJob) {
  queue.push(job)
  void drain()
}
```

Pass:

```typescript
import { Queue, Worker } from 'bullmq'

export const indexQueue = new Queue<IndexJob>('index', { connection })

new Worker<IndexJob>('index', async (job) => reindexMarket(job.data.marketId), {
  connection,
  concurrency: 5,
})
```

---

### Enqueue the identifier, not the object

A payload is serialised at enqueue time and consumed minutes later. Store the primary key and re-read the row in the
worker, so the job acts on current data and the payload stays small enough to inspect in a dead-letter queue.

Pass: `{ marketId: 'abc-123' }`.

Fail: the whole market row plus its creator, already stale by the time the worker runs, and carrying fields the queue
has no business storing.

---

### Every handler must be idempotent

At-least-once delivery is the normal case, not the failure case: a worker can crash after doing the work and before
acknowledging. Make the effect safe to repeat, either by writing with a natural key and `ON CONFLICT DO NOTHING`, or by
recording a processed marker inside the same transaction as the effect.

```typescript
await db.transaction(async (tx) => {
  const claimed = await tx.insertInto('processed_jobs')
    .values({ jobId })
    .onConflict((oc) => oc.doNothing())
    .executeTakeFirst()

  if (Number(claimed.numInsertedOrUpdatedRows ?? 0) === 0) return

  await applyEffect(tx)
})
```

---

### Publish through an outbox when the job must follow a committed write

Writing a row and enqueueing a job are two systems. If the enqueue succeeds and the transaction rolls back, a worker
processes a record that does not exist. Insert the message into an outbox table inside the same transaction, and let a
relay move committed rows onto the broker.

```sql
CREATE TABLE outbox (
  id           bigserial PRIMARY KEY,
  topic        text        NOT NULL,
  payload      jsonb       NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz
);
```

```sql
UPDATE outbox SET published_at = now()
WHERE id IN (
  SELECT id FROM outbox WHERE published_at IS NULL
  ORDER BY id LIMIT 100 FOR UPDATE SKIP LOCKED
)
RETURNING id, topic, payload;
```

---

### Bound every retry and terminate on a dead-letter queue

An unbounded retry turns one poison message into a permanent load source. Cap attempts, back off exponentially with
jitter, and move the exhausted job somewhere a human can see it.

```typescript
await indexQueue.add('reindex', { marketId }, {
  attempts: 5,
  backoff: { type: 'exponential', delay: 1_000 },
  removeOnComplete: 1_000,
  removeOnFail: false,
})
```

Distinguish the two failure classes before retrying at all. A validation failure, a 404, or a 422 will fail identically
on every attempt: fail it straight to the dead-letter queue. Retry only timeouts, 5xx responses, and connection errors.

---

### Give the worker its own timeout and its own shutdown

A handler with no timeout holds a queue slot forever. Set one per job, and on `SIGTERM` stop accepting new jobs, let the
in-flight ones finish inside the platform's grace period, then close the connections.

```typescript
process.on('SIGTERM', async () => {
  await worker.close()
  await connection.quit()
  process.exit(0)
})
```

---

### Log the job like a request

Carry the same `correlationId` from the enqueuing request into the payload, and put it on the worker's child logger.
Without it, a failed job cannot be traced back to the user action that produced it.

---

### Scheduled work needs a lock

A cron entry that runs on every instance runs N times. Use the broker's repeatable job support, or take a short
advisory lock in Postgres, so exactly one instance performs the run.

---

### Related skills

- `node-backend-patterns` for the hub these rules belong to.
- `backend-patterns` for the language-neutral outbox and retry rules.
- `postgres-patterns` for `FOR UPDATE SKIP LOCKED` queue mechanics and advisory locks.
- `observability-and-logging` for tracing a job back to its originating request.
