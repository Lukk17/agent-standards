---
name: coding-standards
description: 'The cross-project engineering floor: SOLID, DRY, KISS, YAGNI, FIRST, intention-revealing naming, guard clauses, immutability, structured errors, layering, feature flags, and code that explains itself rather than carrying comments. Use when you say "review this for quality", "start this module properly", "refactor to our conventions", "should this have a comment", or "set up our naming rules". Not for stack-specific patterns, use a framework skill such as `springboot-patterns`.'
---

# Coding Standards

The shared floor every project stands on, stated without reference to a language or a framework. A framework skill
extends this floor with stack-specific patterns and never contradicts it, so when the two disagree, this hub is the
one that needs fixing.

| Task | Open |
|---|---|
| Wanting a rule shown as concrete code rather than stated | [typescript-examples.md](references/typescript-examples.md) |
| Reviewing for structural problems and naming the shape you found | [code-smells.md](references/code-smells.md) |
| Converting a loop into a pipeline, or deciding not to | [functional-pipelines.md](references/functional-pipelines.md) |

---

### When to activate

- Starting a new project or module
- Reviewing code for quality and maintainability
- Refactoring existing code toward the conventions
- Enforcing naming, structure or control-flow consistency
- Setting up linting, formatting or type-checking rules
- Onboarding a contributor to the conventions
- Deciding whether a comment or a doc comment belongs in the code at all

---

### When not to activate

- React composition, hooks, state and rendering, use `react-patterns`
- Backend service structure, endpoints and data access, use `backend-patterns` or `api-design`
- Blank lines, brace placement and chain breaking inside a function body, use `code-formatter`
- The full testing playbook rather than the principle, use `tdd-workflow` or the language test skill
- Logging and observability beyond the one rule here, use `observability-and-logging`
- Ports and adapters in depth, use `hexagonal-architecture`
- Any case where a narrower skill in this repository already covers the stack in question

---

### Core principles

These are the floor. A request or an existing pattern that breaks one of them is a defect, the same as a failing
test, so say so and propose the version that respects it.

- SOLID. One reason to change per unit. Extend rather than edit working code. A subtype works anywhere its base type
  does. Many small interfaces beat one large one. Depend on abstractions, never on concrete implementations.
- DRY. Every piece of knowledge has one source of truth. Extract shared logic into one well-named place.
- KISS. The simplest solution that fully works wins.
- YAGNI. Build only what is needed now. No speculative abstraction, no configurability nobody asked for.
- FIRST for tests. Fast, isolated, repeatable, self-validating, timely, written with the code and ideally before it.
- Favour composition over inheritance, immutable data over mutable state, pure functions over hidden side effects.

Pass:

```text
Added the second payment provider by implementing the existing gateway interface. No caller changed.
```

Fail:

```text
Added the second payment provider with an if-else on provider name inside the existing gateway class.
```

---

### Naming and control flow

Names explain themselves, so logic that needs a comment to say what it does gets extracted into a well-named function
instead. Functions read verb then noun. Booleans start with is, has or can. No magic number or string survives
outside a named constant. Guard clauses and early returns replace deep nesting. Prefer an explicit type name where
the language allows one, except where the idiom requires inference. Use imports rather than inline fully-qualified
names. Keep functions short and single-purpose. The codebase is English only, so translate a foreign-language name at
the boundary.

Pass:

```typescript
function calculateTotalRevenue(orders: Order[]): Money { }
const isUserAuthenticated = session !== null
const MAX_RETRIES = 3
```

Fail:

```typescript
function revenue(o) { }
const flag = true
if (retryCount > 3) { }
```

---

### Functional pipelines over imperative cascades

When transforming a collection, reach for a pipeline of filter, map and aggregate before an imperative loop with an
if-else cascade and an accumulator. The pipeline states what is being done to the data. Keep the loop where the body
has side effects, where early termination does not map cleanly onto a pipeline operation, or where the cascade is
genuinely clearer to a reader. The rule is prefer, not always. Worked examples per language are in
[functional-pipelines.md](references/functional-pipelines.md).

Pass:

```python
active_names = [e.name for e in exercises if e.is_active]
```

Fail:

```python
active_names = []
for e in exercises:
    if e.is_active:
        active_names.append(e.name)
```

---

### Error handling and logging

