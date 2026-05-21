---
name: coding-standards
description: Baseline cross-project coding conventions for naming, readability, immutability, and code-quality review. Use detailed frontend or backend skills for framework-specific patterns.
origin: ECC
---

# Coding Standards & Best Practices

Baseline coding conventions applicable across projects.

This skill is the shared floor, not the detailed framework playbook.

- Use `frontend-patterns` for React, state, forms, rendering, and UI architecture.
- Use `backend-patterns` or `api-design` for repository/service layers, endpoint design, validation, and server-specific concerns.
- Use `rules/common/coding-style.md` when you need the shortest reusable rule layer instead of a full skill walkthrough.

## When to Activate

- Starting a new project or module
- Reviewing code for quality and maintainability
- Refactoring existing code to follow conventions
- Enforcing naming, formatting, or structural consistency
- Setting up linting, formatting, or type-checking rules
- Onboarding new contributors to coding conventions

## Scope Boundaries

Activate this skill for:
- descriptive naming
- immutability defaults
- readability, KISS, DRY, and YAGNI enforcement
- error-handling expectations and code-smell review

Do not use this skill as the primary source for:
- React composition, hooks, or rendering patterns
- backend architecture, API design, or database layering
- domain-specific framework guidance when a narrower ECC skill already exists

## Code Quality Principles

### 1. Readability First
- Code is read more than written
- Clear variable and function names
- Self-documenting code preferred over comments
- Consistent formatting

### 2. KISS (Keep It Simple, Stupid)
- Simplest solution that works
- Avoid over-engineering
- No premature optimization
- Easy to understand > clever code

### 3. DRY (Don't Repeat Yourself)
- Extract common logic into functions
- Create reusable components
- Share utilities across modules
- Avoid copy-paste programming

### 4. YAGNI (You Aren't Gonna Need It)
- Don't build features before they're needed
- Avoid speculative generality
- Add complexity only when required
- Start simple, refactor when needed

### 5. Functional Pipelines Over Imperative Cascades

When transforming a collection — filter, then map, then aggregate —
prefer a *pipeline* (one operation per step, top-down) over an
imperative `for` loop with `if`-`else` cascading and an explicit
accumulator. The pipeline reads as "what we're doing to the data";
the cascade reads as "how the bookkeeping goes."

This is a code-shape rule, not a syntax-level formatting one. The
sibling `code-formatter` skill says "one chain step per line"; this
skill says "*reach* for the chain in the first place."

#### Dart

```dart
// BAD — imperative cascade
final activeNames = <String>[];
for (final e in exercises) {
  if (e.isActive) {
    activeNames.add(e.name);
  }
}

// GOOD — pipeline
final activeNames = exercises
    .where((e) => e.isActive)
    .map((e) => e.name)
    .toList();
```

#### Java

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

#### Python

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

#### When NOT to convert

- Side effects inside the loop body (writing to disk, calling an API
  with an index-dependent argument, mutating an outside variable)
  belong in an explicit `for` — pipelines should be pure.
- Early termination on a complex condition that doesn't map to
  `takeWhile`/`first` cleanly.
- Cases where the cascade is genuinely clearer to a reader unfamiliar
  with the codebase's style — *clarity outranks compactness*.

The point is *prefer*, not *always*.

## TypeScript/JavaScript Standards

### Variable Naming

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

### Function Naming

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

### Immutability Pattern (CRITICAL)

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

### Error Handling

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
    console.error('Fetch failed:', error)
    throw new Error('Failed to fetch data')
  }
}

// FAIL: BAD: No error handling
async function fetchData(url) {
  const response = await fetch(url)
  return response.json()
}
```

### Async/Await Best Practices

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

### Type Safety

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

## React Best Practices

### Component Structure

```typescript
// PASS: GOOD: Functional component with types
interface ButtonProps {
  children: React.ReactNode
  onClick: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary'
}

export function Button({
  children,
  onClick,
  disabled = false,
  variant = 'primary'
}: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`btn btn-${variant}`}
    >
      {children}
    </button>
  )
}

// FAIL: BAD: No types, unclear structure
export function Button(props) {
  return <button onClick={props.onClick}>{props.children}</button>
}
```

### Custom Hooks

```typescript
// PASS: GOOD: Reusable custom hook
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}

// Usage
const debouncedQuery = useDebounce(searchQuery, 500)
```

### State Management

```typescript
// PASS: GOOD: Proper state updates
const [count, setCount] = useState(0)

