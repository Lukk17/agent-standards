---
name: tdd-workflow
description: 'The test-driven loop: red, green, refactor, with mocking boundaries and a coverage gate. Use when the user says "write this feature test first" or "what should I mock here". Not for browser tests, use `e2e-testing`.'
metadata:
  version: "1.1.0"
---

# Test-Driven Development Workflow

Write the test before the code, watch it fail for the right reason, then make it pass. This skill owns the loop, the coverage gate, and the mocking boundary.

---

### When not to activate

- Browser journeys through a real UI, and the flaky-test policy, use `e2e-testing`.
- Capability sweeps against a deployed stack with an API client, use `e2e-runbooks`.
- Per-language test mechanics, use `python-patterns`, `golang-patterns` or `springboot-patterns`.

---

### Rules

1. The loop. State the user journey in one sentence, turn it into cases named for behaviour and condition, watch them fail, implement the minimum, watch them pass, then refactor under green.
2. The RED gate. Run the new test and see it fail before any production code changes. Valid RED is runtime (it compiles, runs and fails) or compile-time (it references code that does not exist yet), caused by the missing behaviour or the bug, never by a typo, broken setup, a missing dependency or an unrelated regression. Refactor only under green, rerunning after each step.
3. Coverage gate. Around 90 percent line coverage of real logic across all layers, branch coverage 70 to 80 percent, 100 percent on critical logic where it adds value, and no exclusion added to dodge a meaningful test. Enforce it in CI, with the config key the tool actually reads.
4. Test layers. Most tests are unit tests with no I/O. Integration tests run against real engines in containers the test owns. End-to-end journeys belong entirely to `e2e-testing`.
5. Test naming. Match the project's style. With none, use the natural-language sentence from `coding-standards`. Never mix two naming forms in one codebase.
6. Test structure. The three phases follow `coding-standards`. One behaviour per test, several assertions allowed, and each test builds its own data so order never matters.
7. Test what the user observes, not internal state, and never weaken an assertion to get green.
8. Mocking boundaries. Mock only interfaces the project owns, only in unit tests. Never mock a database you can exercise, and never use a shared staging instance. For third-party HTTP clients, ORMs and cloud SDKs, prefer a real instance, the official test double, or a fake at the wire protocol.
9. Flaky tests. `e2e-testing` holds the one flaky-test policy, for every layer. Do not restate it or adopt a second one.
10. Continuous testing. Watch mode while developing, tests and lint gate the commit, CI runs with coverage and uploads the report through an action pinned to a full commit SHA.
11. Test comments. The only comments in a test are the bare `// Given`, `// When`, `// Then` and `// When & Then` markers. No divider banner, section label, file-header description or trailing explanation: the meaning goes into the test name.
12. Test file size. A test class or file past about 300 lines covers several behaviours, so split it into focused classes named for the behaviour, sharing builders through one `<Subject>TestFixtures`, and fold a coverage-driven `*BranchTest` into the behaviour class it belongs to.

---

### Reference map

| Task | Open |
| --- | --- |
| A rule above in full: its reasoning, pass and fail forms | [loop-and-rules.md](references/loop-and-rules.md) |
| The test pyramid, test data factories, contract, mutation and performance testing, what may be mocked | [advanced-testing.md](references/advanced-testing.md) |
| The project is JavaScript or TypeScript: the Jest, npm and CI forms | [jest.md](references/jest.md) |
| The project is on the JVM: JUnit, JaCoCo, PIT, Spring Cloud Contract, Testcontainers | [jvm-testing.md](references/jvm-testing.md) |
| A load test runs on k6 | [k6.md](references/k6.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling the work done | [checklist.md](references/checklist.md) |
