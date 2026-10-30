---
name: coding-standards
description: 'The cross-project engineering floor: SOLID as heuristics under KISS and YAGNI, DRY without coincidental merges, naming, guard clauses, one error shape, layering, feature flags, and when a comment or doc comment belongs. Use when the user says "review this for quality", "refactor to our conventions", or "should this have a comment". Not for stack-specific patterns, use `springboot-patterns`.'
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

- Starting a new project or module, or the user says "start this module properly"
- Reviewing code for quality and maintainability, or the user says "review this for quality"
- Refactoring existing code toward the conventions, or the user says "refactor to our conventions"
- Enforcing naming, structure or control-flow consistency, or the user says "set up our naming rules"
- Setting up linting, formatting or type-checking rules
- Onboarding a contributor to the conventions
- Deciding whether a comment or a doc comment belongs in the code at all, or the user asks "should this have a
  comment"
- Deciding whether to introduce an abstraction or merge two similar blocks

---

### When not to activate

- React composition, hooks, state and rendering, use `react-patterns`
- Backend service structure, endpoints and data access, use `backend-patterns` or `api-design`
- Blank lines, chain breaking and comment placement inside a Dart, Java or Python function body, use
  `code-formatter`. Any other language follows its language skill or its default formatter, and brace placement
  and indent width follow each language's default formatter
- The full testing playbook rather than the principle, use `tdd-workflow` or the language test skill
- Logging and observability beyond the one rule here, use `observability-and-logging`
- Ports and adapters in depth, use `hexagonal-architecture`
- Any case where a narrower skill in this repository already covers the stack in question

---

### Core principles

These are the floor. When two of them pull in opposite directions, KISS and YAGNI win until a second real use case
appears. A request or an existing pattern that ignores the floor with no such reason is worth naming, with the version
that respects it.

- SOLID, as heuristics rather than laws. One reason to change per unit. Prefer adding a new implementation over growing
  a conditional inside a stable one. A subtype works anywhere its base type does. Keep interfaces small. Introduce an
  abstraction at a boundary you actually need to swap or test (I/O, a vendor, a clock), not in front of every class.
- DRY. Every piece of knowledge has one source of truth. Two blocks that look alike but change for different reasons
  are not duplication. Extract on the third real occurrence, or when the copies must change together.
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

Fail, the opposite mistake:

```text
Put a PriceCalculator interface in front of the only calculator. No second implementation, no test needs a fake.
```

---

### Naming and control flow

Names explain themselves, so logic that needs a comment to say what it does gets extracted into a well-named function
instead. Functions read verb then noun. Booleans start with is, has or can. No magic number or string survives
outside a named constant. Guard clauses and early returns replace deep nesting. Annotate every public signature
(parameters and return types). For locals, follow the language's idiom: infer where the initializer makes the type
obvious, and name the type where it does not. Use imports rather than inline fully-qualified names. Keep functions
short and single-purpose. The codebase is English only, so translate a foreign-language name at the boundary.

Pass:

```typescript
const MAX_RETRIES = 3

function calculateTotalRevenueCents(orders: Order[]): number {
  return orders.reduce((sum, order) => sum + order.totalCents, 0)
}

const isUserAuthenticated = session !== null
```

Fail:

```typescript
function revenue(o: Order[]): number {
  return o.reduce((s, x) => s + x.totalCents, 0)
}

const flag: boolean = session !== null
if (retryCount > 3) {
  retry()
}
```

Adopt the language's default formatter and linter, run both as a CI check, and let them settle every layout question
they own. Neither a reviewer nor a skill argues with their output.

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
the right response. Catch locally only to translate a low-level failure into a domain error, and chain the cause so the
original stack survives. Do not handle situations that cannot happen. Return one structured error shape across the
surface, which for an HTTP API is the problem details format defined in `api-design` (RFC 9457), and map each error
type to its status code there. Leak no internal detail, no stack trace and no fact about whether an account exists.
Log through one logging abstraction rather than a concrete backend in business code, with structured output,
meaningful levels and a correlation identifier, and never log a secret, a credential or personal data.

Pass:

```typescript
async function loadOrder(id: string): Promise<Order> {
  try {
    return await fetchOrder(id)
  } catch (error) {
    throw new OrderLookupError(`Order ${id} unavailable`, { cause: error })
  }
}
```

Fail:

```typescript
async function loadOrder(id: string): Promise<Order | undefined> {
  try {
    return await fetchOrder(id)
  } catch (error) {
  }
}
```

The full logging and observability playbook lives in `observability-and-logging`.

---

### Architecture

Keep business logic separate from frameworks, from input and output, and from storage, so it can be tested alone and
moved without dragging the rest with it. At those boundaries the core depends on a contract it owns rather than on the
concrete adapter. Layer the system so dependencies point one way, toward the core, and enforce that direction with an
automated check where the toolchain has one. Inject dependencies through the constructor and avoid hidden global
state. Validate untrusted input once at the boundary into a typed value, and assert invariants in constructors. Model
state explicitly, as exactly one of several named states, never as a bag
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
function renderCheckout(): Page {
  if (!flags.isEnabled('checkout-v2')) {
    return renderLegacyCheckout()
  }
  return renderCheckoutV2()
}
```

Fail:

```typescript
function renderCheckout(): Page {
  if (process.env.CHECKOUT_V2 === 'true' && user.id % 2 === 0) {
    return renderCheckoutV2()
  }
  return renderLegacyCheckout()
}
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

This is the one canonical doc-comment rule. Each language skill points here and adds only its own delta, such as the
tag spelling (`Args:` and `Raises:` in Python, `.PARAMETER` in PowerShell) or what its doc tool renders. The tag names
below use the JSDoc spelling.

