---
name: e2e-runbooks
description: 'Capability testing against a live stack, one feature per immutable spec, with behaviour-only assertions, canary fixtures, setup-cost ordering, token and duration accounting, and parallel subagents. Use when the user says "add an e2e test for the upload flow", "run the e2e sweep" or "verify this capability end to end". Not for Playwright browser UI testing, use `e2e-testing`.'
---

# E2E Runbooks

Verify that a deployed service actually does what it claims when poked from outside, one capability per spec, asserted
only on what the running system shows. Each spec has a paired immutable tasks-template, and every execution leaves a
timestamped run record with token and duration accounting.

---

### When to activate

- Adding, running, or refining an end-to-end capability test against a live or staging stack.
- Running a sweep across the whole capability suite and aggregating the verdicts.
- Verifying that an MCP tool, a background ingestion job, or a multi-service flow works end to end.
- Smoke testing a deployment before promoting it.
- Setting up the `e2e/` directory tree in a project that has none.
- The user says "test that the MCP tool actually fires" or "smoke test against the staging stack".

---

### When not to activate

- Browser and UI journeys. Use `e2e-testing`, which owns Playwright.
- Unit and integration tests inside the codebase. Use `tdd-workflow`, `python-patterns`, `golang-patterns`, or
  `springboot-patterns`.
- Sandbox-mode API regression tests that need no deployed stack. Use `ai-regression-testing`.
- Load, soak, or chaos testing. Out of scope: this skill is about correctness, not capacity or resilience.
- Designing the API being tested. Use `api-design`.

---

### Reference map

| Task | Open |
| --- | --- |
| Scaffold the `e2e/` tree and `.gitignore`, the three-file triple, the seven spec sections and the tasks-template | [references/spec-format.md](references/spec-format.md) |
| Behaviour-only assertions with examples, the `{N}` cost table, canary fixtures, the API client table | [references/writing-tests.md](references/writing-tests.md) |
| Run record naming, the nine-step runner contract, sweeps, the readiness banner | [references/running-tests.md](references/running-tests.md) |
| Write a spec from a worked example: curl, MCP tool round trip, fixture upload and retrieval | [references/examples.md](references/examples.md) |
| Set the parallel cap, declare what a test mutates, schedule a sweep around conflicts | [references/orchestration.md](references/orchestration.md) |
| Install the companion OpenSpec schema for slash-command lifecycle integration | [references/openspec-schema.md](references/openspec-schema.md) |

---

### Rules

1. Scaffold `e2e/` once per project (the OpenSpec schema does it on first use), and gitignore `e2e/testing/runs/*.md` except the runs README.
2. Every capability is three files: the immutable spec `e2e/testing/{N}-{capability}-test.md`, the immutable template under `templates/`, and the run record under `runs/` named `{utc-timestamp}_{N}-{capability}-tasks.md`.
3. Never edit a spec or a template to make a failing run pass. Fix the system, or write a new spec with a new `{N}`.
4. Every spec has seven sections in order: What this verifies, Prerequisites, Reset state, Run, Expected, Fixtures, Concurrency (with a `Serial:` flag).
5. Assert only what the API or directly queried persisted state shows, never a log substring. A log tail is the next diagnostic step, not a pass criterion.
6. Number `{N}` by setup cost, lowest unused number in the class, so cheap failures stop a sweep before expensive tests run.
7. Every upload fixture carries canary content the model could not have memorised, stays small enough to upload in under two seconds, lives in `e2e/fixtures/`, and is recorded in `e2e/fixtures/README.md`.
8. Pin one API client per project. Drive an MCP tool test through the agent, not the MCP server directly.
9. One UTC timestamp, with colons replaced by hyphens, names every run record of one sweep.
10. The runner records Start first, ticks tasks in spec order, records End, computes wall-clock Duration, fills token counts or leaves them blank rather than inventing them, and writes the Result summary, the Verdict and any off-spec work.
11. For more than one test the main session delegates: one `e2e-runner` subagent per spec in `{N}` order, never running a client or ticking boxes itself, never editing a spec mid-sweep. A single test being debugged can run inline.
12. The default parallel cap is 5, confirmed with the user before each sweep and never exceeded. Conflicting tests serialise below it.
13. When the service has the startup-readiness banner, check it once at sweep start and fix any `[FAILED]` dependency before running tests.

---

### Related skills

- `e2e-testing` owns browser and UI testing with Playwright, and the canonical flaky-test policy.
- `tdd-workflow` owns unit and integration tests inside the codebase, along with `python-patterns`,
  `golang-patterns` and `springboot-patterns`.
- `ai-regression-testing` owns sandbox-mode API regression tests that need no deployed stack.
- `observability-and-logging` owns the startup-readiness banner this skill reads at sweep start.
- `docker-patterns` owns the local stack the tests are pointed at.

---

### Checklist

- [ ] One capability per spec, one spec per file, seven sections in order.
- [ ] Every assertion is observable through the API or the persisted state, never a log line.
- [ ] The `{N}` prefix matches the test's real setup cost class.
- [ ] Every fixture carries canary content the model could not have memorised.
- [ ] The Reset section wipes everything the Run section writes.
- [ ] The Concurrency section names every resource the test mutates.
- [ ] The spec and template were not edited to make a run pass.
- [ ] Every run record carries Start, End, Duration, token counts, a Result summary, and a Verdict.
- [ ] A sweep used one timestamp across every run record.
- [ ] The parallel cap was confirmed with the user before fan-out.
