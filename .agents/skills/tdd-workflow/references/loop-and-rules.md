# Loop and Rules

Contents:

- [The loop](#the-loop)
- [The RED gate](#the-red-gate)
- [Coverage gate](#coverage-gate)
- [Test layers](#test-layers)
- [Test naming](#test-naming)
- [Test structure](#test-structure)
- [Test comments](#test-comments)
- [Test file size](#test-file-size)
- [Test what the user observes](#test-what-the-user-observes)
- [Mocking boundaries](#mocking-boundaries)
- [Flaky tests](#flaky-tests)
- [Continuous testing](#continuous-testing)

The red-green-refactor loop and every testing rule in SKILL.md in full, with the reasoning and the pass and fail forms that need no framework. The form each rule takes in a JavaScript or TypeScript project, with the Jest coverage key, the commands and the CI upload pin, is in [jest.md](jest.md), and the JUnit form is in [jvm-testing.md](jvm-testing.md). Load this file when applying a rule and the one-line summary in SKILL.md is not enough.

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

Turn the journey into cases that name the behaviour and the condition. The cases this journey gives are written out as a test skeleton in [jest.md](jest.md#cases-from-a-journey).

---

### The RED gate

Running the new test and seeing it fail is mandatory before any production code changes. A test that was written but
never executed proves nothing, and a failure caused by a typo proves nothing either.

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

Refactoring under green means removing duplication, improving names, and simplifying structure, with the suite rerun
after each step.

---

### Coverage gate

Around 90 percent line coverage of real logic, across unit, integration and end-to-end tests combined. Branch coverage
sits at 70 to 80 percent. Critical logic reaches 100 percent where that genuinely adds value rather than as a ritual. No
exclusion pattern may be added to dodge a meaningful test, and every edge case, error path, and boundary condition is
covered.

Enforce it as a CI gate so a pull request that drops coverage below the threshold is blocked, and verify locally before pushing.

Write the gate with the config key the tool actually reads. Jest reads `coverageThreshold`, not `coverageThresholds`: with the plural key Jest ignores the whole block and the gate never fires. The Jest key, with its failing and passing form, is in [jest.md](jest.md#coverage-threshold), and the JaCoCo rule is in [jvm-testing.md](jvm-testing.md#coverage-configuration-with-jacoco).

---

### Test layers

Three layers, with the bulk of the suite at the bottom. The proportions and the tooling per layer are in
[advanced-testing.md](advanced-testing.md).

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
`coding-standards`, which is the canonical rule: a sentence describing the behaviour and the condition that triggers it. The names that describe nothing and the natural-language names that pass are in [jest.md](jest.md#test-naming).

The `<method>_<scenario>_<expectedResult>` form is the same rule spelled differently and is idiomatic in JUnit codebases. Use it when the project already uses it, not as a second convention alongside the first. Its example is in [jvm-testing.md](jvm-testing.md#junit-test-naming).

The two forms are alternatives, never a mix inside one codebase.

---

### Test structure

The three-phase shape and how its phases are labelled follow `coding-standards`, which holds the canonical rule. This
section adds the isolation that goes with it.

One behaviour per test. Several assertions are fine when they all verify that one behaviour, and each test builds its
own data so the order tests run in never matters. A second test that depends on the first fails, and a test that owns its setup passes. Both forms are in [jest.md](jest.md#test-isolation).

---

### Test comments

The three phases are marked with bare comments and nothing else: `// Given`, `// When`, `// Then`, or `// When & Then` when the action and the assertion are one call, with `#` in Python. They are the only comments a test file carries, because a comment is the part of a test nobody keeps true. A divider banner (`// ---- helpers ----`, `// ─── MODULE MOCKS ───`), a numbered section label (`// 7.1 Directory listing happy path`), a file header saying what the file tests and how its environment is chosen, and a trailing explanation after an assertion all go. What a test proves belongs in its name, or in the display name the framework offers where the name alone cannot carry it, such as `@DisplayName` in JUnit, and grouping belongs in a nested class or a separate file. The pass and fail form is in [jvm-testing.md](jvm-testing.md#test-comments-and-display-names).

The CI-guard pragmas a project defines, such as `// biome-ignore` or an `i18n-allow` marker, are tool input rather than prose and stay.

---

### Test file size

Past about 300 lines a test class is testing several behaviours, and a failure in it no longer points at one. Split it by behaviour into focused classes, for example `SubmissionServiceCreateTest`, `SubmissionServiceStatusTransitionTest` and `SubmissionServiceQueryTest`, and move the builders and canned data they share into one `<Subject>TestFixtures` class or module. A test class created only to push branch coverage up, typically named `*BranchTest`, is folded into the behaviour class whose branches it covers, because a branch is part of a behaviour. The same rule covers TypeScript and Python test files: `vendors.test.ts` becomes one file per behaviour area beside a shared fixtures module.

---

### Test what the user observes

Assert the behaviour the caller can see, not the internal state that produced it. A test coupled to internals fails on
every refactor and passes through real defects. The failing and passing assertion are in [jest.md](jest.md#test-what-the-user-observes).

Never weaken an assertion to make a test pass. Fix the code, or fix the setup that was wrong.

---

### Mocking boundaries

Mock only what you own, and only in unit tests. Do not mock the database when you can exercise it: integration tests run
against a real engine through Testcontainers, never a shared staging instance. For third-party HTTP clients, ORMs, and
cloud SDKs, prefer a real instance, the library's own official test double, or an HTTP-level fake such as WireMock or
MSW. The detail behind both rules is in [advanced-testing.md](advanced-testing.md).

A mock replaces an interface the project owns (its repository and its client wrapper), never the vendor SDK
underneath it, and it is not a substitute for exercising the real datastore. The seam is an interface the project defines, so the mock stays valid when the
vendor library changes underneath it. Two mocks at such a seam are in [jest.md](jest.md#mock-seams).

---

### Flaky tests

`e2e-testing` holds the canonical flaky-test policy: the fix-or-quarantine SLA, the maximum quarantine period, what
happens when it expires, the prohibited sleep patterns, and when a framework retry is allowed. It applies to every
layer, not only browser tests. Do not restate it here, and do not adopt a second policy alongside it.

---

### Continuous testing

Run the suite in watch mode while developing. Gate the commit on tests and lint. In CI, run with coverage and upload the report, through an upload action pinned to a full commit SHA with its tag in a trailing comment. The three commands, the workflow steps and the command that resolves the SHA are in [jest.md](jest.md#watch-commit-and-ci).