// Functional update for state based on previous state
setCount(prev => prev + 1)

// FAIL: BAD: Direct state reference
setCount(count + 1)  // Can be stale in async scenarios
```

### Conditional Rendering

```typescript
// PASS: GOOD: Clear conditional rendering
{isLoading && <Spinner />}
{error && <ErrorMessage error={error} />}
{data && <DataDisplay data={data} />}

// FAIL: BAD: Ternary hell
{isLoading ? <Spinner /> : error ? <ErrorMessage error={error} /> : data ? <DataDisplay data={data} /> : null}
```

## API Design Standards

### REST API Conventions

```
GET    /api/markets              # List all markets
GET    /api/markets/:id          # Get specific market
POST   /api/markets              # Create new market
PUT    /api/markets/:id          # Update market (full)
PATCH  /api/markets/:id          # Update market (partial)
DELETE /api/markets/:id          # Delete market

# Query parameters for filtering
GET /api/markets?status=active&limit=10&offset=0
```

### Response Format

```typescript
// PASS: GOOD: Consistent response structure
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: {
    total: number
    page: number
    limit: number
  }
}

// Success response
return NextResponse.json({
  success: true,
  data: markets,
  meta: { total: 100, page: 1, limit: 10 }
})

// Error response
return NextResponse.json({
  success: false,
  error: 'Invalid request'
}, { status: 400 })
```

### Input Validation

```typescript
import { z } from 'zod'

// PASS: GOOD: Schema validation
const CreateMarketSchema = z.object({
  name: z.string().min(1).max(200),
  description: z.string().min(1).max(2000),
  endDate: z.string().datetime(),
  categories: z.array(z.string()).min(1)
})

export async function POST(request: Request) {
  const body = await request.json()

  try {
    const validated = CreateMarketSchema.parse(body)
    // Proceed with validated data
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({
        success: false,
        error: 'Validation failed',
        details: error.errors
      }, { status: 400 })
    }
  }
}
```

## File Organization

### Project Structure

```
src/
├── app/                    # Next.js App Router
│   ├── api/               # API routes
│   ├── markets/           # Market pages
│   └── (auth)/           # Auth pages (route groups)
├── components/            # React components
│   ├── ui/               # Generic UI components
│   ├── forms/            # Form components
│   └── layouts/          # Layout components
├── hooks/                # Custom React hooks
├── lib/                  # Utilities and configs
│   ├── api/             # API clients
│   ├── utils/           # Helper functions
│   └── constants/       # Constants
├── types/                # TypeScript types
└── styles/              # Global styles
```

### File Naming

```
components/Button.tsx          # PascalCase for components
hooks/useAuth.ts              # camelCase with 'use' prefix
lib/formatDate.ts             # camelCase for utilities
types/market.types.ts         # camelCase with .types suffix
```

## Comments & Documentation

### When to Comment

Default to **no comments**. Identifiers and structure already say what the code does. Add a comment only when the *why* is non-obvious — a hidden invariant, a workaround for a specific defect with a stable external reference (CVE, RFC section), or behavior that would surprise a future reader.

**Do not** write comments that reference ticket numbers, PR numbers, or review section numbers (`// PHA-270 fix`, `// per review §4.4`, `// Regression guard for §1.1`). Nobody remembers what `§1.1` means six months later; the PR description and commit message already carry that context. The one exception is a TODO tied to an open ticket: `// TODO(PHA-265): <what's missing>`.

```typescript
// PASS: GOOD: Explain WHY, not WHAT
// Use exponential backoff to avoid overwhelming the API during outages
const delay = Math.min(1000 * Math.pow(2, retryCount), 30000)

// Deliberately using mutation here for performance with large arrays
items.push(newItem)

// FAIL: BAD: Stating the obvious
// Increment counter by 1
count++

// Set name to user's name
name = user.name

// FAIL: BAD: Ticket / review-section references
// PHA-270 §4.4 — switch to ArrayList
// PR #15 review comment fix
// added for the cleanup pass
```

### JSDoc for Public APIs

```typescript
/**
 * Searches markets using semantic similarity.
 *
 * @param query - Natural language search query
 * @param limit - Maximum number of results (default: 10)
 * @returns Array of markets sorted by similarity score
 * @throws {Error} If OpenAI API fails or Redis unavailable
 *
 * @example
 * ```typescript
 * const results = await searchMarkets('election', 5)
 * console.log(results[0].name) // "Trump vs Biden"
 * ```
 */
export async function searchMarkets(
  query: string,
  limit: number = 10
): Promise<Market[]> {
  // Implementation
}
```

