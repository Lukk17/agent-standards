# Scope

Companion reference for the [performance-optimization](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

The cross-cutting principles hub is the `coding-standards` skill, and this skill is the optimisation detail on top of it. It applies when:

- An application, endpoint, or job is slow, or a deployment regressed a latency or throughput metric.
- You need a baseline before optimising, or want to confirm an optimisation actually moved the metric.
- Reviewing a change for an obvious performance trap: a query inside a loop, an unbounded fetch, sequential awaits of unrelated calls.
- The user says "this endpoint is slow", "the page takes four seconds to load", "profile this before I change anything", "did my change regress latency", or "this query runs inside a loop".

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

### Related skills

- `coding-standards` is the hub for the shared engineering floor this skill sits on.
- `postgres-patterns` owns schema, index, and query design in Postgres itself.
- `database-migrations` owns applying an index or a schema change safely.
- `backend-patterns` owns the cache invalidation rule a justified cache follows.
- `observability-and-logging` owns the metrics and traces that give you the baseline to measure against.
- `tdd-workflow` owns the regression test that keeps the optimisation from silently reverting.
- `code-reviewer` is the entry point when performance is one concern among several in a review.
