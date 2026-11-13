---
name: coding-standards
description: 'The cross-project engineering floor: SOLID as heuristics under KISS and YAGNI, DRY without coincidental merges, naming, guard clauses, one error shape, layering, feature flags, and when a comment or doc comment belongs. Use when the user says "review this for quality", "refactor to our conventions", or "should this have a comment". Not for stack-specific patterns, use `springboot-patterns`.'
metadata:
  version: "1.0.0"
---

# Coding Standards

The shared floor every project stands on, stated without reference to a language or a framework. A framework skill extends this floor and never contradicts it, so when the two disagree, this hub is the one that needs fixing.

| Task | Open |
|---|---|
| A rule's full statement, its reasoning, or its pass and fail form | [principles-in-depth.md](references/principles-in-depth.md) |
| Writing or reviewing a comment or a doc comment, with the TSDoc pass, fail and best forms | [comments-and-doc-comments.md](references/comments-and-doc-comments.md) |
| Wanting a rule shown as concrete TypeScript rather than stated | [typescript-examples.md](references/typescript-examples.md) |
| Reviewing for structural problems and naming the shape you found | [code-smells.md](references/code-smells.md) |
| Converting a loop into a pipeline, or deciding not to | [functional-pipelines.md](references/functional-pipelines.md) |

---

### When to activate

- Starting a module, reviewing for quality,, or refactoring, as in "review this for quality" or "refactor to our conventions"
- Enforcing naming, structure, file size or control-flow consistency, or setting up linting and type-checking
- Deciding whether a comment belongs at all, as in "should this have a comment"
- Deciding whether to introduce an abstraction or merge two similar blocks

---

### When not to activate

- React composition, hooks, state and rendering, use `react-patterns`
- Backend service structure, endpoints and data access, use `backend-patterns` or `api-design`
- Blank lines, chain breaking and comment placement in a Dart, Java or Python function body, use `code-formatter`. Other languages, braces and indent width follow the default formatter
- The full testing playbook rather than the principle, use `tdd-workflow` or the language test skill
- Logging and observability beyond the one rule here, use `observability-and-logging`
- Ports and adapters in depth, use `hexagonal-architecture`
- Any case where a narrower skill in this repository already covers the stack in question

---

### Rules

1. Core principles. KISS and YAGNI win until a second real use case. SOLID as heuristics, with an abstraction only at a boundary you must swap or test. DRY is one source of truth, never a merge of lookalikes that change for different reasons; extract on the third occurrence. FIRST tests, composition, immutability, pure functions.
2. Naming and control flow. Self-explaining names with no cryptic abbreviation, descriptive type parameters (`TRow`, not a doc comment explaining `T`), verb-noun functions, is/has/can booleans, named constants for fixed values and configuration for tunables, guard clauses, annotated public signatures, short single-purpose functions, English only. The default formatter and linter run in CI and settle layout.
3. Functional pipelines. Prefer filter, map and aggregate over a loop with a cascade and an accumulator, unless side effects, early exit or clarity favour the loop.
4. Error handling and logging. No swallowed exception, no empty catch. Catch locally only to translate into a domain error with the cause chained, otherwise a central handler. One error shape, RFC 9457 problem details from `api-design` on HTTP, leaking nothing internal. One structured logging abstraction with a correlation identifier, never a secret or personal data.
5. Architecture. Business logic apart from framework, I/O and storage, dependencies pointing toward the core, constructor injection. Validate untrusted input once at the boundary into a typed value, and model state as one of several named states, never a bag of flags.
6. Feature flags. Risky work goes behind a flag, not a long-lived branch. Each flag has an owner and a removal date, defaults to off, is read from configuration, is checked once at the feature edge, and is deleted once shipped.
7. Architecture decision records. Record every significant design decision outside source files, using `architecture-decision-records`.
8. Performance. Measure before optimising and fix the one real bottleneck, using `performance-optimization`.
9. Test structure. Set up, one action, assert the outcome, named for behaviour and condition, with the bare Given, When and Then markers as the only comments, using `tdd-workflow`.
10. Code smells. Long functions, deep nesting, magic numbers and blocks that need a comment call for restructuring, not a comment.
11. Size. A class, module, component or test file past about 300 lines does several jobs, so split it by responsibility.

---

### Comments

Default to no comments. Add one only for a non-obvious why: a hidden invariant, a workaround with a stable external reference such as a CVE or an RFC section, or surprising behaviour. A deliberate gap requires a ticketed marker, `// TODO(TICKET-001): <what is missing>`, and a gap without one is a defect. A ticket, PR or review-section number cited instead of the reasoning is banned, as are divider banners, section labels and file-header comments.

---

### Doc Comments

This is the one canonical doc-comment rule. Each language skill points here and adds only its delta, such as the tag spelling or what its doc tool renders. Tag names use the JSDoc spelling.

- Default to none. The exception is the exported surface of a published library or SDK: one line per exported symbol. `golang-patterns` widens it to every exported Go name, and `powershell` to `.SYNOPSIS`, one `.PARAMETER` per parameter and one `.EXAMPLE` on every exported function, where the one-line cap overrides rule 2.
- Prose capped at five lines, usually one. Every tag line capped at one line, with no exception.
- Rule 1, prose: one sentence on what it does, then only what the signature cannot say.
- Rule 2, `@param` only for units, nullability, a valid range or ownership, never a restated type.
- Rule 3, `@returns` only when non-obvious.
- Rule 4, `@throws` always, for every error a caller can act on.
- Past five lines only for a contract that cannot be shorter, justified in review.

---

### Related skills

- `review-duplication` applies the DRY rule to a change under review
- `tdd-workflow`, `python-patterns`, `golang-patterns` and `springboot-patterns` own the testing playbook
- `java-coding-standards`, `python-patterns`, `golang-patterns` and `dart-flutter-patterns` own per-language idiom

---

### Checklist

- [ ] Every name reveals intent, no single letters, no bare nouns for functions
- [ ] Public signatures annotated, locals typed the way the language's idiom says
- [ ] No magic number or string outside a named constant
- [ ] Guard clauses used instead of deep nesting
- [ ] No file past about 300 lines, and no divider banner or section-label comment
- [ ] No abstraction without a second real use case or a boundary that needs swapping or testing
- [ ] No merge of two blocks that only look alike and change for different reasons
- [ ] No swallowed exception, no empty catch, causes chained
- [ ] Errors returned in one structured shape, problem details on HTTP, no internal detail leaked
- [ ] Untrusted input validated once at the boundary into a typed value
- [ ] Business logic separable from framework, input and output, and storage
- [ ] State modelled as one of several named states, not a bag of flags
- [ ] Every feature flag has an owner and a removal date
- [ ] Every deliberate gap carries a ticketed task marker
- [ ] No comment states what the code already says, and the exported surface of a published library is documented
