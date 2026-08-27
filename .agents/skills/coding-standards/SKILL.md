---
name: coding-standards
description: Canonical baseline for cross-project engineering principles (SOLID, DRY, KISS, YAGNI, FIRST), naming, control flow, immutability, error handling, architecture, and feature flags. The hub other skills defer to for the shared floor; use framework skills for stack-specific patterns.
origin: ECC
---

# Coding Standards & Best Practices

Baseline coding conventions applicable across projects.

This skill is the shared floor, not the detailed framework playbook.

- Use `frontend-patterns` for React, state, forms, rendering, and UI architecture.
- Use `backend-patterns` or `api-design` for repository/service layers, endpoint design, validation, and server-specific
  concerns.
- Use `rules/common/coding-style.md` when you need the shortest reusable rule layer instead of a full skill walkthrough.

---

### When to Activate

- Starting a new project or module
- Reviewing code for quality and maintainability
- Refactoring existing code to follow conventions
- Enforcing naming, formatting, or structural consistency
- Setting up linting, formatting, or type-checking rules
- Onboarding new contributors to coding conventions

---

### Scope Boundaries

Activate this skill for:
- descriptive naming
- immutability defaults
- readability, KISS, DRY, and YAGNI enforcement
- error-handling expectations and code-smell review

Do not use this skill as the primary source for:
- React composition, hooks, or rendering patterns
- backend architecture, API design, or database layering
- domain-specific framework guidance when a narrower ECC skill already exists

---

### Core principles

These are the engineering floor for every project. A request or an existing pattern that breaks one of them is a defect,
the same as a failing test. Say so and propose the version that respects them.

- SOLID. Single responsibility: one reason to change per class or function. Open for extension, closed for modification:
  add behaviour by extending, not by editing working code. Liskov substitution: a subtype works anywhere its base type
  is expected. Interface segregation: many small focused interfaces over one large one. Dependency inversion: depend on
  abstractions, never on concrete implementations.
- DRY. Every piece of knowledge has one source of truth. Extract shared logic into one well-named place. No copy-paste
  programming.
- KISS. The simplest solution that fully works wins. No cleverness for its own sake.
- YAGNI. Build only what is needed now. No speculative abstractions or configurability nobody asked for.
- FIRST for tests. Fast, isolated, repeatable, self-validating, and timely, written with the code and ideally before it.
- Favour composition over inheritance, immutable data over mutable state, and pure functions over hidden side effects.

The detailed testing playbook lives in the `tdd-workflow`, `python-testing`, `golang-testing`, and `springboot-tdd`
skills; this hub only states the principle.

---

### Naming and control flow

- Names explain themselves. Use descriptive, intention-revealing names for everything. If a piece of logic needs a
  comment to explain what it does, extract it into a well-named function instead.
- Functions use the verb-then-noun pattern (`calculateTotalRevenue`, `fetchMarketData`), never a bare noun or a single
  letter. Booleans start with `is`, `has`, or `can`.
- No magic numbers or strings. Extract them into named constants or configuration.
- Use guard clauses and early returns instead of deep nesting.
- Prefer an explicit type name over an inferred-type keyword where the language allows one, except where an idiom
  requires inference (for example Go short variable declarations).
- Use imports. Never write a fully-qualified name inline.
- Keep functions short and single-responsibility. A function much longer than a screen, or with five levels of nesting,
  is a smell to split.
- The codebase is English only. Translate any foreign-language name at the boundary.

#### 5. Functional Pipelines Over Imperative Cascades

When transforming a collection, filter, then map, then aggregate -
prefer a pipeline (one operation per step, top-down) over an
imperative `for` loop with `if`-`else` cascading and an explicit
accumulator. The pipeline reads as "what we're doing to the data";
the cascade reads as "how the bookkeeping goes."

This is a code-shape rule, not a syntax-level formatting one. The
sibling `code-formatter` skill says "one chain step per line"; this
skill says "reach for the chain in the first place."

##### Dart

```dart
// BAD: imperative cascade
final activeNames = <String>[];
for (final e in exercises) {
  if (e.isActive) {
    activeNames.add(e.name);
  }
}

// GOOD: pipeline
final activeNames = exercises
    .where((e) => e.isActive)
    .map((e) => e.name)
    .toList();
```

##### Java

Java's `Stream` API and `Optional` are explicitly designed for this.
A `for` + `if` + `list.add` block where a stream would do is a code
smell in modern Java.

