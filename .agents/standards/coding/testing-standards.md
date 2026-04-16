# Testing Standards

Universal testing rules. Language-specific standards files contain additional language-level testing rules.

---

## Coverage Requirements

Test coverage must be truly comprehensive:
- **Positive cases**: expected inputs produce expected outputs.
- **Negative cases**: invalid inputs are rejected correctly.
- **Edge cases**: boundary values, empty collections, null/nil inputs, maximum values.

Partial test coverage is a failure.

---

## Test Data

- Extract object creation to helper methods or a shared `TestDataFactory` class.
- Never repeat object construction inline across multiple test methods.
- Test data must be realistic and representative, not trivially minimal.

---

## Structure

Follow the AAA (Arrange / Act / Assert) pattern in every test:
1. **Arrange**: set up inputs, mocks, and preconditions.
2. **Act**: invoke the unit under test.
3. **Assert**: verify outputs and side effects.

Each test method must test exactly one behavior. Do not combine multiple assertions for unrelated behaviors in a single test.

---

## Naming

Test method names must describe what is being tested and the expected outcome:
- Pattern: `<methodName>_<scenario>_<expectedResult>`
- Example: `calculateTotal_withEmptyCart_returnsZero`

---

## Constraints

- Do not mock what you do not own. Prefer integration tests over mocking third-party libraries.
- Do not write tests that only verify mocks were called; test real behavior.
- Run all tests at once when verifying any change; never verify a single test in isolation.

---

## Test Pyramid

| Layer | Scope | Relative Volume | Tool Examples |
|---|---|---|---|
| Unit | Single class / function, all dependencies mocked | ~70% | JUnit, pytest, Vitest |
| Integration | Multiple components with real I/O (DB, queue) | ~20% | Testcontainers, httpx, SuperTest |
| Contract | Producer-consumer API compatibility | per service boundary | Pact, Spring Cloud Contract |
| End-to-End | Full user journey through deployed system | ~10% | Playwright, Cypress |

Do not compensate for missing unit tests with integration tests — integration tests are slower, harder to debug, and should verify wiring, not logic.

---

## Coverage Thresholds

- Minimum **80% line coverage** and **70% branch coverage** enforced as a CI quality gate.
- Coverage must not decrease on any PR. A PR that drops coverage below threshold is blocked from merging.
- Coverage exemptions (e.g., generated code, framework boilerplate) must be explicitly annotated and approved.
- 100% coverage is not the goal; covering all meaningful branches and edge cases is.

---

## Flaky Test Policy

- A test that fails non-deterministically is a **blocking defect**. It must be fixed or quarantined within 2 business days.
- Quarantined tests must be tracked in an issue and must not remain quarantined for more than 2 sprint cycles.
- Never use `sleep` / `Thread.sleep` as a synchronisation mechanism in tests; use proper async wait helpers or retry assertions.

---

## Contract Testing

- Every HTTP API that has external consumers must have a consumer-driven contract test (Pact or Spring Cloud Contract).
- The provider must verify all registered consumer contracts in CI before merging API changes.
- Breaking a contract is treated as a breaking API change and requires a version bump.

---

## Mutation Testing

- For critical business logic (pricing, auth, validation), run mutation testing (PIT for Java, Stryker for JS/TS) to verify test quality.
- A mutation score below 70% on a critical module is a quality gate failure.
- Mutation testing need not run on every PR — a weekly CI schedule is acceptable.

---

## Performance Testing

- Any endpoint or job on a critical path must have a baseline performance test (k6, Gatling, or `pytest-benchmark`).
- Performance tests must run in CI on the main branch after each merge; alert if p99 latency increases by more than 20%.
- Load tests simulating production-scale traffic must run before every major release.

---

## Test Environment Management

- Each test run must be fully isolated: no shared mutable state between tests or test runs.
- Integration tests must create and tear down their own data; never depend on pre-existing database state.
- Use Testcontainers or equivalent to spin up real infrastructure dependencies; do not rely on a shared staging database for automated tests.
