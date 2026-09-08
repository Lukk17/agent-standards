---
name: ai-regression-testing
description: "Regression testing for the blind spots of AI-assisted development: bug-driven test selection, response-contract assertions, sandbox and production path parity, and a mechanical check step before any AI review. Use when you say \"an agent changed my API routes\", \"write a regression test for this bug\", \"the same bug keeps coming back\", \"test this without a database\", or \"the sandbox path drifted from production\". Not for the red-green-refactor loop and the coverage gate, use `tdd-workflow`."
---

# AI Regression Testing

When the same model writes code and then reviews it, it carries the same assumptions into both steps, so a whole class
of defect survives review and only a mechanical test catches it. This skill covers the test selection and assertion
shapes that target that class. `coding-standards` is the baseline and `tdd-workflow` owns the core discipline this sits
on top of.

The code examples assume Next.js App Router route handlers tested with Vitest, because that stack shows the sandbox and
production split most plainly. Every pattern here is about the shape of the assertion rather than the framework: on
another stack, translate the harness and keep the assertion. The equivalents are a Django or FastAPI test client,
`MockMvc` or `@SpringBootTest` in Spring Boot, and `httptest` in Go.

---

### When to activate

- An AI agent has modified API routes, serialisers, or backend logic and the change needs a mechanical check.
- A bug was just found and fixed, and it must not come back.
- The project has a sandbox or mock mode that lets an API be tested without a database.
- The same defect has appeared more than once in the same area.
- Multiple code paths exist for one behaviour: sandbox against production, or a feature flag with two branches.

---

### When not to activate

- The red-green-refactor loop, the test pyramid, and the coverage gate. Use `tdd-workflow`.
- Browser journeys through the UI. Use `e2e-testing`.
- Verifying a deployed capability against a live stack with an API client. Use `e2e-runbooks`.
- Language-level test mechanics: fixtures, parametrisation, table-driven tests. Use `python-testing`, `golang-testing`,
  or `springboot-tdd`.
- Reviewing the change by reading it. Use `code-reviewer`, and treat this skill as the step that runs before that
  review.

---

### The failure this skill targets

An AI writes a fix, reviews its own fix, declares it correct, and the bug is still there. The review inherits the
assumption that caused the bug, so it cannot see it. A representative sequence, all four steps observed on one field:

```text
Fix 1: added notification_settings to the API response, but not to the query projection.
       Self-review passed. Field was still undefined.
Fix 2: added it to the projection. Build failed on a type that did not know the column.
       Self-review looked at fix 1 only.
Fix 3: widened the projection. Fixed the production path, left the sandbox path behind.
       Self-review missed it a fourth time.
Fix 4: a test asserting the field is present failed on the first run and located it immediately.
```

Path inconsistency between a sandbox branch and a production branch is the single most common AI-introduced regression.
A test asserting the response contract catches it in milliseconds and never gets bored.

---

### Run the mechanical checks before the AI review

The order matters. A test suite and a type check find defects without judgement, so they run first and their output is
what the review starts from. An AI review that runs first anchors on its own reading and then rationalises the failures.

Fail: review first, tests as a formality afterwards.

```text
1. Read the diff and report findings.
2. Run the tests if time permits.
```

Pass: the mechanical gate is step one and blocks the rest.

```text
1. Run the test suite. Any failure is the highest-priority finding; stop and report it.
2. Run the type check or build. Any error is the next-highest finding; stop and report it.
3. Only once both are green, review by reading, with the known blind spots in mind:
   sandbox and production path parity, response shape against what the caller expects,
   query projection completeness, error handling with rollback, optimistic update races.
4. For every defect fixed, add a regression test before closing it out.
```

Wire those steps into whatever the project uses for repeatable prompts, and name the verification command the way the
project's own AGENTS.md names it rather than assuming `npm run test`.

---

### Assert the response contract, not the implementation

Declare the fields a response must carry, then assert the whole list on every relevant test. A contract list is one line
to extend when a field is added, and it fails loudly when a field silently disappears.

Fail: asserts one field the author happened to think of.

```typescript
it("returns a profile", async () => {
  const res = await GET(createTestRequest("/api/user/profile"))
  const { json } = await parseResponse(res)
  expect(json.data.email).toBeDefined()
})
```

Pass: asserts the declared contract, and names the regression it prevents.

```typescript
const REQUIRED_FIELDS = [
  "id",
  "email",
  "full_name",
  "phone",
  "role",
  "created_at",
  "avatar_url",
  "notification_settings",
]

it("returns every field in the profile contract", async () => {
  const res = await GET(createTestRequest("/api/user/profile"))
  const { status, json } = await parseResponse(res)

  expect(status).toBe(200)
  for (const field of REQUIRED_FIELDS) {
    expect(json.data).toHaveProperty(field)
  }
})

it("keeps notification_settings present and typed (BUG-R1 regression)", async () => {
  const res = await GET(createTestRequest("/api/user/profile"))
  const { json } = await parseResponse(res)

  expect("notification_settings" in json.data).toBe(true)
  const settings = json.data.notification_settings
  expect(settings === null || typeof settings === "object").toBe(true)
})
```

`toHaveProperty` is the right assertion here rather than a truthiness check, because a field present with a `null` value
passes the contract while a missing field does not.

---

### Test sandbox and production parity

Where a handler branches on a sandbox flag, both branches owe the same response shape. Assert it directly instead of
hoping the two branches stay in step.

Fail: the new field reaches one branch only.

