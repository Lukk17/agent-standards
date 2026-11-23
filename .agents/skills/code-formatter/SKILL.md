---
name: code-formatter
description: 'Blank lines, braces and comment placement in Dart, Java and Python function bodies. Use when the user says "format this function" or "clean up the spacing here". Not for what a comment says, use `coding-standards`.'
metadata:
  version: "1.1.0"
---

# Code Formatter

Formatting rules that optimise for one thing: the next reader locating a function's control-flow exits and its async phase transitions in a single scan. They add what the language's default formatter leaves to the author, mostly blank lines and braces. Where the project runs that formatter and it rewrites a construct, its output wins and the rule yields. Apply them only to a file already written in this style, or when the user asked for the conversion, never to an unrelated file the project has not adopted this style for.

---

### When not to activate

- Naming, SOLID, error handling, architecture, and whether a comment or a doc comment should exist, use `coding-standards`.
- Language idiom and typing, use `java-coding-standards`, `python-patterns` or `golang-patterns`.
- Human-facing markdown rather than source code, use `markdown-writer`.

---

### Rules

1. Brace every inline exit. A `return` or `throw` never shares a line with its `if`. Braced, body on its own indented line.
2. Blank line after a wrapped signature. When a method, constructor or record parameter list wraps onto several lines, a blank line follows the opening brace, so the end of the signature and the start of the body are visually distinct.
3. Empty lines around try, catch and finally. A `try` is a control-flow landmark, so it gets a blank line before it and after it.
4. Empty line above a standalone async call. A hand-off to network or disk is a phase transition and reads as its own beat. Not for an await inside an assignment.
5. Empty line above a closing return. A `return` ending a multi-statement block gets a blank line above it. Not for single-expression bodies.
6. Blank line below a return inside a try with clauses. The blank line marks the seam between the happy path and the failure or cleanup clauses.
7. Empty line above an operation-terminating call. A call that ends a phase, such as a dismiss, a send, a publish or a navigation, separates from the arithmetic that set it up.
8. Comments above the line, never trailing. A trailing comment gets truncated by line length and forces horizontal scrolling.
9. Doc comments sit on their declaration. No blank line between the block and what it documents, and no tag hard-wrapped to fit a width.
10. One concept per blank-separated paragraph. Related lines stay together with no blank between them, a topic change gets exactly one. Two blanks means extract a method.
11. One chain step per line. Only where the project's formatter does not own line breaking. Where one does, its output wins and this rule does not apply.
12. Single-expression bodies stay on one line. The blank-line rules govern blocks. Do not expand an arrow function or a one-line definition to satisfy them.

---

### Reference files

| Open | When |
|---|---|
| [rules-in-depth.md](references/rules-in-depth.md) | A rule's full body and reasoning, and what the skill leaves to the formatter |
| [dart.md](references/dart.md) | The code is Dart: the wrong and right form of each rule |
| [java.md](references/java.md) | The code is Java: the wrong and right form of each rule, and all rules applied to one method |
| [python.md](references/python.md) | The code is Python: the wrong and right form of each rule |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job |
| [checklist.md](references/checklist.md) | Before calling a formatting pass done |
