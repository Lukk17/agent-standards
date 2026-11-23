# E2E Testing Checklist

Run it before calling a suite or a spec done.

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
