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

The full statement of each floor rule in SKILL.md, with its pass and fail forms. A framework skill extends this floor and never contradicts it, so when the two disagree, this hub is the one that needs fixing. Load this file when a rule's one-line summary in SKILL.md does not settle the case in front of you.

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

Names explain themselves, with no cryptic abbreviation, so logic that needs a comment to say what it does gets extracted into a well-named function
instead. A type parameter that stands for a domain role is named for it, such as `TRow`, rather than explained in a doc comment, as [typescript-examples.md](typescript-examples.md) shows. A fixed value gets a named constant and a tunable goes to configuration, as [code-smells.md](code-smells.md) shows. Functions read verb then noun. Booleans start with is, has or can. No magic number or string survives
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

When transforming a collection, filter then map then aggregate, prefer a pipeline with one operation per step
reading top down, over an imperative loop with an if-else cascade and an explicit accumulator. The pipeline reads as
what is being done to the data. The cascade reads as how the bookkeeping goes. The pass and fail form per language is
in [dart.md](dart.md), [java.md](java.md) and [python.md](python.md).

This is a code-shape rule, not a syntax-level formatting one. Where the project runs a formatter that owns line
breaking (dart format, google-java-format, ruff format, black), its output decides how a chain wraps. Where none does,
the sibling `code-formatter` skill says one chain step per line. This rule says reach for the chain in the first
place.

Keep the loop, and do not convert it, in three cases:

- Side effects inside the loop body, such as writing to disk, calling an API with an index-dependent argument, or
  mutating an outside variable. Those belong in an explicit loop, because a pipeline should be pure.
- Early termination on a complex condition that does not map cleanly onto a take-while or a first-match operation.
- Cases where the cascade is genuinely clearer to a reader unfamiliar with the codebase style. Clarity outranks
  compactness.

The point is prefer, not always.

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

Every test sets up state, performs one action, then asserts the observable outcome. The phases are marked with the bare `// Given`, `// When` and `// Then` comments, or `// When & Then` where the action is the assertion, and those markers are the only comments a test carries. Name a
test for the behaviour and the condition, so a failure report reads as a sentence. Worked examples, test isolation and
the two naming forms are in `tdd-workflow`, and the per-language mechanics in `python-patterns`, `golang-patterns` and
`springboot-patterns`.

---

### Code smells

Watch for long functions, deep nesting, magic numbers, and any block that needs a comment to be understood. Each of
those calls for restructuring rather than for a comment. The failing and repaired forms are in
[code-smells.md](code-smells.md).
