---
name: ai-regression-testing
description: 'Regression testing for the blind spots of AI-assisted development: bug-driven test selection, response-contract assertions, sandbox and production path parity, and mechanical checks before any AI review. Use when the user says "an agent changed my API routes", "the same bug keeps coming back", or "test this route without a shared database". Not for the red-green-refactor loop, use `tdd-workflow`.'
---

# AI Regression Testing

When the same model writes code and then reviews it, it carries the same assumptions into both steps, so a whole class
of defect survives review and only a mechanical test catches it. This skill covers the test selection and assertion
shapes that target that class. `coding-standards` is the baseline and `tdd-workflow` owns the core discipline this sits
on top of.

The patterns are about the shape of the assertion, not the framework: the examples use Next.js route handlers with Vitest, and other stacks translate the harness and keep the assertion.

| Task | Open |
| --- | --- |
| Applying a rule below: the four-fix sequence, the review order, the contract, parity and production-guard code, the pattern table, the bug-trail example | [references/patterns-and-examples.md](references/patterns-and-examples.md) |
| Wiring up the Vitest and Next.js harness: config, sandbox setup file, request helper | [references/vitest-nextjs-harness.md](references/vitest-nextjs-harness.md) |

---

### When to activate

- An AI agent has modified API routes, serialisers, or backend logic and the change needs a mechanical check, or the
  user says "an agent changed my API routes".
- A bug was just found and fixed, and it must not come back, or the user says "write a regression test for this bug".
- The project has a sandbox or mock mode that lets a route be tested without a shared database.
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

### Rules

1. The failure this skill targets. A model that reviews its own fix inherits the assumption behind the bug, so only a mechanical test catches it. Drift between a sandbox branch and a production branch is the common case.
2. Run the mechanical checks before the AI review. Tests first, then the type check or build, each failure the top finding. Only when both are green, review by reading with the blind spots in mind: path parity, response shape, projection completeness, error handling with rollback, optimistic update races. Every fixed defect gets a regression test. Name the verification command as the project's AGENTS.md does.
3. Assert the response contract, not the implementation. Declare the required fields once and assert the whole list with `toHaveProperty`, which passes a present `null` and fails a missing field. Name the regression a test prevents.
4. Test sandbox and production parity. Both branches return the same shape, the sandbox one with explicit empty values. The service refuses to start with the sandbox flag set in production, reads no identity header outside the sandbox, and prefers an injected fake repository over a branch (CWE-489). Run the contract test once in sandbox and once against the production branch on Testcontainers; parity means both pass.
5. Watch the four recurring patterns: projection omission, error state leakage (clear stale data on error), optimistic update without rollback (restore only the removed item at its index), and a type cast masking a null (assert not undefined).
6. Choose the next test by where bugs were found. AI repeats categories of mistake and bugs cluster in auth, multi-path logic and state, so follow the bug trail. The `tdd-workflow` coverage gate is unchanged.

---

### Related skills

- `tdd-workflow` owns the red-green-refactor loop, the test pyramid, and the coverage gate this skill defers to.
- `e2e-testing` owns browser journeys and the canonical flaky-test policy.
- `e2e-runbooks` owns capability sweeps against a deployed stack.
- `code-reviewer` is the review pass that runs after the mechanical checks in this skill are green.
- `coding-standards` holds the error-handling and state conventions the failure patterns above violate.

---

### Checklist

- [ ] The test suite and the type check ran before any review by reading.
- [ ] Every fixed defect gained a regression test named after the bug it prevents.
- [ ] Response contracts are asserted as a declared field list, not one field at a time.
- [ ] Both sides of every sandbox or feature-flag branch satisfy the same contract, each proven by its own run.
- [ ] The sandbox branch refuses to start in production and reads no identity header outside the sandbox.
- [ ] Query projections were checked whenever a response field was added.
- [ ] Error paths clear the state they invalidate.
- [ ] Optimistic updates restore only the item they removed, so an overlapping update is not undone.
- [ ] Test selection follows the bug trail, and the `tdd-workflow` coverage gate is still met.
