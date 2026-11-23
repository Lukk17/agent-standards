---
name: e2e-runbooks
description: 'API-client capability checks of a deployed stack, one immutable spec each. Use when the user says "run the e2e sweep" or "smoke test the staging stack". Not for browser tests, use `e2e-testing`.'
metadata:
  version: "1.1.0"
---

# E2E Runbooks

Verify that a deployed service actually does what it claims when poked from outside, one capability per spec, asserted only on what the running system shows. Each spec has a paired immutable tasks-template, and every execution leaves a timestamped run record with token and duration accounting.

---

### When not to activate

- Browser and UI journeys, use `e2e-testing`, which owns Playwright.
- Unit and integration tests inside the codebase, use `tdd-workflow`.
- Sandbox-mode API regression tests that need no deployed stack, use `ai-regression-testing`.

---

### Reference map

| Task | Open |
| --- | --- |
| Scaffold the `e2e/` tree and `.gitignore`, the three-file triple, the seven spec sections and the tasks-template | [spec-format.md](references/spec-format.md) |
| Behaviour-only assertions with examples, the `{N}` cost table, canary fixtures, the API client table | [writing-tests.md](references/writing-tests.md) |
| Run record naming, the nine-step runner contract, sweeps, the readiness banner | [running-tests.md](references/running-tests.md) |
| Write a spec from a worked example: curl, MCP tool round trip, fixture upload and retrieval | [examples.md](references/examples.md) |
| Set the parallel cap, declare what a test mutates, schedule a sweep around conflicts | [orchestration.md](references/orchestration.md) |
| The project uses OpenSpec and wants the slash-command lifecycle | [openspec-schema.md](references/openspec-schema.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling a spec, a run or a sweep done | [checklist.md](references/checklist.md) |

---

### Rules

1. Scaffold `e2e/` once per project, and gitignore `e2e/testing/runs/*.md` except the runs README.
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
