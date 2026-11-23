---
name: ai-regression-testing
description: 'Regression tests for the defects AI-written code repeats: response contracts, sandbox parity. Use when the user says "an agent changed my API routes" or "the same bug keeps coming back". Not for TDD, use `tdd-workflow`.'
metadata:
  version: "1.1.0"
---

# AI Regression Testing

When the same model writes code and then reviews it, it carries the same assumptions into both steps, so a whole class of defect survives review and only a mechanical test catches it. This skill covers the test selection and assertion shapes that target that class. `coding-standards` is the baseline and `tdd-workflow` owns the core discipline this sits on top of.

The patterns are about the shape of the assertion, not the framework: the examples use Next.js route handlers with Vitest, and other stacks translate the harness and keep the assertion.

| Task | Open |
| --- | --- |
| Applying a rule below: the four-fix sequence, the review order, the contract, parity and production-guard code, the pattern table, the bug-trail example | [patterns-and-examples.md](references/patterns-and-examples.md) |
| Wiring up the Vitest and Next.js harness: config, sandbox setup file, request helper, the harness on other stacks | [vitest-nextjs-harness.md](references/vitest-nextjs-harness.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling the regression work done | [checklist.md](references/checklist.md) |

---

### When not to activate

- The red-green-refactor loop, the test pyramid, and the coverage gate, use `tdd-workflow`.
- Browser journeys through the UI, use `e2e-testing`.
- Verifying a deployed capability against a live stack with an API client, use `e2e-runbooks`.

---

### Rules

1. The failure this skill targets. A model that reviews its own fix inherits the assumption behind the bug, so only a mechanical test catches it. Drift between a sandbox branch and a production branch is the common case.
2. Run the mechanical checks before the AI review. Tests first, then the type check or build, each failure the top finding. Only when both are green, review by reading with the blind spots in mind: path parity, response shape, projection completeness, error handling with rollback, optimistic update races. Every fixed defect gets a regression test. Name the verification command as the project's AGENTS.md does.
3. Assert the response contract, not the implementation. Declare the required fields once and assert the whole list with a presence assertion, which passes a present `null` and fails a missing field. Name the regression a test prevents.
4. Test sandbox and production parity. Both branches return the same shape, the sandbox one with explicit empty values. The service refuses to start with the sandbox flag set in production, reads no identity header outside the sandbox, and prefers an injected fake repository over a branch (CWE-489). Run the contract test once in sandbox and once against the production branch on a real database in a container the test owns. Parity means both pass.
5. Watch the four recurring patterns: projection omission, error state leakage (clear stale data on error), optimistic update without rollback (restore only the removed item at its index), and a type cast masking a null (assert not undefined).
6. Choose the next test by where bugs were found. AI repeats categories of mistake and bugs cluster in auth, multi-path logic and state, so follow the bug trail. The `tdd-workflow` coverage gate is unchanged.
