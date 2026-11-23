# Scope

Companion reference for the [tdd-workflow](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

This skill owns the loop, the coverage gate, and the mocking boundary. `coding-standards` is the hub above it and the language testing skills hold the per-stack mechanics. It applies when:

- Writing a new feature, an endpoint, or a component, or the user says "write this feature test first".
- Fixing a bug, where the test that reproduces it comes first, or the user says "add tests for this bug fix".
- Refactoring, where the existing tests are the safety net that has to stay green, or the user says "refactor this
  without breaking behaviour".
- The coverage gate is failing, or a pull request is blocked on it, or the user says "our coverage gate is failing".
- Deciding what to mock, as in "what should I mock here", or whether a test belongs at the unit, integration, or end-to-end layer.

---

### When not to activate

- Browser journeys through a real UI, and the flaky-test policy. Use `e2e-testing`, which is canonical for both.
- Capability sweeps against a deployed stack with an API client. Use `e2e-runbooks`.
- Regression tests aimed specifically at AI-introduced defects and sandbox-path drift. Use `ai-regression-testing`.
- Per-language mechanics: pytest fixtures and parametrisation, Go table-driven tests and fuzzing, JUnit slice tests. Use
  `python-patterns`, `golang-patterns`, or `springboot-patterns`.
- Load, soak, or capacity testing. Use `performance-optimization` for the measurement discipline instead.

---

### Related skills

- `coding-standards` holds the canonical test-naming and test-structure rules this skill applies.
- `e2e-testing` owns the browser layer and the flaky-test policy.
- `e2e-runbooks` owns capability verification against a deployed stack.
- `ai-regression-testing` owns bug-driven regression tests and sandbox-path parity.
- `python-patterns`, `golang-patterns`, `springboot-patterns` hold the per-language mechanics.
- `performance-optimization` owns the measurement discipline when a test proves something is slow.
