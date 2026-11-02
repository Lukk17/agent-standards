---
name: e2e-testing
description: Playwright browser end-to-end testing, covering suite layout, the Page Object Model, configuration, semantic locators, the canonical flaky-test policy, artifacts and CI wiring. Use when the user says "write a Playwright test for the login flow", "our e2e suite is flaky" or "add e2e tests to CI". Not for backend capability sweeps against a live stack, use `e2e-runbooks`.
---

# E2E Testing Patterns

Build Playwright suites that stay stable, fast, and readable as the UI changes underneath them. This skill owns browser end-to-end testing and is the canonical home of the flaky-test policy that the other testing skills defer to.

| Task | Open |
| --- | --- |
| The suite tree, a full page object, the Pass and Fail code behind any rule below, provider stubs, and the checkout test | [references/patterns-and-examples.md](references/patterns-and-examples.md) |
| Write `playwright.config.ts`, decide the retry and artifact policy, wire the suite into CI | [references/config-and-ci.md](references/config-and-ci.md) |

---

### When to activate

- Writing or restructuring Playwright tests for a user journey through the browser.
- A browser suite is flaky, slow, or full of hardcoded waits, and needs a policy as well as a fix.
- Setting up `playwright.config.ts`, choosing projects and reporters, or wiring the suite into CI.
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

### Rules

1. Group specs under `tests/e2e/` by the journey they exercise (`auth/`, `features/`, `api/`), with fixtures in `tests/fixtures/` and page objects in `tests/pages/`, out of the spec tree, so a spec reads only as a scenario.
2. Put selectors and waiting behind a page object, so a markup change costs one edit rather than twenty. A page object exposes intent (`search`, `submitOrder`) and never leaks a raw selector into a spec.
3. Locate by role, label, or an explicit test id (`getByRole`, `getByLabel`, `getByTestId`). A locator tied to a generated class name or `nth-child` breaks on the next restyle and tells the reader nothing.
4. Create a `waitForResponse` promise, without `await`, before the action that triggers it, then await it. Awaited after the action, a fast response can arrive before the listener exists and the wait hangs until the timeout.
5. Assert web-first (`await expect(locator).toBeVisible()`, `toHaveCount`), which retries until the condition holds. `expect(await locator.isVisible())` and `expect(await locator.count())` read once and fail whenever the UI is a frame behind.
6. Prefer `locator.click()` over the discouraged `page.click(selector)`. Both wait for actionability, so a flaky click is usually a wrong locator or a missing web-first assertion, not a missing wait.
7. Stub a third-party provider (identity provider, payment widget, analytics beacon) at the browser boundary with `context.route`, or `context.addInitScript` before navigation for an injected global. It keeps the test hermetic and fast and is the only way to reach the failure paths.
8. A money-moving flow never runs against production (`test.skip` on it), asserts the confirmation state rather than the click, and waits on the settlement response rather than a timeout.

---

### Flaky tests, the canonical policy

A flaky test is a blocking defect, not background noise. It costs more than a failing test because it teaches the team to ignore red. This section is the project-wide policy: `tdd-workflow` and the language testing skills defer to it rather than restating it.

- Fix or quarantine within 2 business days of the first observed flake.
- Quarantine for at most 2 sprints. When it expires, delete the test and rewrite it from scratch.
- Quarantine explicitly with `test.fixme` and a linked tracking issue, so the test cannot quietly rot.
- Prohibited in assertions: `Thread.sleep()`, `time.sleep()`, `setTimeout`, `page.waitForTimeout`. A wall-clock wait is never the fix.
- Framework-level retry (`retries` in Playwright, `@RetryingTest` in JUnit) only for genuinely non-deterministic integration paths, never to paper over a race.
- Confirm a suspected flake with `npx playwright test <spec> --repeat-each=10` before spending time on it.

---

### Related skills

- `e2e-runbooks` covers the backend counterpart: one capability per spec, driven by an API client against a live stack.
- `tdd-workflow` owns the unit and integration layers below this one and defers its flaky policy here.
- `ai-regression-testing` covers DB-free API regression tests for AI-introduced defects.
- `web-accessibility` covers keyboard and screen-reader auditing, which a functional browser test does not prove.
- `deployment-patterns` covers where the suite runs in the pipeline and what a failure gates.

---

### Checklist

- [ ] Specs are grouped by journey, page objects live outside the spec tree.
- [ ] No raw selector appears in a spec file.
- [ ] Every locator is role, label, or test-id based.
- [ ] No `waitForTimeout` anywhere in the suite.
- [ ] Every `waitForResponse` promise is created before the action that triggers it.
- [ ] Assertions are web-first, never `expect(await locator.count())` or `expect(await locator.isVisible())`.
- [ ] Base URL and every environment value come from the environment.
- [ ] Trace, screenshot and video kept on failure, all under one artifact directory.
- [ ] Every quarantined test carries a tracking issue and a quarantine date.
- [ ] Third-party providers are stubbed at the browser boundary.
- [ ] Money-moving flows are skipped against production and assert the confirmed state.
- [ ] CI uploads the report on failure as well as success.