```java
// BAD
List<String> activeNames = new ArrayList<>();
for (Exercise e : exercises) {
    if (e.isActive()) {
        activeNames.add(e.name());
    }
}

// GOOD
List<String> activeNames = exercises.stream()
    .filter(Exercise::isActive)
    .map(Exercise::name)
    .toList();

// Same principle for nullable values: reach for Optional, not if-null
// BAD
Exercise e = repository.findById(id);
if (e != null) {
    return e.name();
} else {
    return "unknown";
}

// GOOD
return repository.findById(id)
    .map(Exercise::name)
    .orElse("unknown");
```

##### Python

Python's idiomatic equivalent is a comprehension (or, for lazy
streams, a generator expression). Reach for them before you reach
for an explicit `for` + `if` + `list.append`.

```python
# BAD
active_names = []
for e in exercises:
    if e.is_active:
        active_names.append(e.name)

# GOOD
active_names = [e.name for e in exercises if e.is_active]

# When the transformation is heavier than a single expression, a
# generator + sum/max/min/any/all keeps the pipeline shape:
total_reps = sum(s.reps for s in series if s.reps > 0)
```

##### When NOT to convert

- Side effects inside the loop body (writing to disk, calling an API
  with an index-dependent argument, mutating an outside variable)
  belong in an explicit `for`, pipelines should be pure.
- Early termination on a complex condition that doesn't map to
  `takeWhile`/`first` cleanly.
- Cases where the cascade is genuinely clearer to a reader unfamiliar
  with the codebase's style, clarity outranks compactness.

The point is prefer, not always.

---

### Error handling and logging

- Never swallow an exception. Use specific, meaningful exception types, not generic ones, and never an empty catch that
  hides the failure.
- Handle errors in one central place rather than wrapping every method in its own try/catch. Let a global handler turn
  an error into the correct response.
- Chain exceptions so the original cause and its stack trace are preserved.
- Do not add error handling for situations that cannot happen.
- Return errors in a consistent, structured shape with a clear code and message. For a web service, map each error type
  to the correct status code and never leak internal detail (no stack trace, no disclosure of whether an account
  exists).
- Log through a single logging abstraction, never a concrete logging backend in business code. Use structured logging
  with meaningful levels and a correlation or trace identifier. Never log secrets, credentials, or personal data; mask
  sensitive fields.

The full logging and observability playbook lives in the `observability-and-logging` skill.

---

### Architecture

- Depend on abstractions and contracts, not on concrete implementations.
- Keep business logic separate from frameworks, from input and output, and from storage, so it can be tested on its own
  and moved without dragging the rest along.
- Layer the system and let dependencies point one way, toward the core. Enforce that direction with an automated check
  where the toolchain supports it.
- Inject dependencies through the constructor. Avoid hidden global state.
- Validate inputs at the entry of a method and fail fast on bad input.
- Model state explicitly. Represent something that can be in one of several states as exactly one of those states at a
  time, never as a loose bag of flags that can contradict each other.

The detailed ports-and-adapters treatment lives in the `hexagonal-architecture` skill.

---

### Feature flags

Gate risky, incomplete, or experimental work behind a feature flag rather than a long-lived branch that drifts from the
main line.

- Merge work into the main branch early, kept dark behind a flag, so integration stays continuous and each change is
  reviewed in small pieces.
- Give every flag a clear name, an owner, and a planned removal date. A flag is temporary scaffolding: delete it and its
  dead branches once the feature is fully shipped.
- Default a flag to off, and read its state from configuration so it can be turned on without a new deployment.
- Keep the flag check at the edge of the feature, in one place, rather than scattered through the code.

---

### Architecture decision records

Record every significant design decision as a short architecture decision record with the context, the decision, and the
consequences. Keep design rationale and decision history out of source files. The format and workflow live in the
`architecture-decision-records` skill.

---

### TypeScript/JavaScript Standards

#### Variable Naming

```typescript
// PASS: GOOD: Descriptive names
const marketSearchQuery = 'election'
const isUserAuthenticated = true
const totalRevenue = 1000

// FAIL: BAD: Unclear names
const q = 'election'
const flag = true
const x = 1000
```

#### Function Naming

```typescript
// PASS: GOOD: Verb-noun pattern
async function fetchMarketData(marketId: string) { }
function calculateSimilarity(a: number[], b: number[]) { }
function isValidEmail(email: string): boolean { }

// FAIL: BAD: Unclear or noun-only
async function market(id: string) { }
function similarity(a, b) { }
function email(e) { }
```

#### Immutability Pattern (CRITICAL)

