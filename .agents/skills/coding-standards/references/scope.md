# Scope

Companion reference for the [coding-standards](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Starting a module, reviewing for quality, or refactoring, as in "review this for quality" or "refactor to our conventions"
- Enforcing naming, structure, file size or control-flow consistency, or setting up linting and type-checking
- Deciding whether a comment belongs at all, as in "should this have a comment"
- Deciding whether to introduce an abstraction or merge two similar blocks

The floor covers SOLID as heuristics under KISS and YAGNI, DRY without coincidental merges, naming, guard clauses, one error shape, layering, feature flags, and when a comment or doc comment belongs.

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

### Related skills

- `code-reviewer` owns the structured review of a diff or a pull request, measured against this floor
- `code-formatter` owns blank lines, chain breaking and where a comment sits inside a Dart, Java or Python function
  body, and leaves brace placement and indent width to each language's default formatter. Other languages follow the
  default formatter for all of it
- `react-patterns` owns React composition, hooks, state and rendering
- `backend-patterns` and `api-design` own service structure, endpoints and contracts
- `api-design` owns the HTTP error shape, RFC 9457 problem details, that the error rule points to
- `review-duplication` applies the DRY rule, coincidental lookalikes included, to a change under review
- `hexagonal-architecture` owns ports, adapters and dependency direction in depth
- `observability-and-logging` owns structured logging, tracing, metrics and health
- `performance-optimization` owns profiling and the measure-first loop
- `architecture-decision-records` owns the decisions this hub keeps out of source files
- `tdd-workflow`, `python-patterns`, `golang-patterns` and `springboot-patterns` own the testing playbook
- `java-coding-standards`, `python-patterns`, `golang-patterns` and `dart-flutter-patterns` own per-language idiom
- `springboot-patterns` and every other stack skill own stack-specific patterns. Wherever a narrower skill in this repository already covers the stack in question, that skill is the one to use
