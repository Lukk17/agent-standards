---
name: e2e-testing
description: 'Playwright browser tests: page objects, locators and the flaky-test policy. Use when the user says "write a Playwright test for the login flow" or "our browser suite is flaky". Not for API checks, use `e2e-runbooks`.'
metadata:
  version: "1.1.0"
---

# E2E Testing Patterns

Build Playwright suites that stay stable, fast, and readable as the UI changes underneath them. This skill owns browser end-to-end testing and is the canonical home of the flaky-test policy that the other testing skills defer to.

| Task | Open |
| --- | --- |
| The suite tree, a full page object, the Pass and Fail code behind any rule below, provider stubs, the checkout test | [patterns-and-examples.md](references/patterns-and-examples.md) |
| Write `playwright.config.ts`, decide the retry and artifact policy, wire the suite into CI | [config-and-ci.md](references/config-and-ci.md) |
| Before calling a suite or a spec done | [checklist.md](references/checklist.md) |

---

### When not to activate

- Verifying a deployed backend capability with an API client rather than a browser, use `e2e-runbooks`.
- Unit and integration tests inside the codebase, and the red-green-refactor loop, use `tdd-workflow`.
- Auditing a page for keyboard operability and screen-reader behaviour, use `web-accessibility`.

---

### Rules

1. Group specs under `tests/e2e/` by the journey they exercise (`auth/`, `features/`, `api/`), with fixtures in `tests/fixtures/` and page objects in `tests/pages/`, out of the spec tree, so a spec reads only as a scenario.
2. Put selectors and waiting behind a page object. It exposes intent (`search`, `submitOrder`) and never leaks a raw selector into a spec.
3. Locate by role, label, or an explicit test id (`getByRole`, `getByLabel`, `getByTestId`), never by a generated class name or `nth-child`, which breaks on the next restyle.
4. Create a `waitForResponse` promise, without `await`, before the action that triggers it, then await it. Awaited after the action, a fast response can arrive before the listener exists.
5. Assert web-first (`await expect(locator).toBeVisible()`, `toHaveCount`), which retries until the condition holds. `expect(await locator.isVisible())` and `expect(await locator.count())` read once and fail whenever the UI is a frame behind.
6. Prefer `locator.click()` over the discouraged `page.click(selector)`. Both wait for actionability, so a flaky click is usually a wrong locator or a missing web-first assertion, not a missing wait.
7. Stub a third-party provider (identity provider, payment widget, analytics beacon) at the browser boundary with `context.route`, or `context.addInitScript` before navigation for an injected global, so the failure paths are reachable.
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
