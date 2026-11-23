# Scope

Companion reference for the [e2e-runbooks](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

The skill covers capability testing against a live stack, one feature per immutable spec, with behaviour-only assertions, canary fixtures, setup-cost ordering, token and duration accounting, and parallel subagents. It applies when:

- Adding, running, or refining an end-to-end capability test against a live or staging stack, as in "add an e2e test for the upload flow" when the test drives the API of a deployed stack rather than a browser.
- Running a sweep across the whole capability suite and aggregating the verdicts, as in "run the e2e sweep".
- Verifying that an MCP tool, a background ingestion job, or a multi-service flow works end to end, as in "verify this capability end to end" or "test that the MCP tool actually fires".
- Smoke testing a deployment before promoting it, as in "smoke test against the staging stack".
- Setting up the `e2e/` directory tree in a project that has none.

---

### When not to activate

- Browser and UI journeys. Use `e2e-testing`, which owns Playwright.
- Unit and integration tests inside the codebase. Use `tdd-workflow`, `python-patterns`, `golang-patterns`, or
  `springboot-patterns`.
- Sandbox-mode API regression tests that need no deployed stack. Use `ai-regression-testing`.
- Load, soak, or chaos testing. Out of scope: this skill is about correctness, not capacity or resilience.
- Designing the API being tested. Use `api-design`.

---

### Related skills

- `e2e-testing` owns browser and UI testing with Playwright, and the canonical flaky-test policy.
- `tdd-workflow` owns unit and integration tests inside the codebase, along with `python-patterns`,
  `golang-patterns` and `springboot-patterns`.
- `ai-regression-testing` owns sandbox-mode API regression tests that need no deployed stack.
- `observability-and-logging` owns the startup-readiness banner this skill reads at sweep start.
- `docker-patterns` owns the local stack the tests are pointed at.
