# AI Regression Testing Checklist

Run it before calling the regression work done.

- [ ] The test suite and the type check ran before any review by reading.
- [ ] Every fixed defect gained a regression test named after the bug it prevents.
- [ ] Response contracts are asserted as a declared field list, not one field at a time.
- [ ] Both sides of every sandbox or feature-flag branch satisfy the same contract, each proven by its own run.
- [ ] The sandbox branch refuses to start in production and reads no identity header outside the sandbox.
- [ ] Query projections were checked whenever a response field was added.
- [ ] Error paths clear the state they invalidate.
- [ ] Optimistic updates restore only the item they removed, so an overlapping update is not undone.
- [ ] Test selection follows the bug trail, and the `tdd-workflow` coverage gate is still met.