## Performance Best Practices

### Memoization

```typescript
import { useMemo, useCallback } from 'react'

// PASS: GOOD: Memoize expensive computations
const sortedMarkets = useMemo(() => {
  return markets.sort((a, b) => b.volume - a.volume)
}, [markets])

// PASS: GOOD: Memoize callbacks
const handleSearch = useCallback((query: string) => {
  setSearchQuery(query)
}, [])
```

### Lazy Loading

```typescript
import { lazy, Suspense } from 'react'

// PASS: GOOD: Lazy load heavy components
const HeavyChart = lazy(() => import('./HeavyChart'))

export function Dashboard() {
  return (
    <Suspense fallback={<Spinner />}>
      <HeavyChart />
    </Suspense>
  )
}
```

### Database Queries

```typescript
// PASS: GOOD: Select only needed columns
const { data } = await supabase
  .from('markets')
  .select('id, name, status')
  .limit(10)

// FAIL: BAD: Select everything
const { data } = await supabase
  .from('markets')
  .select('*')
```

## Testing Standards

### Test Structure (AAA Pattern)

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

### Test Naming

```typescript
// PASS: GOOD: Descriptive test names
test('returns empty array when no markets match query', () => { })
test('throws error when OpenAI API key is missing', () => { })
test('falls back to substring search when Redis unavailable', () => { })

// FAIL: BAD: Vague test names
test('works', () => { })
test('test search', () => { })
```

## Code Smell Detection

Watch for these anti-patterns:

### 1. Long Functions
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

### 2. Deep Nesting
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

### 3. Magic Numbers
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

**Remember**: Code quality is not negotiable. Clear, maintainable code enables rapid development and confident refactoring.

---

## Startup readiness log

Every long-running service emits one canonical multi-line INFO log entry the moment it starts **accepting traffic** — not the moment the process boots. Use the latest-possible startup hook for the framework. This single line is the most-read log entry in any service: first thing on-call sees when paging, first thing CI inspects when smoke-testing, first thing a new contributor sees when running locally. Investing in its clarity pays back every shift.

The log block contains, in order:

1. **ASCII banner** with the application name in **ANSI Shadow** FIGlet font (Unicode box-drawing: `█▀▄╔╗╚╝═║`). Width ~120 chars, 6 lines. Modern terminals, container stdout, Loki, JsonEncoder-escaped JSON logs all render it. The bold weight makes "we're up" unmistakable when scrolling startup output. Do not use Standard / Big / Slant / Small / Block ASCII FIGlet — they pack too tightly to scan from a `kubectl logs` flood, and look indistinguishable from any other log line. Plain-ASCII fallback is acceptable only when the deployment target is a known UTF-8-hostile environment (legacy `cmd.exe`, embedded serial console).

   Generate the banner once at build time, paste it into a string constant. Do NOT compute it at runtime, do NOT have the agent "draw" it freehand (the agent will silently pick a different FIGlet font, usually Standard, every time). Use one of:

   - CLI: `figlet -f 'ANSI Shadow' 'EXAMPLE'`
   - Web: <https://patorjk.com/software/taag/#p=display&f=ANSI%20Shadow&t=EXAMPLE>

   This is the canonical look for the app name `EXAMPLE`:

   ```text
   ███████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██╗     ███████╗
   ██╔════╝╚██╗██╔╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝
   █████╗   ╚███╔╝ ███████║██╔████╔██║██████╔╝██║     █████╗
   ██╔══╝   ██╔██╗ ██╔══██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝
   ███████╗██╔╝ ██╗██║  ██║██║ ╚═╝ ██║██║     ███████╗███████╗
   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝
   ```

   Tells that the wrong font was used: the banner is ~3 lines tall instead of 6, uses `/ \ _ |` ASCII slashes instead of Unicode box-drawing, looks like `_ _____ _____ ____ ____` patterns, or fits inside a single 80-column line. Regenerate with the FIGlet font explicitly set to `ANSI Shadow`.
2. **Access URLs** — `Local: http://localhost:port/...` and `Hostname: http://<resolved-hostname>:port/...`. Both are diagnostic: in Kubernetes the real external URL comes from ingress / service definitions, not the app's self-report.
3. **Active profile / environment** — whatever the framework exposes (`local`, `docker`, `prod`, `staging`).
4. **External dependencies** — each one probed with a **2-second connect + read timeout** so an unreachable dependency cannot stall the banner. Result format: `<url> [Connected | Warning (status=N) | FAILED]` — URL first, status marker last. Never include the exception detail in the banner; log it at `DEBUG` for diagnostics.
5. **Observability endpoints** — one URL per line: health / readiness / liveness / metrics / prometheus, plus OpenAPI / Swagger UI / tracing endpoint + sampling, plus the logging encoder mode by profile.

