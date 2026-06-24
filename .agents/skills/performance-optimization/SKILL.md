---
name: performance-optimization
description: Measure-first performance work for application code and data access. Profile before changing, fix the real bottleneck, avoid N+1 queries, fetch and index only what is needed, cache with a clear invalidation rule, stream large data, and run independent IO concurrently. Use when something is slow, a change regressed performance, or you need a baseline before optimising.
---

# Performance Optimization

Make slow things fast without guessing. Performance work that is not driven by a measurement is decoration. The
cross-cutting principles hub is the `coding-standards` skill; this skill is the optimisation detail.

---

### When to activate

- An application or endpoint is slow, or a deployment regressed a latency or throughput metric.
- You need a baseline before optimising, or want to verify an optimisation actually moved the metric.
- Reviewing a change for an obvious performance trap (a query in a loop, an unbounded fetch, a sync call that should
  run concurrently).

---

### Measure first

- Do not optimise before measuring. Profile, find the one real bottleneck, then fix that one thing. The bottleneck is
  almost never where intuition points.
- Set a target before you start (a latency budget, a throughput number) so you know when you are done, and measure
  again after to confirm the change moved the metric and did not just move the cost elsewhere.

---

### Data access

- Avoid the N+1 query problem. Batch related lookups, and never run a query inside a loop when one query would do.
- Fetch only the data you need: select only the columns a query uses, and page large result sets rather than loading
  everything.
- Add the indexes the real queries require, and confirm with the database's own query plan that they are used. An
  index nobody queries is write-cost for no read benefit.

---

### Caching

Cache where reads dominate and the data tolerates slight staleness, with a clear rule for invalidating it. A cache
without an invalidation story is a correctness bug waiting to surface. Name the staleness you accept and the event
that clears the entry.

---

### Memory and concurrency

- Build a string from many pieces with a join or a buffer, never by repeated concatenation in a loop.
- Stream large data lazily instead of loading it all into memory. A file or result set that fits today overflows
  tomorrow.
- Run independent input and output work concurrently rather than one call after another. Sequential awaits of
  unrelated calls waste the slowest one's whole duration.