Never swallow an exception and never write an empty catch that hides a failure. Use specific exception types. Handle
errors centrally rather than wrapping every method in its own try block, and let a global handler turn an error into
the right response. Chain exceptions so the original cause and its stack survive. Do not handle situations that
cannot happen. Return a consistent structured error shape with a code and a message, map each type to the right
status code for a web service, and leak no internal detail, no stack trace and no fact about whether an account
exists. Log through one logging abstraction rather than a concrete backend in business code, with structured output,
meaningful levels and a correlation identifier, and never log a secret, a credential or personal data.

Pass:

```typescript
try {
  return await fetchOrder(id)
} catch (error) {
  throw new OrderLookupError(`Order ${id} unavailable`, { cause: error })
}
```

Fail:

```typescript
try {
  return await fetchOrder(id)
} catch (e) {
}
```

The full logging and observability playbook lives in `observability-and-logging`.

---

### Architecture

Depend on abstractions and contracts, not on concrete implementations. Keep business logic separate from frameworks,
from input and output, and from storage, so it can be tested alone and moved without dragging the rest with it. Layer
the system so dependencies point one way, toward the core, and enforce that direction with an automated check where
the toolchain has one. Inject dependencies through the constructor and avoid hidden global state. Validate input at
the entry of a method and fail fast. Model state explicitly, as exactly one of several named states, never as a bag
of flags that can contradict each other.

Pass:

```typescript
type Order = { status: 'draft' } | { status: 'paid', paidAt: Date } | { status: 'cancelled', reason: string }
```

Fail:

```typescript
type Order = { isDraft: boolean, isPaid: boolean, isCancelled: boolean, paidAt?: Date }
```

The detailed ports-and-adapters treatment lives in `hexagonal-architecture`.

---

### Feature flags

Gate risky, incomplete or experimental work behind a flag rather than a long-lived branch that drifts from the main
line. Merge early and keep the work dark, so integration stays continuous and every change is reviewed small. Give
each flag a name, an owner and a planned removal date, then delete the flag and its dead branch once the feature has
fully shipped. Default a flag to off and read it from configuration so it can be turned on without a deployment. Keep
the check at the edge of the feature, in one place.

Pass:

```typescript
if (!flags.isEnabled('checkout-v2')) return renderLegacyCheckout()
```

Fail:

```typescript
if (process.env.CHECKOUT_V2 === 'true' && user.id % 2 === 0) { }
```

---

### Architecture decision records

Record every significant design decision as a short record with the context, the decision and the consequences, and
keep design rationale and decision history out of source files. The format and the workflow live in
`architecture-decision-records`.

---

### Comments

Default to no comments. Identifiers and structure already say what the code does. Add a comment only when the why is
non-obvious, a hidden invariant, a workaround for a specific defect with a stable external reference such as a CVE or
an RFC section, or behaviour that would surprise a future reader.

A task marker tied to an open ticket is required, not merely allowed, whenever something is deliberately left
unimplemented. If a gap is intentional, the code must say so and name where it will be closed:
`// TODO(TICKET-001): <what is missing>`. A gap with no ticketed marker is a defect, not a style choice.

What is banned is a reference that stands in place of the explanation rather than alongside it: a ticket number, a PR
number, or a review section cited instead of the reasoning (`// TICKET-001 fix`, `// per review section 4.4`,
`// PR #15 review comment fix`). Each of those gives a number and a verb and says nothing about what constraint holds,
so the next reader has to open a tracker to learn anything the comment should have said directly. A task marker that
names what is missing and links where it will be done is the opposite of that, which is why it is the one form this
rule requires rather than merely tolerates.

```typescript
// PASS: GOOD: Explain WHY, not WHAT
// Use exponential backoff to avoid overwhelming the API during outages
const delay = Math.min(1000 * Math.pow(2, retryCount), 30000)

// PASS: GOOD: required task marker naming what's missing and where it's tracked
// TODO(TICKET-001): retry path for 429 responses is not handled yet

// FAIL: BAD: Stating the obvious
// Increment counter by 1
count++

// FAIL: BAD: a reference standing in for the explanation, not naming a gap
// TICKET-001 section 4.4: switch to ArrayList
// PR #15 review comment fix
// added for the cleanup pass
```

---

### Doc Comments

