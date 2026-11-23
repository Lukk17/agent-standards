# Pester 6

How the tests of a script or a module are written. Open this when adding Pester tests, or when a suite written for an older Pester fails. The rule it serves is in [SKILL.md](../SKILL.md), and the `Tests/` folder they live in is set out in [module-layout.md](module-layout.md).

---

### Structure, mocks and setup

Structure tests with `Describe` / `Context` / `It`, mock dependencies with `Mock` and verify with `Should -Invoke`,
and use `BeforeAll` / `AfterAll` for shared setup rather than repeating expensive work in `BeforeEach`. Pester 6
allows one of each setup and teardown block per `Describe` or `Context` and throws on a duplicate, and it removed
`Assert-MockCalled`, so `Should -Invoke` is the call-count check. Classic `Should -Be` keeps working, and the newer
`Should-*` assertions are optional.
