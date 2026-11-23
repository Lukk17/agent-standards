# Scope

Companion reference for the [ai-regression-testing](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

The skill covers regression testing for the blind spots of AI-assisted development: bug-driven test selection, response-contract assertions, sandbox and production path parity, and mechanical checks before any AI review. It applies when:

- An AI agent has modified API routes, serialisers, or backend logic and the change needs a mechanical check, or the
  user says "an agent changed my API routes".
- A bug was just found and fixed, and it must not come back, or the user says "write a regression test for this bug".
- The project has a sandbox or mock mode that lets a route be tested without a shared database, as in "test this route without a shared database".
- The same defect has appeared more than once in the same area, or the user says "the same bug keeps coming back".
- Multiple code paths exist for one behaviour: sandbox against production, or a feature flag with two branches, or
  the user says "the sandbox path drifted from production".

---

### When not to activate

- The red-green-refactor loop, the test pyramid, and the coverage gate. Use `tdd-workflow`.
- Browser journeys through the UI. Use `e2e-testing`.
- Verifying a deployed capability against a live stack with an API client. Use `e2e-runbooks`.
- Language-level test mechanics: fixtures, parametrisation, table-driven tests. Use `python-patterns`,
  `golang-patterns`, or `springboot-patterns`.
- Reviewing the change by reading it. Use `code-reviewer`, and treat this skill as the step that runs before that
  review.

---

### Related skills

- `tdd-workflow` owns the red-green-refactor loop, the test pyramid, and the coverage gate this skill defers to.
- `e2e-testing` owns browser journeys and the canonical flaky-test policy.
- `e2e-runbooks` owns capability sweeps against a deployed stack.
- `code-reviewer` is the review pass that runs after the mechanical checks in this skill are green.
- `coding-standards` holds the error-handling and state conventions the failure patterns of this skill violate.
