# Playwright patterns with examples

Open this for the suite tree, the page object, the Pass and Fail code, and the reasoning behind any rule in [SKILL.md](../SKILL.md). The flaky-test policy itself is stated once, in [SKILL.md](../SKILL.md), and this file carries its examples.

---

### Contents

- [Suite layout](#suite-layout)
- [Page Object Model](#page-object-model)
- [Locators](#locators)
- [Flaky tests, examples](#flaky-tests-examples)
- [External providers and third-party widgets](#external-providers-and-third-party-widgets)
- [Critical flows that move money](#critical-flows-that-move-money)

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
exposes intent (`search`, `submitOrder`) and never leaks a raw selector into a spec. Start waiting for a response
before the action that triggers it, and assert with web-first assertions such as `toHaveCount` and `toBeVisible`,
which retry until they pass, rather than `expect(await locator.count())`, which reads once and moves on.

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
    const response = this.page.waitForResponse(resp => resp.url().includes('/api/search'))
    await this.searchInput.fill(query)
    await response
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

    await expect(itemsPage.itemCards).not.toHaveCount(0)
    await expect(itemsPage.itemCards.first()).toContainText(/test/i)
  })

  test('shows the empty state when nothing matches', async ({ page }) => {
    await itemsPage.search('xyznonexistent123')

    await expect(page.getByTestId('no-results')).toBeVisible()
    await expect(itemsPage.itemCards).toHaveCount(0)
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

### Flaky tests, examples

The policy, its SLA and its quarantine limits are in [SKILL.md](../SKILL.md) under "Flaky tests, the canonical policy". These are its examples.

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

The two causes worth knowing.

A response the test needs, awaited after the action that triggers it. A fast response can arrive before the listener
exists, and the wait then hangs until the timeout. Create the promise first, without `await`, then act, then await it.

Fail:

```typescript
await page.getByRole('button', { name: 'Load more' }).click()
await page.waitForResponse(resp => resp.url().includes('/api/data') && resp.ok())
```

Pass:

```typescript
const response = page.waitForResponse(resp => resp.url().includes('/api/data') && resp.ok())
await page.getByRole('button', { name: 'Load more' }).click()
await response
```

An assertion that does not retry. `expect(await locator.isVisible())` and `expect(await locator.count())` read the
page once, so they fail whenever the UI is a frame behind. A web-first assertion waits and retries until the condition
holds or the timeout expires. A wall-clock wait such as `page.waitForTimeout(5000)` is never the fix.

Fail:

```typescript
expect(await page.getByTestId('menu-item').isVisible()).toBe(true)
```

Pass:

```typescript
await expect(page.getByTestId('menu-item')).toBeVisible()
```

Prefer `locator.click()` over `page.click(selector)`, which Playwright discourages. Both wait for the element to be
actionable, so a flaky click is usually a wrong locator or a missing web-first assertion, not a missing wait.

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

  const order = page.waitForResponse(
    resp => resp.url().includes('/api/orders') && resp.status() === 201,
    { timeout: 30000 },
  )
  await page.getByRole('button', { name: 'Place order' }).click()
  await order

  await expect(page.getByTestId('order-confirmation')).toBeVisible()
})
```