```typescript
if (isSandboxMode()) {
  return { data: { id, email, name } }
}
return { data: { id, email, name, notificationSettings } }
```

Pass: both branches satisfy the same contract, with the sandbox branch returning an explicit empty value.

```typescript
if (isSandboxMode()) {
  return { data: { id, email, name, notificationSettings: null } }
}
return { data: { id, email, name, notificationSettings } }
```

The test that enforces it runs against the sandbox branch, since the test environment forces the flag on.

```typescript
it("returns the same fields in sandbox mode", async () => {
  const res = await GET(createTestRequest("/api/user/profile"))
  const { json } = await parseResponse(res)

  for (const field of REQUIRED_FIELDS) {
    expect(json.data).toHaveProperty(field)
  }
})
```

---

### Watch the four recurring patterns

Projection omission. A field is added to the response mapping but not to the query that loads it, so it is always
undefined. The same trap exists in every data layer: a column list in SQL, a `select` in a query builder, a projection
interface in JPA, a serialiser field list.

Fail:

```typescript
const user = await userRepository.findById(id, { select: ["id", "email", "name"] })
return { data: { ...user, notificationSettings: user.notificationSettings } }
```

Pass:

```typescript
const user = await userRepository.findById(id, {
  select: ["id", "email", "name", "notificationSettings"],
})
return { data: user }
```

Error state leakage. An error is caught and surfaced, but the stale data it replaced is left on screen.

Fail:

```typescript
catch (err) {
  setError("Failed to load")
}
```

Pass:

```typescript
catch (err) {
  logger.error({ err }, "Failed to load reservations")
  setReservations([])
  setError("Failed to load")
}
```

Optimistic update without rollback. The UI is updated before the request succeeds and never reverts when it does not.

Fail:

```typescript
const remove = async (id: string) => {
  setItems(prev => prev.filter(item => item.id !== id))
  await fetch(`/api/items/${id}`, { method: "DELETE" })
}
```

Pass:

```typescript
const remove = async (id: string) => {
  const previous = items
  setItems(prev => prev.filter(item => item.id !== id))
  try {
    const res = await fetch(`/api/items/${id}`, { method: "DELETE" })
    if (!res.ok) {
      throw new Error(`Delete failed with ${res.status}`)
    }
  } catch (err) {
    logger.error({ err }, "Failed to remove item, rolling back")
    setItems(previous)
    setError("Could not delete the item")
  }
}
```

Type cast masking a null. A cast tells the compiler a value exists without making it exist, so the failure moves from
build time to run time. Assert the field is not undefined rather than trusting the type.

| Pattern | Test strategy | Priority |
| --- | --- | --- |
| Sandbox and production mismatch | Assert the full contract in sandbox mode | High |
| Projection omission | Assert every required field is present in the response | High |
| Error state leakage | Assert stale state is cleared on the error path | Medium |
| Missing rollback | Assert state is restored after a failed request | Medium |
| Type cast masking a null | Assert the field is not undefined | Medium |

---

### Choose the next test by where bugs were found

Coverage percentage says how much of the code a test touched. It does not say whether the test would have caught the
defect that shipped. This skill decides which test to write next. It does not lower the bar for how much is covered.

The gate is unchanged and lives in `tdd-workflow`: around 90 percent line coverage of real logic, branch coverage at 70
to 80 percent, enforced in CI. The goal of the tests written under this skill is regression prevention, and following
the bug trail is how you reach the gate with tests that are worth having rather than tests that exist to move a number.

Fail: filling coverage where nothing has ever broken.

```text
Wrote 14 tests for the notifications helper to lift the module from 61% to 92%.
No defect has ever been reported there.
```

Pass: the bug trail drives the order, and the gate is still met.

```text
Bug in /api/user/profile      -> contract test for the profile response.
Bug in /api/user/messages     -> contract test for the conversation list.
Bug in /api/user/favorites    -> contract test for the favorites response.
Remaining gap to the 90% line gate closed on the modules the coverage report names,
starting with the ones adjacent to the three bugs above.
```

This works because an AI repeats a category of mistake rather than making random ones, bugs cluster in the complex areas
(auth, multi-path logic, state management), and each regression test permanently closes the exact hole it was written
for.

---

### Reference map

| Task | Open |
| --- | --- |
| Wire up the Vitest and Next.js harness: config, sandbox setup file, request helper | [references/vitest-nextjs-harness.md](references/vitest-nextjs-harness.md) |

---

### Related skills

- `tdd-workflow` owns the red-green-refactor loop, the test pyramid, and the coverage gate this skill defers to.
- `e2e-testing` owns browser journeys and the canonical flaky-test policy.
- `e2e-runbooks` owns capability sweeps against a deployed stack.
- `code-reviewer` is the review pass that runs after the mechanical checks in this skill are green.
- `coding-standards` holds the error-handling and state conventions the failure patterns above violate.

---

### Checklist

- [ ] The test suite and the type check ran before any review by reading.
- [ ] Every fixed defect gained a regression test named after the bug it prevents.
- [ ] Response contracts are asserted as a declared field list, not one field at a time.
- [ ] Both sides of every sandbox or feature-flag branch satisfy the same contract.
- [ ] Query projections were checked whenever a response field was added.
- [ ] Error paths clear the state they invalidate.
- [ ] Optimistic updates capture the previous state and restore it on failure.
- [ ] Test selection follows the bug trail, and the `tdd-workflow` coverage gate is still met.
