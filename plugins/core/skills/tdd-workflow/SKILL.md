---
name: tdd-workflow
description: 'Test-driven development: the red-green-refactor loop with an enforced RED gate, the test pyramid, mocking boundaries, test naming and isolation, and a CI coverage gate of around 90 percent of real logic. Use when the user says "write this feature test first", "add tests for this bug fix", or "what should I mock here". Not for browser journeys and the flaky-test policy, use `e2e-testing`.'
---

# Test-Driven Development Workflow

Write the test before the code, watch it fail for the right reason, then make it pass. This skill owns the loop, the
coverage gate, and the mocking boundary. `coding-standards` is the hub above it and the language testing skills hold the
per-stack mechanics.

---

### When to activate

- Writing a new feature, an endpoint, or a component, or the user says "write this feature test first".
- Fixing a bug, where the test that reproduces it comes first, or the user says "add tests for this bug fix".
- Refactoring, where the existing tests are the safety net that has to stay green, or the user says "refactor this
  without breaking behaviour".
- The coverage gate is failing, or a pull request is blocked on it, or the user says "our coverage gate is failing".
- Deciding what to mock, or whether a test belongs at the unit, integration, or end-to-end layer.

---

### When not to activate

- Browser journeys through a real UI, and the flaky-test policy. Use `e2e-testing`, which is canonical for both.
- Capability sweeps against a deployed stack with an API client. Use `e2e-runbooks`.
- Regression tests aimed specifically at AI-introduced defects and sandbox-path drift. Use `ai-regression-testing`.
- Per-language mechanics: pytest fixtures and parametrisation, Go table-driven tests and fuzzing, JUnit slice tests. Use
  `python-patterns`, `golang-patterns`, or `springboot-patterns`.
- Load, soak, or capacity testing. Use `performance-optimization` for the measurement discipline instead.

---

### Rules

1. The loop. State the user journey in one sentence, turn it into cases named for behaviour and condition, watch them fail, implement the minimum, watch them pass, then refactor under green.
2. The RED gate. Run the new test and see it fail before any production code changes. Valid RED is runtime (it compiles, runs and fails) or compile-time (it references code that does not exist yet), caused by the missing behaviour or the bug, never by a typo, broken setup, a missing dependency or an unrelated regression. Refactor only under green, rerunning after each step.
3. Coverage gate. Around 90 percent line coverage of real logic across all layers, branch coverage 70 to 80 percent, 100 percent on critical logic where it adds value, every edge case, error path and boundary covered, and no exclusion added to dodge a meaningful test. Enforce it in CI, with the config key the tool actually reads (Jest reads `coverageThreshold`, not `coverageThresholds`).
4. Test layers. Most tests are unit tests with no I/O. Integration tests run against real engines through Testcontainers. End-to-end journeys belong entirely to `e2e-testing`.
5. Test naming. Match the project's style. With none, use the natural-language sentence from `coding-standards`. `<method>_<scenario>_<expectedResult>` is the JUnit spelling of the same rule, never mixed with the first in one codebase.
6. Test structure. The three phases follow `coding-standards`. One behaviour per test, several assertions allowed, and each test builds its own data so order never matters.
7. Test what the user observes, not internal state, and never weaken an assertion to get green.
8. Mocking boundaries. Mock only interfaces the project owns, only in unit tests. Never mock a database you can exercise, and never use a shared staging instance. For third-party HTTP clients, ORMs and cloud SDKs, prefer a real instance, the official test double, or an HTTP fake such as WireMock or MSW.
9. Flaky tests. `e2e-testing` holds the one flaky-test policy, for every layer. Do not restate it or adopt a second one.
10. Continuous testing. Watch mode while developing, tests and lint gate the commit, CI runs with coverage and uploads the report through an action pinned to a full commit SHA.

---

### Reference map

| Task | Open |
| --- | --- |
| Applying a rule above: the journey and case examples, RED pass and fail output, the Jest coverage block, naming forms, isolation, mock seams, the watch, commit and CI commands | [references/loop-and-rules.md](references/loop-and-rules.md) |
| Test pyramid proportions, contract testing, mutation testing, performance testing, JaCoCo and PIT config, the Testcontainers mandate, the test data factory pattern | [references/advanced-testing.md](references/advanced-testing.md) |

---

### Related skills

- `coding-standards` holds the canonical test-naming and test-structure rules this skill applies.
- `e2e-testing` owns the browser layer and the flaky-test policy.
- `e2e-runbooks` owns capability verification against a deployed stack.
- `ai-regression-testing` owns bug-driven regression tests and sandbox-path parity.
- `python-patterns`, `golang-patterns`, `springboot-patterns` hold the per-language mechanics.
- `performance-optimization` owns the measurement discipline when a test proves something is slow.

---

### Checklist

- [ ] A user journey was stated before the first test was written.
- [ ] The test was executed and produced a valid RED for the intended reason.
- [ ] No production code changed before that RED was confirmed.
- [ ] The implementation is the minimum that turns the test green.
- [ ] Refactoring happened only under green, with the suite rerun after each step.
- [ ] Around 90 percent line coverage of real logic, branch coverage 70 to 80 percent, enforced in CI.
- [ ] The coverage config uses the key the tool actually reads.
- [ ] Test names describe behaviour and condition, in one convention across the codebase.
- [ ] Every test builds its own data and passes in any order.
- [ ] Assertions target observable behaviour, and none was weakened to get green.
- [ ] Mocks sit at interfaces the project owns, and integration tests use Testcontainers.
- [ ] The full suite ran, not just the one test that was being fixed.
- [ ] No test is skipped or disabled without a tracked quarantine entry.
