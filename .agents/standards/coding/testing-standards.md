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
