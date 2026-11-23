# Jest and npm Forms

Contents:

- [Cases from a journey](#cases-from-a-journey)
- [Running the RED and GREEN steps](#running-the-red-and-green-steps)
- [Coverage threshold](#coverage-threshold)
- [Test naming](#test-naming)
- [Test isolation](#test-isolation)
- [Test what the user observes](#test-what-the-user-observes)
- [Mock seams](#mock-seams)
- [Test data factory](#test-data-factory)
- [Watch, commit and CI](#watch-commit-and-ci)

The rules of this skill in the form a JavaScript or TypeScript project uses: Jest syntax, npm commands and the CI upload step. Open it when the project is JavaScript or TypeScript. The rule behind each section, with its reasoning, is in [loop-and-rules.md](loop-and-rules.md) or [advanced-testing.md](advanced-testing.md).

---

### Cases from a journey

Turn the journey into cases that name the behaviour and the condition.

```typescript
describe('catalogue search', () => {
  it('returns matching products for a keyword', async () => {})
  it('returns an empty list for a query that matches nothing', async () => {})
  it('falls back to substring matching when the search index is unavailable', async () => {})
  it('orders results by relevance score, highest first', async () => {})
})
```

---

### Running the RED and GREEN steps

Run the new test and see it fail before any production code changes.

```bash
npm test
```

Implement the minimum that turns it green, then rerun the same target.

```bash
npm test
```

---

### Coverage threshold

Fail: the config key is plural, so Jest ignores the whole block and the gate never fires.

```json
{
  "jest": {
    "coverageThresholds": {
      "global": { "branches": 70, "functions": 90, "lines": 90, "statements": 90 }
    }
  }
}
```

Pass: the key Jest actually reads.

```json
{
  "jest": {
    "coverageThreshold": {
      "global": { "branches": 70, "functions": 90, "lines": 90, "statements": 90 }
    }
  }
}
```

Verify locally before pushing.

```bash
npm run test:coverage
```

---

### Test naming

Fail: names that describe nothing.

```typescript
test('works', () => {})
test('test search 2', () => {})
test('happyPath', () => {})
```

Pass: natural-language form, the default.

```typescript
test('returns an empty list when no product matches the query', () => {})
test('throws when the API key is missing', () => {})
```

---

### Test isolation

Fail: the second test depends on the first.

```typescript
test('creates a user', () => { createUser('alice') })
test('updates the same user', () => { updateUser('alice', { name: 'Alicia' }) })
```

Pass: each test owns its setup.

```typescript
test('creates a user', () => {
  const user = createTestUser()
  expect(findUser(user.id)).toBeDefined()
})

test('updates a user', () => {
  const user = createTestUser()
  updateUser(user.id, { name: 'Alicia' })
  expect(findUser(user.id).name).toBe('Alicia')
})
```

---

### Test what the user observes

Fail:

```typescript
expect(component.state.count).toBe(5)
```

Pass:

```typescript
expect(screen.getByText('Count: 5')).toBeInTheDocument()
```

---

### Mock seams

The mocks below replace interfaces the project owns (its repository and its client wrapper), never the vendor SDK
underneath them, and they are not a substitute for exercising the real datastore.

A repository, mocked at the interface the application defines.

```typescript
jest.mock('@/lib/repositories/product-repository', () => ({
  productRepository: {
    findByKeyword: jest.fn(async () => [{ id: 1, name: 'Test Product' }]),
    findById: jest.fn(async () => ({ id: 1, name: 'Test Product' })),
  },
}))
```

An external HTTP client, mocked at the project's own wrapper rather than at the vendor SDK.

```typescript
jest.mock('@/lib/clients/search-client', () => ({
  searchClient: {
    query: jest.fn(async () => [{ id: 'test-product', score: 0.95 }]),
    health: jest.fn(async () => ({ reachable: true })),
  },
}))
```

Note what both examples have in common: the seam is an interface the project defines, so the mock stays valid when the
vendor library changes underneath it.

---

### Test data factory

The factory pattern from [advanced-testing.md](advanced-testing.md#test-data-factory) in TypeScript, with one function per named state.

```typescript
export const OrderFactory = {
  valid: (): Order => ({
    id: crypto.randomUUID(),
    customerId: 'cust-001',
    items: [{ sku: 'SKU-1', quantity: 2, price: 9.99 }],
    status: 'pending',
  }),
  cancelled: (): Order => ({ ...OrderFactory.valid(), status: 'cancelled' }),
}
```

---

### Watch, commit and CI

Run the suite in watch mode while developing.

```bash
npm test -- --watch
```

Gate the commit on tests and lint.

```bash
npm test && npm run lint
```

In CI, run with coverage and upload the report. The upload action is pinned to a full commit SHA with its tag in a
trailing comment, `<commit-sha>` standing in for a real one, resolved with
`git ls-remote https://github.com/codecov/codecov-action refs/tags/<tag> refs/tags/<tag>^{}`.

```yaml
- name: Run tests
  run: npm test -- --coverage
- name: Upload coverage
  uses: codecov/codecov-action@<commit-sha> # vX.Y.Z
```