Default to none, with one exception. The exported surface of a published library or SDK carries a one-line doc comment
per exported symbol, because the doc tool renders it and a missing entry reads as a bug. Everything else, application
code and the internals of a library alike, defaults to none.

Two language skills widen that exception where their doc tool renders every entry, and their delta wins for those
entries only. `golang-patterns` gives every exported Go name a doc comment, application code included, because `go doc`
and pkg.go.dev render each one. `powershell` gives every function a module exports `.SYNOPSIS`, one `.PARAMETER` per
parameter and one `.EXAMPLE`, because `Get-Help` renders them, so for those tags rule 2 below gives way to the one-line
cap. Unexported Go code and private PowerShell helpers keep the default of none.

A doc comment is usually a sign that the code failed to explain itself. Before writing one, extract the unclear block
into a well-named function, rename the parameters so they carry their own meaning, and tighten the types. Do that first
and most doc comments have nothing left to say, which is the outcome you want. Code that explains itself cannot go
stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@param` and `@returns` and `@throws` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `@param` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or
   who owns the argument afterwards. `@param userId - The user identifier` is noise, delete it, and never restate a
   type the signature already declares.
3. `@returns` only when it is non-obvious.
4. `@throws` always, for every error a caller can act on. Most languages keep thrown errors out of the signature
   (TypeScript, Python, unchecked Java exceptions), so this one is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

Pass, one sentence, then only what the signature cannot say:

```typescript
/**
 * Searches markets using semantic similarity.
 *
 * @param limit upper bound on results, values above 50 are clamped
 * @returns matches ordered by descending similarity
 * @throws {ServiceUnavailableError} when the embedding backend is unreachable
 */
export async function searchMarkets(query: string, limit = 10): Promise<Market[]> {
  return marketIndex.nearest(query, Math.min(limit, MAX_SEARCH_RESULTS))
}
```

Fail, restates the signature, wraps a tag onto a second line, and pads with an example nobody maintains:

```typescript
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
export async function searchMarkets(query: string, limit = 10): Promise<Market[]> {
  return marketIndex.nearest(query, Math.min(limit, MAX_SEARCH_RESULTS))
}
```

Best, naming carried the parameter and the ordering, so only the contract the signature cannot carry is left:

```typescript
/** @throws {ServiceUnavailableError} when the embedding backend is unreachable */
export async function searchMarketsBySimilarity(query: string, maxResults = 10): Promise<Market[]> {
  return marketIndex.nearest(query, Math.min(maxResults, MAX_SEARCH_RESULTS))
}
```

A function that cannot throw anything a caller acts on needs no doc comment at all once naming has done that work.

---

### Performance

Measure before optimising, fix the one real bottleneck, avoid the N+1 query, fetch only the columns you need, cache
where reads dominate and staleness is tolerable, and run independent input and output work concurrently. Optimising
without a measurement is guessing, and a guess that lands is indistinguishable from one that does not. The full
treatment lives in `performance-optimization`.

---

### Test structure

Every test sets up state, performs one action, then asserts the observable outcome, labelled the way the project's
existing tests label the three phases (Arrange, Act, Assert or Given, When, Then, or the project's own words). Name a
test for the behaviour and the condition, so a failure report reads as a sentence. Worked examples, test isolation and
the two naming forms are in `tdd-workflow`, and the per-language mechanics in `python-patterns`, `golang-patterns` and
`springboot-patterns`.

---

### Code smells

Watch for long functions, deep nesting, magic numbers, and any block that needs a comment to be understood. Each of
those calls for restructuring rather than for a comment. The failing and repaired forms are in
[code-smells.md](references/code-smells.md).

---

### Related skills

- `code-formatter` owns blank lines, chain breaking and where a comment sits inside a Dart, Java or Python function
  body, and leaves brace placement and indent width to each language's default formatter
- `react-patterns` owns React composition, hooks, state and rendering
- `backend-patterns` and `api-design` own service structure, endpoints and contracts
- `api-design` owns the HTTP error shape, RFC 9457 problem details, that the error rule above points to
- `review-duplication` applies the DRY rule, coincidental lookalikes included, to a change under review
- `hexagonal-architecture` owns ports, adapters and dependency direction in depth
- `observability-and-logging` owns structured logging, tracing, metrics and health
- `performance-optimization` owns profiling and the measure-first loop
- `architecture-decision-records` owns the decisions this hub keeps out of source files
- `tdd-workflow`, `python-patterns`, `golang-patterns` and `springboot-patterns` own the testing playbook
- `java-coding-standards`, `python-patterns`, `golang-patterns` and `dart-flutter-patterns` own per-language idiom

---

### Checklist

- [ ] Every name reveals intent, no single letters, no bare nouns for functions
- [ ] Public signatures annotated, locals typed the way the language's idiom says
- [ ] No magic number or string outside a named constant
- [ ] Guard clauses used instead of deep nesting
- [ ] No abstraction without a second real use case or a boundary that needs swapping or testing
- [ ] No merge of two blocks that only look alike and change for different reasons
- [ ] The default formatter and linter run in CI
- [ ] No swallowed exception, no empty catch, causes chained
- [ ] Errors returned in one structured shape, problem details on HTTP, no internal detail leaked
- [ ] Untrusted input validated once at the boundary into a typed value
- [ ] Business logic separable from framework, input and output, and storage
- [ ] State modelled as one of several named states, not a bag of flags
- [ ] Every feature flag has an owner and a removal date
- [ ] Every deliberate gap carries a ticketed task marker
- [ ] No comment states what the code already says, and the exported surface of a published library is documented
- [ ] Significant design decisions recorded outside the source files
