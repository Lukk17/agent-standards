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
  retries: 0,
  workers: process.env.CI ? 1 : undefined,
  outputDir: 'artifacts/test-results',
  reporter: [
    ['html', { outputFolder: 'artifacts/playwright-report' }],
    ['junit', { outputFile: 'artifacts/playwright-results.xml' }],
    ['json', { outputFile: 'artifacts/playwright-results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'retain-on-failure',
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
suite to one test. `retries: 0` keeps every flake visible, because the flaky policy in [SKILL.md](../SKILL.md) allows a
retry only on a genuinely non-deterministic integration path, and that spec opts in on its own. `workers: 1` under CI
trades wall-clock for determinism, and is worth relaxing once the suite is genuinely isolated.

```typescript
test.describe.configure({ retries: 2 })
```

That line sits at the top of the one spec file that drives the non-deterministic path, never in the global config.

---

### Artifacts

Let the config capture failures rather than sprinkling manual captures through specs. Screenshots, video, traces, and
the reports all belong under one artifact directory, `artifacts/`, that CI uploads as a whole. `outputDir` is where
Playwright writes screenshots, video, and traces, and Playwright cleans it at the start of every run.

A deliberate screenshot inside a spec is for documenting a state, not for diagnosing a failure. Write it through
`testInfo.outputPath`, which puts it inside `outputDir` in a folder of its own for that test.

```typescript
await page.screenshot({ path: test.info().outputPath('checkout-summary.png'), fullPage: true })
```

Traces are the highest-value artifact for a failure that only reproduces in CI, because they replay the run with DOM
snapshots, network activity, and the console. `trace: 'retain-on-failure'` is the right default with no global retry: it
records every run and keeps the trace only for a run that failed, even when a later retry passes.

---

### CI wiring

Run the suite on every push and pull request, and always upload the artifact directory, so a red build is diagnosable
without a local reproduction.

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
          name: playwright-artifacts
          path: artifacts/
          retention-days: 30
```

`if: always()` on the upload step is the part people forget. Without it the report is uploaded only when the suite
passes, which is exactly when nobody needs it.

Pin the Node version to the current LTS rather than `latest`, so a runner image update cannot change the runtime under
the suite without a commit.