Canonical full output, what a real service should print when it accepts traffic. Match this layout precisely; omit sections that don't apply (e.g. no `Auth` section if the service is unauthenticated), but keep the ones that do in this order:

```text
███████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██╗     ███████╗
██╔════╝╚██╗██╔╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝
█████╗   ╚███╔╝ ███████║██╔████╔██║██████╔╝██║     █████╗
██╔══╝   ██╔██╗ ██╔══██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝
███████╗██╔╝ ██╗██║  ██║██║ ╚═╝ ██║██║     ███████╗███████╗
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝
----------------------------------------------------------
    Application 'example' is running!

    Access URLs:
      Local:     http://localhost:8080/example
      Hostname:  http://hostname:8080/example

    Profile(s): local

    Auth (OAuth2 Resource Server):
      Issuer:   https://keycloak.example/realms/main
      JWK Set:  https://keycloak.example/realms/main/protocol/openid-connect/certs [Connected]
      Roles:    @MainUser → hasAnyRole('USER','ADMIN')

    Service Discovery:
      Eureka:   [Disabled] (spring.cloud.discovery.enabled=false)

    Database:
      Postgres: jdbc:postgresql://db.internal:5432/example [Connected]

    Actuator:
      Health:     http://localhost:8080/example/actuator/health
      Readiness:  http://localhost:8080/example/actuator/health/readiness
      Prometheus: http://localhost:8080/example/actuator/prometheus
      Metrics:    http://localhost:8080/example/actuator/metrics

    API documentation:
      OpenAPI:    http://localhost:8080/example/openapi/v3/api-docs
      Swagger UI: http://localhost:8080/example/openapi/swagger-ui.html

    Observability:
      Tracing:  OTel bridge enabled, no OTLP endpoint set (sampling=1.0)
      Logging:  text pattern [traceId,spanId,jwt] (local/test profile)
----------------------------------------------------------
```

Format rules:

- Top and bottom separator: 58 dashes (`-` repeated). Same character, same count.
- 4-space indent for every line inside the block. Section labels are 1-indented (`    Section name:`), keys inside a section are 3-indented (`      Key: value`).
- Key column inside each section right-padded to 10-12 characters so values align vertically (`Local:     `, `Hostname:  `).
- Status markers in brackets at end of line: `[Connected]`, `[Warning (status=N)]`, `[FAILED]`, `[Disabled]`. Never include the exception detail in the banner; log it at DEBUG.
- Blank line between every section, no blank line inside a section.

### Emit the whole block in ONE log call with a leading `\n`

The banner plus the readiness body must be a single log statement whose message starts with `\n`. The leading newline pushes the first line of the banner (and every line after it) below the framework's prefix, so the banner art renders cleanly from column 0.

**Bad: one log call per line of the banner.** Every line gets its own timestamp / level / logger prefix, which destroys the art:

```text
2026-05-22 09:28:36.586 INFO  c.l.s.i.config.StartupLogConfig [Example] : ███████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██╗     ███████╗
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : ██╔════╝╚██╗██╔╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : █████╗   ╚███╔╝ ███████║██╔████╔██║██████╔╝██║     █████╗
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : ██╔══╝   ██╔██╗ ██╔══██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : ███████╗██╔╝ ██╗██║  ██║██║ ╚═╝ ██║██║     ███████╗███████╗
2026-05-22 09:28:36.587 INFO  c.l.s.i.config.StartupLogConfig [Example] : ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝
```

**Good: one log call, leading `\n`, banner art rendered cleanly underneath the single prefix line:**

```text
2026-05-22 09:28:36.586 INFO  c.l.s.i.config.StartupLogConfig [Example] :
███████╗██╗  ██╗ █████╗ ███╗   ███╗██████╗ ██╗     ███████╗
██╔════╝╚██╗██╔╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝
█████╗   ╚███╔╝ ███████║██╔████╔██║██████╔╝██║     █████╗
██╔══╝   ██╔██╗ ██╔══██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝
███████╗██╔╝ ██╗██║  ██║██║ ╚═╝ ██║██║     ███████╗███████╗
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝
----------------------------------------------------------
    Application 'example' is running!
...
```

