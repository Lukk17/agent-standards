# Scope

Companion reference for the [e2e-testing](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

The skill covers Playwright browser end-to-end testing: suite layout, the Page Object Model, configuration, semantic locators, the canonical flaky-test policy, artifacts and CI wiring. It applies when:

- Writing or restructuring Playwright tests for a user journey through the browser, as in "write a Playwright test for the login flow".
- A browser suite is flaky, slow, or full of hardcoded waits, and needs a policy as well as a fix, as in "our e2e suite is flaky".
- Setting up `playwright.config.ts`, choosing projects and reporters, or wiring the suite into CI, as in "add e2e tests to CI" when those tests drive a browser.
- Testing a checkout or another money-moving journey in a browser.
- Deciding how a UI test should locate elements, or where its page objects live.
- Another testing skill has deferred a flaky-test decision to this one.

---

### When not to activate

- Verifying a deployed backend capability with an API client rather than a browser. Use `e2e-runbooks`.
- Unit and integration tests inside the codebase, and the red-green-refactor loop. Use `tdd-workflow`, or the language testing skill (`python-patterns`, `golang-patterns`, `springboot-patterns`).
- Sandbox-mode API regression tests that need no browser and no database. Use `ai-regression-testing`.
- Auditing a page for keyboard operability and screen-reader behaviour. Use `web-accessibility`.
- Load, soak, or chaos testing. Out of scope here, which is about correctness rather than capacity.

---

### Related skills

- `e2e-runbooks` covers the backend counterpart: one capability per spec, driven by an API client against a live stack.
- `tdd-workflow` owns the unit and integration layers below this one and defers its flaky policy here.
- `ai-regression-testing` covers DB-free API regression tests for AI-introduced defects.
- `web-accessibility` covers keyboard and screen-reader auditing, which a functional browser test does not prove.
- `deployment-patterns` covers where the suite runs in the pipeline and what a failure gates.
