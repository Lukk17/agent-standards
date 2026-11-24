---
name: performance-optimization
description: 'Measure-first performance work: profiling, N+1 queries, indexes, caches. Use when the user says "this endpoint is slow" or "this query runs inside a loop". Not for Postgres schema design, use `postgres-patterns`.'
metadata:
  version: "1.1.0"
---

# Performance Optimization

Make slow things fast without guessing, because performance work that is not driven by a measurement is decoration.

| Task | Open |
|---|---|
| A rule below in full, with its reasoning and its pass and fail form | [worked-examples.md](references/worked-examples.md) |
| Python: batching lookups and streaming a large response | [python.md](references/python.md) |
| SQL: a narrow, paged query and its index | [sql.md](references/sql.md) |
| TypeScript: independent calls with `Promise.all` | [typescript.md](references/typescript.md) |
| Go: independent calls with `errgroup` | [go.md](references/go.md) |
| Before calling the optimisation done | [checklist.md](references/checklist.md) |

---

### When not to activate

- Designing a table, choosing a column type, or writing a migration, use `postgres-patterns` for the schema and `database-migrations` for the change.
- Frontend rendering, bundle weight and Core Web Vitals in a specific framework, use `nextjs-app-router-patterns` or `angular`.
- A general code review that happens to mention speed, use `code-reviewer` and pull this skill in for the performance findings only.

---

### Rules

1. Measure before you change anything. Set a target, a latency budget or a throughput number, then profile, fix the one real bottleneck, and measure again. A change that only moves cost between layers is no win.
2. Avoid the N+1 query. Batch related lookups into one query, or fetch the relation eagerly. Confirm by counting the queries the request issues.
3. Fetch and index only what is needed. Select the columns the caller reads, page large results by cursor, add the indexes the real queries need, and confirm in the query plan that they are used, because an unused index is write cost for no read benefit.
4. Add a cache only after a profile shows a read-dominated hot path, and follow the invalidation rule `backend-patterns` owns. A guessed cache hides the bottleneck and adds a staleness bug.
5. Keep memory bounded. Join or buffer strings rather than concatenate in a loop, and stream large data lazily rather than materialise it.
6. Run independent IO concurrently, only for calls with no data dependency, and cap the fan-out so 10,000 ids never open 10,000 sockets.
