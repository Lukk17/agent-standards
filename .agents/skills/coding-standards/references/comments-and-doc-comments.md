# Comments and Doc Comments

Contents:

- [Comments](#comments)
- [Doc Comments](#doc-comments)

The full comment and doc-comment rules from SKILL.md, with the reasoning and the TSDoc pass, fail and best forms that the language skills point to. Load this file before writing or reviewing any comment or doc comment.

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
