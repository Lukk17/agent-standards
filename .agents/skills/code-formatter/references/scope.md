# Scope

Companion reference for the [code-formatter](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing a new source file in Dart, Java or Python
- Editing a file already written in this style
- Reviewing a branch or pull request and flagging readability problems
- The user says "format this function", "why is this hard to read", "clean up the spacing here", or "break this
  method chain up"

The rules cover the reading flow inside a function body: braced control-flow exits, blank lines between phases, comments above the line, doc comments on their declaration, and chain breaks where no formatter owns them.

---

### When not to activate

- Naming, SOLID, immutability, error handling and architecture, use `coding-standards`
- Deciding whether a comment or a doc comment should exist and what it says, use `coding-standards`
- Language-specific idiom and typing in Java, use `java-coding-standards`
- Language-specific idiom and typing in Python, use `python-patterns`
- Language-specific idiom in Go, use `golang-patterns`
- Auto-formatting an unrelated file the project has not adopted this style for
- Human-facing markdown rather than source code, use `markdown-writer`

---

### Related skills

- `coding-standards` owns the engineering floor: SOLID, DRY, KISS, YAGNI, naming, error handling, architecture
- `java-coding-standards` owns Java idiom, Lombok, Optional, streams and Javadoc discipline
- `python-patterns` owns Python idiom, typing and package layout
- `golang-patterns` owns Go idiom and error conventions
- `dart-flutter-patterns` owns Dart and Flutter structure above the level of a function body
- `code-reviewer` owns the review pass where these rules get applied to somebody else's diff