Default to none. A doc comment is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named function, rename the parameters so they carry their own meaning, and tighten the
types. Do that first and most doc comments have nothing left to say, which is the outcome you want. Code that explains
itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@param` and `@returns` and `@throws` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `@param` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or
   who owns the argument afterwards. `@param userId - The user identifier` is noise, delete it, and never restate a
   type TypeScript already declares.
3. `@returns` only when it is non-obvious.
4. `@throws` always, for every error a caller can act on. TypeScript keeps throws out of the signature, so this one is
   genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

```typescript
// PASS: GOOD: One sentence, then only what the signature cannot say
/**
 * Searches markets using semantic similarity.
 *
 * @param limit upper bound on results, values above 50 are clamped
 * @returns matches ordered by descending similarity
 * @throws {ServiceUnavailableError} when the embedding backend is unreachable
 */
export async function searchMarkets(query: string, limit: number = 10): Promise<Market[]> {
  // Implementation
}

// FAIL: BAD: Restates the signature, wraps a tag onto a second line, pads with an example nobody maintains
/**
 * Searches markets.
 *
 * @param query - Natural language search query
 * @param limit - Maximum number of results, defaults to 10 and is passed
 *                straight through to the vector store
 * @returns Array of markets
 *
 * @example
 * const results = await searchMarkets('election', 5)
 */
export async function searchMarkets(query: string, limit: number = 10): Promise<Market[]> {
  // Implementation
}

// PASS: BEST: Extraction and naming removed the need for a doc comment entirely
export async function searchMarketsBySimilarity(query: string, maxResults = 10): Promise<Market[]> {
  // Implementation
}
```

---

### Performance

Measure before optimising, fix the one real bottleneck, avoid the N+1 query, fetch only the columns you need, cache
where reads dominate and staleness is tolerable, and run independent input and output work concurrently. Optimising
without a measurement is guessing, and a guess that lands is indistinguishable from one that does not. The full
treatment lives in `performance-optimization`.

---

### Test structure

Every test sets up state, performs one action, then asserts the observable outcome. Which words label the three
phases is the project's choice: Arrange, Act, Assert and Given, When, Then are the two common spellings, and a
project may have its own. Read how existing tests are labelled and match them, and pick a convention only when the
project has none. Name a test for the behaviour and the condition, so a failure report reads as a sentence.

Pass:

```typescript
test('returns an empty array when no markets match the query', () => { })
```

Fail:

```typescript
test('works', () => { })
```

The detailed testing playbook lives in `tdd-workflow`, `python-patterns`, `golang-patterns` and
`springboot-patterns`.

---

### Code smells

Watch for long functions, deep nesting, magic numbers, and any block that needs a comment to be understood. Each of
those calls for restructuring rather than for a comment. The failing and repaired forms are in
[code-smells.md](references/code-smells.md).

Pass:

```typescript
if (!user) return
if (!user.isAdmin) return
if (!market.isActive) return
```

Fail:

```typescript
if (user) {
  if (user.isAdmin) {
    if (market.isActive) {
    }
  }
}
```

---

### Related skills

- `code-formatter` owns blank lines, brace placement and chain breaking inside a function body
- `react-patterns` owns React composition, hooks, state and rendering
- `backend-patterns` and `api-design` own service structure, endpoints and contracts
- `hexagonal-architecture` owns ports, adapters and dependency direction in depth
- `observability-and-logging` owns structured logging, tracing, metrics and health
- `performance-optimization` owns profiling and the measure-first loop
- `architecture-decision-records` owns the decisions this hub keeps out of source files
- `tdd-workflow`, `python-patterns`, `golang-patterns` and `springboot-patterns` own the testing playbook
- `java-coding-standards`, `python-patterns`, `golang-patterns` and `dart-flutter-patterns` own per-language idiom

---

### Checklist

- [ ] Every name reveals intent, no single letters, no bare nouns for functions
- [ ] No magic number or string outside a named constant
- [ ] Guard clauses used instead of deep nesting
- [ ] No swallowed exception, no empty catch, causes chained
- [ ] Errors returned in one structured shape, no internal detail leaked
- [ ] Business logic separable from framework, input and output, and storage
- [ ] State modelled as one of several named states, not a bag of flags
- [ ] Every feature flag has an owner and a removal date
- [ ] Every deliberate gap carries a ticketed task marker
- [ ] No comment states what the code already says
- [ ] Significant design decisions recorded outside the source files
