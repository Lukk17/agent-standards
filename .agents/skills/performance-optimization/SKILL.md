---
name: performance-optimization
description: 'Measure-first performance work for application code and data access: profiling, N+1 queries, fetch and index discipline, when a cache is justified, streaming, and bounded concurrent IO. Use when the user says "this endpoint is slow", "profile this before I change anything", or "this query runs inside a loop". Not for schema and index design on Postgres itself, use `postgres-patterns`.'
---

# Performance Optimization

Make slow things fast without guessing, because performance work that is not driven by a measurement is decoration. The
cross-cutting principles hub is the `coding-standards` skill and this skill is the optimisation detail on top of it.

| Task | Open |
|---|---|
| Applying a rule: its reasoning and pass and fail forms in Python, SQL, TypeScript and Go | [worked-examples.md](references/worked-examples.md) |

---

### When to activate

- An application, endpoint, or job is slow, or a deployment regressed a latency or throughput metric.
- You need a baseline before optimising, or want to confirm an optimisation actually moved the metric.
- Reviewing a change for an obvious performance trap: a query inside a loop, an unbounded fetch, sequential awaits of
  unrelated calls.
- The user says "this endpoint is slow", "the page takes four seconds to load", "profile this before I change
  anything", "did my change regress latency", or "this query runs inside a loop".

---

### When not to activate

- Designing a table, choosing a column type, or writing a migration. Use `postgres-patterns` for the schema and
  `database-migrations` for the change.
- Writing the tests that prove the fix holds. Use `tdd-workflow`, or the language skill (`python-patterns`,
  `golang-patterns`, `springboot-patterns`).
- Reducing container image size or build time. Use `docker-patterns`.
- Frontend rendering, bundle weight, and Core Web Vitals in a specific framework. Use `nextjs-app-router-patterns`
  or `angular`.
- A general code review that happens to mention speed. Use `code-reviewer` and pull this skill in for the performance
  findings only.

---

### Rules

1. Measure before you change anything. Set a target, a latency budget or a throughput number, then profile, fix the one real bottleneck, and measure again. A change that only moves cost between layers is no win.
2. Avoid the N+1 query. Batch related lookups into one query, or fetch the relation eagerly (`JOIN FETCH` or an entity graph in JPA, `select_related` / `prefetch_related` in Django, a DataLoader in GraphQL). Confirm by counting the queries the request issues.
3. Fetch and index only what is needed. Select the columns the caller reads, page large results by cursor, add the indexes the real queries need, and confirm in the query plan that they are used, because an unused index is write cost for no read benefit.
4. Add a cache only after a profile shows a read-dominated hot path, and follow the invalidation rule `backend-patterns` owns. A guessed cache hides the bottleneck and adds a staleness bug.
5. Keep memory bounded. Join or buffer strings rather than concatenate in a loop, and stream large data lazily rather than materialise it.
6. Run independent IO concurrently (`Promise.all`, Go `errgroup`), only for calls with no data dependency, and cap the fan-out so 10,000 ids never open 10,000 sockets.

---

### Related skills

- `coding-standards` is the hub for the shared engineering floor this skill sits on.
- `postgres-patterns` owns schema, index, and query design in Postgres itself.
- `database-migrations` owns applying an index or a schema change safely.
- `backend-patterns` owns the cache invalidation rule a justified cache follows.
- `observability-and-logging` owns the metrics and traces that give you the baseline to measure against.
- `tdd-workflow` owns the regression test that keeps the optimisation from silently reverting.
- `code-reviewer` is the entry point when performance is one concern among several in a review.

---

### Checklist

- [ ] A profile or a metric, not a hunch, identified the bottleneck.
- [ ] A target number was set before the change and measured again after.
- [ ] No query runs inside a loop over rows a previous query returned.
- [ ] Queries select named columns and page their results.
- [ ] Every index added is confirmed used by the query plan.
- [ ] Every cache was justified by a profile and follows the `backend-patterns` invalidation rule.
- [ ] Large payloads stream rather than materialise.
- [ ] Independent IO runs concurrently with a bounded fan-out.
- [ ] The metric moved, and the change did not just move the cost elsewhere.