```typescript
// PASS: ALWAYS use spread operator
const updatedUser = {
  ...user,
  name: 'New Name'
}

const updatedArray = [...items, newItem]

// FAIL: NEVER mutate directly
user.name = 'New Name'  // BAD
items.push(newItem)     // BAD
```

#### Error Handling

```typescript
// PASS: GOOD: Comprehensive error handling
async function fetchData(url: string) {
  try {
    const response = await fetch(url)

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return await response.json()
  } catch (error) {
    throw new Error('Failed to fetch data', { cause: error })
  }
}

// FAIL: BAD: No error handling
async function fetchData(url) {
  const response = await fetch(url)
  return response.json()
}
```

#### Async/Await Best Practices

```typescript
// PASS: GOOD: Parallel execution when possible
const [users, markets, stats] = await Promise.all([
  fetchUsers(),
  fetchMarkets(),
  fetchStats()
])

// FAIL: BAD: Sequential when unnecessary
const users = await fetchUsers()
const markets = await fetchMarkets()
const stats = await fetchStats()
```

#### Type Safety

```typescript
// PASS: GOOD: Proper types
interface Market {
  id: string
  name: string
  status: 'active' | 'resolved' | 'closed'
  created_at: Date
}

function getMarket(id: string): Promise<Market> {
  // Implementation
}

// FAIL: BAD: Using 'any'
function getMarket(id: any): Promise<any> {
  // Implementation
}
```

---

### Comments & Documentation

#### When to Comment

Default to no comments. Identifiers and structure already say what the code does. Add a comment only when the why is
non-obvious, a hidden invariant, a workaround for a specific defect with a stable external reference (CVE, RFC section),
or behavior that would surprise a future reader.

A task marker tied to an open ticket is required, not merely allowed, whenever something is deliberately left
unimplemented. If a gap is intentional, the code must say so and name where it will be closed:
`// TODO(TICKET-001): <what's missing>`. A gap with no ticketed marker is a defect, not a style choice.

What is banned is a reference that stands in place of the explanation rather than alongside it: a ticket number, a PR
number, or a review section cited instead of the reasoning (`// TICKET-001 fix`, `// per review §4.4`,
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

// Set name to user's name
name = user.name

// FAIL: BAD: a reference standing in for the explanation, not naming a gap
// TICKET-001 §4.4: switch to ArrayList
// PR #15 review comment fix
// added for the cleanup pass
```

#### Doc Comments

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

Measure before optimising, fix the one real bottleneck, avoid the N+1 query problem, fetch only the columns you need,
cache where reads dominate and staleness is tolerable, and run independent input and output work concurrently. The full
treatment lives in the `performance-optimization` skill.

---

### Testing Standards

#### Test Structure (AAA Pattern)

```typescript
test('calculates similarity correctly', () => {
  // Arrange
  const vector1 = [1, 0, 0]
  const vector2 = [0, 1, 0]

  // Act
  const similarity = calculateCosineSimilarity(vector1, vector2)

  // Assert
  expect(similarity).toBe(0)
})
```

#### Test Naming

```typescript
// PASS: GOOD: Descriptive test names
test('returns empty array when no markets match query', () => { })
test('throws error when OpenAI API key is missing', () => { })
test('falls back to substring search when Redis unavailable', () => { })

// FAIL: BAD: Vague test names
test('works', () => { })
test('test search', () => { })
```

---

### Code Smell Detection

Watch for these anti-patterns:

#### 1. Long Functions
```typescript
// FAIL: BAD: Function > 50 lines
function processMarketData() {
  // 100 lines of code
}

// PASS: GOOD: Split into smaller functions
function processMarketData() {
  const validated = validateData()
  const transformed = transformData(validated)
  return saveData(transformed)
}
```

#### 2. Deep Nesting
```typescript
// FAIL: BAD: 5+ levels of nesting
if (user) {
  if (user.isAdmin) {
    if (market) {
      if (market.isActive) {
        if (hasPermission) {
          // Do something
        }
      }
    }
  }
}

// PASS: GOOD: Early returns
if (!user) return
if (!user.isAdmin) return
if (!market) return
if (!market.isActive) return
if (!hasPermission) return

// Do something
```

#### 3. Magic Numbers
```typescript
// FAIL: BAD: Unexplained numbers
if (retryCount > 3) { }
setTimeout(callback, 500)

// PASS: GOOD: Named constants
const MAX_RETRIES = 3
const DEBOUNCE_DELAY_MS = 500

if (retryCount > MAX_RETRIES) { }
setTimeout(callback, DEBOUNCE_DELAY_MS)
```

Remember: Code quality is not negotiable. Clear, maintainable code enables rapid development and confident refactoring.
