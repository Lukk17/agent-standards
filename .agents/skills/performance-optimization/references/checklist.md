# Performance Optimization Checklist

Run it before calling an optimisation done.

- [ ] A profile or a metric, not a hunch, identified the bottleneck.
- [ ] A target number was set before the change and measured again after.
- [ ] No query runs inside a loop over rows a previous query returned.
- [ ] Queries select named columns and page their results.
- [ ] Every index added is confirmed used by the query plan.
- [ ] Every cache was justified by a profile and follows the `backend-patterns` invalidation rule.
- [ ] Large payloads stream rather than materialise.
- [ ] Independent IO runs concurrently with a bounded fan-out.
- [ ] The metric moved, and the change did not just move the cost elsewhere.
