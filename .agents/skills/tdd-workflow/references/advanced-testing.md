# Advanced testing standards

Depth behind [SKILL.md](../SKILL.md): the pyramid proportions, the test data factory pattern, contract and mutation
testing, performance gates, and the two rules that decide what may be mocked. The configuration and code for one stack
is in [jvm-testing.md](jvm-testing.md), [jest.md](jest.md) and [k6.md](k6.md).

---

### Test pyramid

Proportions to hold across the whole suite. A suite shaped like an inverted pyramid is slow, flaky, and expensive to
keep green.

| Layer | Target share | Tools |
| --- | --- | --- |
| Unit | around 70 percent | JUnit, Vitest, pytest, `go test`. Fast, no input or output |
| Integration | around 20 percent | Testcontainers against a real database, queue, or cache |
| Contract | around 5 percent | Pact, Spring Cloud Contract |
| End to end | around 5 percent | Playwright, covered by the `e2e-testing` skill |

---

### Test data factory

Object construction repeated inline across tests is duplication with a long tail: every schema change becomes a sweep
through the test suite. Extract construction into a factory that exposes named states.

Each named state describes a domain condition, so a test reads as `given a cancelled order` rather than as fifteen lines
of builder calls. The factory in Java is in [jvm-testing.md](jvm-testing.md#test-data-factory) and in TypeScript in [jest.md](jest.md#test-data-factory).

---

### Contract testing

Every internal HTTP API whose consumers you can name needs consumer-driven contract tests, because a green suite on
both sides still lets a provider break a consumer it never runs against. A public API, whose consumers cannot be
individually identified, uses a schema-diff gate on its OpenAPI description instead, since a consumer-driven contract
needs a known consumer to write it.

Use Pact in polyglot estates and Spring Cloud Contract for JVM-to-JVM service pairs. The contract lives with the
consumer and is verified in the provider's pipeline, which is what makes it a gate rather than documentation. A Spring Cloud Contract example is in [jvm-testing.md](jvm-testing.md#contract-testing-with-spring-cloud-contract).

---

### Mutation testing

Line coverage says a line ran. Mutation testing says the test would have noticed if that line were wrong. Run it on
critical business logic and gate CI at a minimum score of 70 percent.

PIT covers the JVM, Stryker covers TypeScript and JavaScript, `mutmut` and `cosmic-ray` cover Python. Scope it to the
modules that hold business rules. Running it over the whole repository is slow enough that teams switch it off. The PIT configuration is in [jvm-testing.md](jvm-testing.md#mutation-testing-with-pit).

---

### Performance gates

Required before a major release and for any change to a hot path. Assert thresholds inside the load test so a regression
fails the run rather than needing someone to read a chart. The k6 form is in [k6.md](k6.md).

k6 and Gatling cover HTTP services, `pytest-benchmark` covers Python hot paths, and JMH covers JVM micro-benchmarks.
Alert on a p99 regression above 20 percent against the previous release baseline. The measurement discipline itself
lives in the `performance-optimization` skill.

---

### Do not mock what you do not own

Mock only types the project defines. A mock of a third-party client encodes your belief about that client's behaviour,
and the belief is what breaks on upgrade, silently, with the test still green.

For an external dependency, in order of preference: a real instance through Testcontainers, the library's own official
test double, or a fake at the wire protocol (WireMock, MSW) so the real client code still runs.

---

### Testcontainers mandate

Every integration test that touches a database, message queue, cache, or cloud service runs it as a container the test
owns, with the image pinned to a version tag and its digest. The Java and Spring Boot form, with the pin and the
connection details, is in [jvm-testing.md](jvm-testing.md#testcontainers).

Never point automated tests at a shared staging database. Tests must be hermetic and reproducible, and a shared instance
makes them neither: results depend on whoever else was running at the time.

---

### Run the whole suite

Verify a fix against the full suite, never against the single test that was failing. A change that turns one test green
while breaking another is not a fix, and running one test in isolation is how that ships.
