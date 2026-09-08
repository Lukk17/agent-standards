---
name: e2e-testing
description: Playwright browser end-to-end testing, covering suite layout, the Page Object Model, configuration, semantic locators, the canonical flaky-test policy, artifacts, and CI wiring. Use when you say "write a Playwright test for the login flow", "our e2e suite is flaky", "set up playwright.config.ts", "add e2e tests to CI", or "test the checkout journey in a browser". Not for backend capability sweeps against a live stack, use `e2e-runbooks`.
---

# E2E Testing Patterns

Build Playwright suites that stay stable, fast, and readable as the UI changes underneath them. This skill owns browser
end-to-end testing and is the canonical home of the flaky-test policy that the other testing skills defer to.

---

### When to activate

- Writing or restructuring Playwright tests for a user journey through the browser.
- A browser suite is flaky, slow, or full of hardcoded waits, and needs a policy as well as a fix.
- Setting up `playwright.config.ts`, choosing projects and reporters, or wiring the suite into CI.
- Deciding how a UI test should locate elements, or where its page objects live.
- Another testing skill has deferred a flaky-test decision to this one.

---

### When not to activate

- Verifying a deployed backend capability with an API client rather than a browser. Use `e2e-runbooks`.
- Unit and integration tests inside the codebase, and the red-green-refactor loop. Use `tdd-workflow`, or the language
  testing skill (`python-testing`, `golang-testing`, `springboot-tdd`).
- Sandbox-mode API regression tests that need no browser and no database. Use `ai-regression-testing`.
- Auditing a page for keyboard operability and screen-reader behaviour. Use `web-accessibility`.
- Load, soak, or chaos testing. Out of scope here, which is about correctness rather than capacity.

---

### Suite layout

Group specs by the journey they exercise, keep fixtures separate from specs, and keep page objects out of the spec tree
so a spec file only reads as a scenario.

```text
tests/
├── e2e/
│   ├── auth/
│   │   ├── login.spec.ts
│   │   ├── logout.spec.ts
│   │   └── register.spec.ts
│   ├── features/
│   │   ├── browse.spec.ts
│   │   ├── search.spec.ts
│   │   └── checkout.spec.ts
│   └── api/
│       └── endpoints.spec.ts
├── fixtures/
│   ├── auth.ts
│   └── data.ts
├── pages/
│   └── ItemsPage.ts
└── playwright.config.ts
```

---

### Page Object Model

Put selectors and waiting behind a page object so a markup change costs one edit rather than twenty. A page object
exposes intent (`search`, `submitOrder`) and never leaks a raw selector into a spec.

Fail: the spec owns the selectors and the waits.

```typescript
test('search', async ({ page }) => {
  await page.goto('/items')
  await page.locator('[data-testid="search-input"]').fill('test')
  await page.waitForTimeout(500)
  expect(await page.locator('[data-testid="item-card"]').count()).toBeGreaterThan(0)
})
```

Pass: the page object owns them, and the spec reads as the journey.

```typescript
export class ItemsPage {
  readonly page: Page
  readonly searchInput: Locator
  readonly itemCards: Locator

  constructor(page: Page) {
    this.page = page
    this.searchInput = page.getByTestId('search-input')
    this.itemCards = page.getByTestId('item-card')
  }

  async goto() {
    await this.page.goto('/items')
  }

  async search(query: string) {
    await this.searchInput.fill(query)
    await this.page.waitForResponse(resp => resp.url().includes('/api/search'))
  }

  async itemCount() {
    return this.itemCards.count()
  }
}
```

```typescript
test.describe('Item search', () => {
  let itemsPage: ItemsPage

  test.beforeEach(async ({ page }) => {
    itemsPage = new ItemsPage(page)
    await itemsPage.goto()
  })

  test('finds items by keyword', async () => {
    await itemsPage.search('test')

    expect(await itemsPage.itemCount()).toBeGreaterThan(0)
    await expect(itemsPage.itemCards.first()).toContainText(/test/i)
  })

  test('shows the empty state when nothing matches', async ({ page }) => {
    await itemsPage.search('xyznonexistent123')

    await expect(page.getByTestId('no-results')).toBeVisible()
    expect(await itemsPage.itemCount()).toBe(0)
  })
})
```

---

### Locators

Locate by role, label, or an explicit test id. A locator tied to a generated class name breaks on the next styling
change and tells the reader nothing.

Fail: brittle and meaningless.

```typescript
await page.click('.css-1x7hj2k > div:nth-child(3) button')
```

Pass: semantic, and stable across restyling.

