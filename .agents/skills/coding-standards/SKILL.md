---
name: coding-standards
description: 'The cross-language engineering floor: SOLID, DRY, naming, errors, layering, comments. Use when the user says "review this for quality" or "should this have a comment". Not for a diff review, use `code-reviewer`.'
metadata:
  version: "1.1.0"
---

# Coding Standards

The shared floor every project stands on, stated without a language or a framework. A framework skill extends it and never contradicts it.

---

### When not to activate

- Layout inside a function body, use `code-formatter`.
- One language's or framework's idiom, use its own skill, such as `java-coding-standards` or `react-patterns`.

---

### Rules

1. Core principles. KISS and YAGNI win until a second real use case. SOLID as heuristics: abstract only at a boundary you must swap or test. DRY is one source of truth, never a merge of lookalikes that change for different reasons. Prefer composition, immutable data and pure functions.
2. Naming and control flow. Self-explaining names, verb-noun functions, is/has/can booleans, named constants, tunables in configuration, guard clauses, annotated public signatures, short single-purpose functions, English only. The default formatter and linter run in CI and settle layout.
3. Functional pipelines. Prefer filter, map and aggregate over a loop with an accumulator, unless side effects, early exit or clarity favour the loop.
4. Error handling and logging. Never swallow an exception. Catch locally only to translate into a domain error with the cause chained, otherwise a central handler. One error shape, RFC 9457 problem details from `api-design` on HTTP, leaking nothing internal. One structured logging abstraction with a correlation identifier, never a secret or personal data.
5. Architecture. Business logic apart from framework, I/O and storage, dependencies pointing toward the core, constructor injection. Validate untrusted input once at the boundary into a typed value. Model state as named states, never a bag of flags.
6. Feature flags. Risky work goes behind a flag, not a long-lived branch: owned, dated for removal, off by default, read from configuration, checked once at the feature edge, deleted once shipped.
7. Decisions. Record a significant design decision outside source files, using `architecture-decision-records`.
8. Performance. Measure first, then fix the one real bottleneck, using `performance-optimization`.
9. Test structure. Set up, one action, assert the outcome, named for behaviour and condition, the bare Given, When and Then markers the only comments, using `tdd-workflow`.
10. Code smells. A long function, deep nesting, a magic number or a block that needs a comment gets restructured, not commented.
11. Size. A class, module, component or test file past about 300 lines is split by responsibility.

---

### Comments

Default to none. Add one only for a non-obvious why: a hidden invariant, a workaround with a stable external reference such as a CVE, or surprising behaviour. A deliberate gap requires a ticketed marker, `// TODO(TICKET-001): <what is missing>`. Banned: a ticket, PR or review number in place of the reasoning, a divider banner, a section label, a file-header comment.

---

### Doc Comments

The one canonical doc-comment rule. A language skill adds only its delta. Tag names use the JSDoc spelling.

Default to none, except one line per exported symbol of a published library or SDK. Prose is capped at five lines, usually one. A tag line is always one line. The four rules for the prose and the tags are in [comments-and-doc-comments.md](references/comments-and-doc-comments.md#doc-comments).

---

### Reference files

| Open | When |
|---|---|
| [principles-in-depth.md](references/principles-in-depth.md) | A rule in full, with its pass and fail form |
| [comments-and-doc-comments.md](references/comments-and-doc-comments.md) | Writing or reviewing a comment or a doc comment |
| [code-smells.md](references/code-smells.md) | Naming a structural problem and its repair |
| [TypeScript](references/typescript-examples.md), [Dart](references/dart.md), [Java](references/java.md), [Python](references/python.md) | A worked example in that language |
| [checklist.md](references/checklist.md) | Before calling a change done |
