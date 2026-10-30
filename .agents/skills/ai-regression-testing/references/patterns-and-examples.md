# Patterns and Examples

Contents:

- [The failure this skill targets](#the-failure-this-skill-targets)
- [Run the mechanical checks before the AI review](#run-the-mechanical-checks-before-the-ai-review)
- [Assert the response contract, not the implementation](#assert-the-response-contract-not-the-implementation)
- [Test sandbox and production parity](#test-sandbox-and-production-parity)
- [Watch the four recurring patterns](#watch-the-four-recurring-patterns)
- [Choose the next test by where bugs were found](#choose-the-next-test-by-where-bugs-were-found)

Every rule in SKILL.md in full, with its reasoning and its pass and fail forms. The code examples assume Next.js App Router route handlers tested with Vitest, because that stack shows the sandbox and production split most plainly. Every pattern here is about the shape of the assertion rather than the framework: on another stack, translate the harness and keep the assertion. The equivalents are a Django or FastAPI test client, `MockMvc` or `@SpringBootTest` in Spring Boot, and `httptest` in Go. Load this file when applying a rule and the one-line summary in SKILL.md is not enough.

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

Path inconsistency between a sandbox branch and a production branch is a common AI-introduced regression, and the one
this skill is built around.
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
  return { data: { id, email, full_name, phone, role, created_at, avatar_url } }
}
return { data: { id, email, full_name, phone, role, created_at, avatar_url, notification_settings } }
```

Pass: both branches satisfy the same contract, with the sandbox branch returning an explicit empty value.

```typescript
if (isSandboxMode()) {
  return { data: { id, email, full_name, phone, role, created_at, avatar_url, notification_settings: null } }
}
return { data: { id, email, full_name, phone, role, created_at, avatar_url, notification_settings } }
```

The sandbox branch must be unreachable in production. Refuse to start when the sandbox flag is set together with
`NODE_ENV=production`, never read identity from a request header outside the sandbox, and prefer injecting a fake
repository over branching inside the handler. A branch left reachable is debug code shipped enabled (CWE-489), and a
sandbox identity header in production lets any caller choose any user.

```typescript
if (process.env.SANDBOX_MODE === "true" && process.env.NODE_ENV === "production") {
  throw new Error("SANDBOX_MODE must never be set in production")
}
```

Run the same contract test twice: once with the sandbox flag on, and once against the production branch backed by a
Testcontainers database, as `tdd-workflow` requires for integration tests. Parity means both runs pass. The sandbox run
alone only proves the branch that never ships.

```typescript
it("returns every contract field", async () => {
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
Restore only the item this call removed rather than a snapshot of the whole list, because a snapshot taken before two
overlapping deletes brings back the one that succeeded. Record the item's index before removing it and reinsert it there, so the rollback
leaves the list in its original order rather than moving the item to the end.

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
  const index = items.findIndex(item => item.id === id)
  const removed = items[index]
  setItems(prev => prev.filter(item => item.id !== id))
  try {
    const res = await fetch(`/api/items/${id}`, { method: "DELETE" })
    if (!res.ok) {
      throw new Error(`Delete failed with ${res.status}`)
    }
  } catch (err) {
    logger.error({ err }, "Failed to remove item, rolling back")
    setItems(prev => (removed ? [...prev.slice(0, index), removed, ...prev.slice(index)] : prev))
    setError("Could not delete the item")
  }
}
```

Type cast masking a null. A cast tells the compiler a value exists without making it exist, so the failure moves from
build time to run time. Assert the field is not undefined rather than trusting the type.

| Pattern | Test strategy | Priority |
| --- | --- | --- |
| Sandbox and production mismatch | Assert the full contract in sandbox mode and against the production branch | High |
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
