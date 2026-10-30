# Principles in Depth

Contents:

- [Core principles](#core-principles)
- [Naming and control flow](#naming-and-control-flow)
- [Functional pipelines over imperative cascades](#functional-pipelines-over-imperative-cascades)
- [Error handling and logging](#error-handling-and-logging)
- [Architecture](#architecture)
- [Feature flags](#feature-flags)
- [Architecture decision records](#architecture-decision-records)
- [Performance](#performance)
- [Test structure](#test-structure)
- [Code smells](#code-smells)
- [Neighbouring skills](#neighbouring-skills)

The full statement of each floor rule in SKILL.md, with its pass and fail forms. Load this file when a rule's one-line summary in SKILL.md does not settle the case in front of you.

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
[functional-pipelines.md](functional-pipelines.md).

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
[code-smells.md](code-smells.md).

---

### Neighbouring skills

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