Stack-by-stack:

- **Java / SLF4J:** `log.info("\n{}", buildStartupLog());` (placeholder substitutes the entire string).
- **Node / Pino / Winston:** `logger.info('\n' + buildStartupLog())`.
- **Python / `logging`:** `logger.info("\n" + build_startup_log())`.
- **Go / `slog`:** `logger.Info("\n" + buildStartupLog())`.
- **Bash / PowerShell:** no framework prefix at all; `cat <<'EOF'` / `Write-Host` print directly to stdout.

Never split the banner across multiple log calls. Never call `println` / `fmt.Print` / `Write-Host` from inside a log handler that adds a prefix per call.

Equally important: the **builder** must return one multi-line String. Building it via repeated `log.info(line)` calls is the same bug from a different angle. Per-call emission is non-atomic, so other threads' logs (background pools, Axon coordinators, scheduled jobs) can interleave between your readiness lines and rip the block apart visually.

**Wrong (Java, per-line emission):**

```java
log.info("----------------------------------------------------------");
log.info("    Application '{}' is running!", appName);
log.info("");
log.info("    Access URLs:");
log.info("      Local:     {}", localUrl);
log.info("      Hostname:  {}", hostnameUrl);
// ...one log call per line, each gets its own timestamp + level + logger prefix,
// and a Coordinator / scheduler / pool thread can log between any two of these.
```

**Right (Java, build then emit once):**

```java
String block = String.join("\n",
    "----------------------------------------------------------",
    "    Application '" + appName + "' is running!",
    "",
    "    Access URLs:",
    "      Local:     " + localUrl,
    "      Hostname:  " + hostnameUrl,
    // ... rest of sections
    "----------------------------------------------------------"
);
log.info("\n{}", block);
// One prefix line, the rest of the block flows under it at column 0. Atomic;
// nothing can interleave between sections.
```

Same shape for every framework: build the whole block first (StringBuilder, `String.join`, template literal, Python f-string, Go `strings.Builder`), then emit once. If the builder needs to probe dependencies asynchronously, do that work first, collect the results, then assemble the string, then log.

Pick the framework's "we're really up" hook from its own skill: [springboot-patterns](../springboot-patterns/SKILL.md), [backend-patterns](../backend-patterns/SKILL.md), [python-patterns](../python-patterns/SKILL.md), [golang-patterns](../golang-patterns/SKILL.md), [bash](../bash/SKILL.md), [powershell](../powershell/SKILL.md). The hook differs per stack; the convention above is identical.

---

## TypeScript / Node.js Project Standards

### Package Manager & Monorepo

Use **pnpm** with workspaces and **Turborepo** for monorepos:

```json
// package.json (root)
{ "packageManager": "pnpm@9.0.0" }
```

```bash
pnpm install          # install all workspaces
pnpm -F myapp dev     # run command in specific workspace
turbo build           # cached parallel builds
```

Monorepo layout: `packages/` for shared libs, `apps/` for deployable services.

### TypeScript Configuration

Enable strict additional flags in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "paths": { "@/*": ["./src/*"] }
  }
}
```

Use **path aliases** over deep relative imports:

```typescript
import { UserService } from '@/services/user'   // Good
import { UserService } from '../../../services/user'  // Avoid
```

### Function Style

Prefer `function` declarations for top-level named functions (better stack traces, hoisting):

```typescript
// Good — top-level named function
function processOrder(order: Order): Result { ... }

// Good — arrow for callbacks and class methods
const sorted = orders.sort((a, b) => a.createdAt - b.createdAt)
```

### Testing Tooling

- Test runner: **Vitest** (not Jest)
- HTTP mocking: **msw** (Mock Service Worker) — do not mock `fetch`/`axios` directly
- Pre-commit: **lint-staged** + **husky**

```bash
pnpm add -D vitest msw lint-staged husky
```

### CI Quality Gates

All of these must pass before merge:
- ESLint (strict `@typescript-eslint/recommended-type-checked`) — **zero warnings** policy
- Prettier formatting check
- `pnpm audit` (fail on HIGH/CRITICAL CVEs)
- Dependency licence check: **prohibit GPL/AGPL/LGPL** in production dependencies (use `license-checker`)

### Observability

Instrument with OpenTelemetry SDK:

```typescript
import { NodeSDK } from '@opentelemetry/sdk-node'
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http'

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({ url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT }),
  instrumentations: [getNodeAutoInstrumentations()],
})
sdk.start()
```
