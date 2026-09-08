---
name: tdd-workflow
description: Test-driven development discipline covering the red-green-refactor loop with an enforced RED gate, the test pyramid, mocking boundaries, test naming and structure, and a CI coverage gate of around 90 percent line coverage of real logic. Use when you say "write this feature test first", "add tests for this bug fix", "our coverage gate is failing", "what should I mock here", or "refactor this without breaking behaviour". Not for browser journeys and the flaky-test policy, use `e2e-testing`.
---

# Test-Driven Development Workflow

Write the test before the code, watch it fail for the right reason, then make it pass. This skill owns the loop, the
coverage gate, and the mocking boundary. `coding-standards` is the hub above it and the language testing skills hold the
per-stack mechanics.

---

### When to activate

- Writing a new feature, an endpoint, or a component.
- Fixing a bug, where the test that reproduces it comes first.
- Refactoring, where the existing tests are the safety net that has to stay green.
- The coverage gate is failing, or a pull request is blocked on it.
- Deciding what to mock, or whether a test belongs at the unit, integration, or end-to-end layer.

---

### When not to activate

- Browser journeys through a real UI, and the flaky-test policy. Use `e2e-testing`, which is canonical for both.
- Capability sweeps against a deployed stack with an API client. Use `e2e-runbooks`.
- Regression tests aimed specifically at AI-introduced defects and sandbox-path drift. Use `ai-regression-testing`.
- Per-language mechanics: pytest fixtures and parametrisation, Go table-driven tests and fuzzing, JUnit slice tests. Use
  `python-testing`, `golang-testing`, or `springboot-tdd`.
- Load, soak, or capacity testing. Use `performance-optimization` for the measurement discipline instead.

---

### The loop

Write the user journey, turn it into test cases, watch them fail, implement the minimum, watch them pass, then refactor
under green.

State the journey in one sentence before writing any test, because a test suite that cannot be traced back to a journey
usually tests the implementation instead.

```text
As a signed-in customer, I want to search the catalogue by keyword,
so that I can find a product without knowing its exact name.
```

Turn the journey into cases that name the behaviour and the condition.

```typescript
describe('catalogue search', () => {
  it('returns matching products for a keyword', async () => {})
  it('returns an empty list for a query that matches nothing', async () => {})
  it('falls back to substring matching when the search index is unavailable', async () => {})
  it('orders results by relevance score, highest first', async () => {})
})
```

---

### The RED gate

Running the new test and seeing it fail is mandatory before any production code changes. A test that was written but
never executed proves nothing, and a failure caused by a typo proves nothing either.

```bash
npm test
```

A valid RED state is one of two things. Runtime RED: the target compiles, the new test actually executes, and the result
is a failure. Compile-time RED: the new test references code that does not exist yet, and the compile failure is itself
the signal.

In both cases the failure must be caused by the missing implementation or the bug under repair, not by unrelated syntax
errors, broken setup, missing dependencies, or a pre-existing regression elsewhere.

Fail: the failure is real but proves nothing about the behaviour under test.

```text
FAIL  src/search.test.ts
  Cannot find module '@/lib/testing/helpers'
```

Pass: the failure is the behaviour the test was written to demand.

```text
FAIL  src/search.test.ts > returns an empty list for a query that matches nothing
  expected [] but received undefined
```

Do not touch production code until a valid RED state is confirmed. Then implement the minimum that turns it green, rerun
the same target, and only refactor once green.

```bash
npm test
```

Refactoring under green means removing duplication, improving names, and simplifying structure, with the suite rerun
after each step.

---

### Coverage gate

Around 90 percent line coverage of real logic, across unit, integration and end-to-end tests combined. Branch coverage
sits at 70 to 80 percent. Critical logic reaches 100 percent where that genuinely adds value rather than as a ritual. No
exclusion pattern may be added to dodge a meaningful test, and every edge case, error path, and boundary condition is
covered.

Enforce it as a CI gate so a pull request that drops coverage below the threshold is blocked.

Fail: the config key is plural, so Jest ignores the whole block and the gate never fires.

```json
{
  "jest": {
    "coverageThresholds": {
      "global": { "branches": 70, "functions": 90, "lines": 90, "statements": 90 }
    }
  }
}
```

Pass: the key Jest actually reads.

```json
{
  "jest": {
    "coverageThreshold": {
      "global": { "branches": 70, "functions": 90, "lines": 90, "statements": 90 }
    }
  }
}
```

Verify locally before pushing.

```bash
npm run test:coverage
```

---

### Test layers

Three layers, with the bulk of the suite at the bottom. The proportions and the tooling per layer are in
[references/advanced-testing.md](references/advanced-testing.md).

- Unit. Individual functions, pure logic, component behaviour, helpers. No input or output.
- Integration. Endpoints, data access, service interactions, external boundaries, run against real engines through
  Testcontainers.
- End-to-end. Critical user journeys through the real UI. `e2e-testing` owns this layer entirely, including the
  Playwright patterns, locator rules, and CI wiring. Write the journeys there and reference them from here.