```typescript
await page.getByRole('button', { name: 'Submit order' }).click()
await page.getByTestId('submit-order').click()
```


---

### Flaky tests, the canonical policy

A flaky test is a blocking defect, not background noise. It costs more than a failing test because it teaches the team
to ignore red. This section is the project-wide policy: `tdd-workflow` and the language testing skills defer to it
rather than restating it.

| Rule | Value |
| --- | --- |
| Fix or quarantine SLA | 2 business days from the first observed flake |
| Maximum quarantine period | 2 sprints |
| Action when quarantine expires | Delete the test and rewrite it from scratch |
| Prohibited in assertions | `Thread.sleep()`, `time.sleep()`, `setTimeout`, `page.waitForTimeout` |
| Allowed retry | Framework-level retry (`retries` in Playwright, `@RetryingTest` in JUnit) only for genuinely non-deterministic integration paths, never to paper over a race |

Quarantine explicitly and link the tracking issue, so the test cannot quietly rot.

```typescript
test('complex search', async ({ page }) => {
  test.fixme(true, 'Flaky, tracked in issue #123')
})
```

Confirm a suspected flake before spending time on it.

```bash
npx playwright test tests/search.spec.ts --repeat-each=10
```

The three causes worth knowing. Race conditions: assert through an auto-waiting locator rather than a bare click on a
possibly unmounted element.

Fail:

```typescript
await page.click('[data-testid="submit"]')
```

Pass:

```typescript
await page.getByTestId('submit').click()
```

Network timing: wait for the response the UI depends on, never for a wall-clock guess.

Fail:

```typescript
await page.waitForTimeout(5000)
```

Pass:

```typescript
await page.waitForResponse(resp => resp.url().includes('/api/data') && resp.ok())
```

Animation timing: wait for the element to be stable before interacting with it.

Fail:

```typescript
await page.click('[data-testid="menu-item"]')
```

Pass:

```typescript
const item = page.getByTestId('menu-item')
await item.waitFor({ state: 'visible' })
await item.click()
```


---

### External providers and third-party widgets

A journey that depends on a third-party provider (an identity provider, a payment widget, an analytics beacon) should
stub the provider at the browser boundary. Stubbing keeps the test hermetic and fast, and it is the only way to make the
failure paths reachable.

Fail: the test drives the real provider, so it is slow, rate limited, and untestable for the declined case.

```typescript
test('user signs in', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill(process.env.REAL_TEST_ACCOUNT!)
  await page.getByRole('button', { name: 'Continue with provider' }).click()
})
```

Pass: the provider is stubbed, the app under test is real, and both outcomes are reachable.

```typescript
test('user signs in with the external provider', async ({ page, context }) => {
  await context.route('**/oauth/token', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: 'test-token', expires_in: 3600 }),
    }),
  )

  await page.goto('/login')
  await page.getByRole('button', { name: 'Continue with provider' }).click()

  await expect(page.getByTestId('user-menu')).toContainText('Signed in')
})
```

The same shape covers any browser-injected global a widget provides: install the stub with `context.addInitScript`
before navigation, then assert on what the application does with it.

---

### Critical flows that move money

A checkout, a payment, or anything that debits a real account gets three extra rules: it never runs against production,
it asserts the confirmation state rather than the click, and it waits on the settlement response rather than a timeout.

```typescript
test('user completes checkout', async ({ page }) => {
  test.skip(process.env.NODE_ENV === 'production', 'Never charge a real account from a test')

  await page.goto('/cart')
  await page.getByTestId('quantity').fill('2')
  await page.getByRole('button', { name: 'Go to checkout' }).click()

  await expect(page.getByTestId('order-total')).toContainText('49.98')

  await page.getByRole('button', { name: 'Place order' }).click()
  await page.waitForResponse(
    resp => resp.url().includes('/api/orders') && resp.status() === 201,
    { timeout: 30000 },
  )

  await expect(page.getByTestId('order-confirmation')).toBeVisible()
})
```

---

### Reference map

| Task | Open |
| --- | --- |
| Write `playwright.config.ts`, decide the retry and artifact policy, wire the suite into CI | [references/config-and-ci.md](references/config-and-ci.md) |

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
- [ ] Base URL and every environment value come from the environment.
- [ ] Trace on first retry, screenshot and video on failure, all under one artifact directory.
- [ ] Every quarantined test carries a tracking issue and a quarantine date.
- [ ] Third-party providers are stubbed at the browser boundary.
- [ ] Money-moving flows are skipped against production and assert the confirmed state.
- [ ] CI uploads the report on failure as well as success.
