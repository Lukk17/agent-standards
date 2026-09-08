# Playwright configuration, artifacts, and CI

The mechanical setup behind [SKILL.md](../SKILL.md): the one config file the whole suite reads, what it captures on
failure, and how the suite runs in a pipeline.

---

### One config for the whole suite

The config owns the base URL, the retry policy, the artifact policy, the browser matrix, and how the app under test is
started. Read every environment-specific value from the environment: a hardcoded host is what stops the same suite from
running against a preview deployment.

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'playwright-results.xml' }],
    ['json', { outputFile: 'playwright-results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
```

Three settings carry most of the weight. `forbidOnly` under CI stops a stray `test.only` from silently reducing the
suite to one test. `retries: 2` under CI and `0` locally means a flake is visible where it can be fixed and survivable
where it blocks a deploy. `workers: 1` under CI trades wall-clock for determinism, and is worth relaxing once the suite
is genuinely isolated.

---

### Artifacts

Let the config capture failures rather than sprinkling manual captures through specs. Screenshots, video, and traces all
belong under one artifact directory that CI uploads as a whole.

A deliberate screenshot inside a spec is for documenting a state, not for diagnosing a failure.

```typescript
await page.screenshot({ path: 'artifacts/checkout-summary.png', fullPage: true })
```

Traces are the highest-value artifact for a failure that only reproduces in CI, because they replay the run with DOM
snapshots, network activity, and the console. `trace: 'on-first-retry'` is the right default: no cost on green runs, a
full trace on the run that actually failed.

---

### CI wiring

Run the suite on every push and pull request, and always upload the report, so a red build is diagnosable without a
local reproduction.

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-node@v5
        with:
          node-version: 24
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test
        env:
          BASE_URL: ${{ vars.STAGING_URL }}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30
```

`if: always()` on the upload step is the part people forget. Without it the report is uploaded only when the suite
passes, which is exactly when nobody needs it.

Pin the Node version to the current LTS rather than `latest`, so a runner image update cannot change the runtime under
the suite without a commit.