---

### Test naming

Descriptive names in the project's existing style win. A reader who has never seen the code should learn the behaviour
and the condition from the name alone.

Match what the project already does. Where a project has no convention, use the natural-language form from
`coding-standards`, which is the canonical rule: a sentence describing the behaviour and the condition that triggers it.

Fail: names that describe nothing.

```typescript
test('works', () => {})
test('test search 2', () => {})
test('happyPath', () => {})
```

Pass: natural-language form, the default.

```typescript
test('returns an empty list when no product matches the query', () => {})
test('throws when the API key is missing', () => {})
```

Pass: the `<method>_<scenario>_<expectedResult>` form, which is the same rule spelled differently and is idiomatic in
JUnit codebases. Use it when the project already uses it, not as a second convention alongside the first.

```java
@Test
void calculateTotal_withEmptyCart_returnsZero() { }

@Test
void processPayment_whenCardDeclined_throwsPaymentException() { }
```

The two forms are alternatives, never a mix inside one codebase.

---

### Test structure

Every test sets up state, performs one action, then asserts the observable outcome. Which words label the three phases
is the project's choice: `Arrange` / `Act` / `Assert` and `Given` / `When` / `Then` are the common spellings. Read the
existing tests and match them.

One behaviour per test. Several assertions are fine when they all verify that one behaviour, and each test builds its
own data so the order tests run in never matters.

Fail: the second test depends on the first.

```typescript
test('creates a user', () => { createUser('alice') })
test('updates the same user', () => { updateUser('alice', { name: 'Alicia' }) })
```

Pass: each test owns its setup.

```typescript
test('creates a user', () => {
  const user = createTestUser()
  expect(findUser(user.id)).toBeDefined()
})

test('updates a user', () => {
  const user = createTestUser()
  updateUser(user.id, { name: 'Alicia' })
  expect(findUser(user.id).name).toBe('Alicia')
})
```

---

### Test what the user observes

Assert the behaviour the caller can see, not the internal state that produced it. A test coupled to internals fails on
every refactor and passes through real defects.

Fail:

```typescript
expect(component.state.count).toBe(5)
```

Pass:

```typescript
expect(screen.getByText('Count: 5')).toBeInTheDocument()
```

Never weaken an assertion to make a test pass. Fix the code, or fix the setup that was wrong.

---

### Mocking boundaries

Mock only what you own, and only in unit tests. Do not mock the database when you can exercise it: integration tests run
against a real engine through Testcontainers, never a shared staging instance. For third-party HTTP clients, ORMs, and
cloud SDKs, prefer a real instance, the library's own official test double, or an HTTP-level fake such as WireMock or
MSW. The detail behind both rules is in [references/advanced-testing.md](references/advanced-testing.md).

The mocks below are unit-test doubles for a boundary the test does not own, not a substitute for exercising the real
datastore.

A repository, mocked at the interface the application defines.

```typescript
jest.mock('@/lib/repositories/product-repository', () => ({
  productRepository: {
    findByKeyword: jest.fn(async () => [{ id: 1, name: 'Test Product' }]),
    findById: jest.fn(async () => ({ id: 1, name: 'Test Product' })),
  },
}))
```

An external HTTP client, mocked at the project's own wrapper rather than at the vendor SDK.

```typescript
jest.mock('@/lib/clients/search-client', () => ({
  searchClient: {
    query: jest.fn(async () => [{ id: 'test-product', score: 0.95 }]),
    health: jest.fn(async () => ({ reachable: true })),
  },
}))
```

Note what both examples have in common: the seam is an interface the project defines, so the mock stays valid when the
vendor library changes underneath it.

---

### Flaky tests

`e2e-testing` holds the canonical flaky-test policy: the fix-or-quarantine SLA, the maximum quarantine period, what
happens when it expires, the prohibited sleep patterns, and when a framework retry is allowed. It applies to every
layer, not only browser tests. Do not restate it here, and do not adopt a second policy alongside it.

---

### Continuous testing

Run the suite in watch mode while developing.

```bash
npm test -- --watch
```

Gate the commit on tests and lint.

```bash
npm test && npm run lint
```

In CI, run with coverage and upload the report.

```yaml
- name: Run tests
  run: npm test -- --coverage
- name: Upload coverage
  uses: codecov/codecov-action@v7
```

---

### Reference map

| Task | Open |
| --- | --- |
| Test pyramid proportions, contract testing, mutation testing, performance testing, JaCoCo and PIT config, the Testcontainers mandate, the test data factory pattern | [references/advanced-testing.md](references/advanced-testing.md) |

---

### Related skills

- `coding-standards` holds the canonical test-naming and test-structure rules this skill applies.
- `e2e-testing` owns the browser layer and the flaky-test policy.
- `e2e-runbooks` owns capability verification against a deployed stack.
- `ai-regression-testing` owns bug-driven regression tests and sandbox-path parity.
- `python-testing`, `golang-testing`, `springboot-tdd` hold the per-language mechanics.
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
