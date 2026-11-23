# Scope

Companion reference for the [dart-flutter-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing any Dart or Flutter code, including plain Dart packages with no widgets.
- The user says "build a Flutter screen", "why does my Column overflow", "set up GoRouter with an auth guard", "parse this JSON without jank", or "write a widget test for this form".
- Structuring a new Flutter project, or refactoring one whose layers have blurred.
- Debugging a layout overflow, a jank frame, a rebuild storm, or a `setState() called after dispose()` crash.
- Wiring navigation, deep links, forms, HTTP clients, local databases, or platform channels.
- Adding tests, localization, accessibility semantics, or a size budget to an existing app.
- Setting up a Linux, macOS, or Windows machine to build Flutter.

---

### When not to activate

- Language-neutral design rules such as SOLID, DRY, naming, and error-handling shape. Use `coding-standards`.
- Blank lines, control-flow exits and chain breaking inside a Dart function body. Use `code-formatter`, which covers Dart, Java and Python only. Any other language follows its language skill or its default formatter.
- The red, green, refactor loop itself rather than Flutter test mechanics. Use `tdd-workflow`.
- WCAG conformance for a web page or a non-Flutter front end. Use `web-accessibility`.
- Reviewing a diff or a pull request for defects. Use `code-reviewer`.
- Measuring and fixing backend or query latency behind the app. Use `performance-optimization`.

---

### Related skills

- `coding-standards` for the cross-language engineering floor these patterns sit on.
- `code-formatter` for reading flow inside function bodies in Dart, Java and Python, and no other language.
- `tdd-workflow` for the red, green, refactor discipline behind [references/testing.md](testing.md).
- `web-accessibility` for WCAG conformance when a Flutter web build sits inside a wider site.
- `code-reviewer` for reviewing a Dart diff against all of the above.
- `build-dependency-management` for pinning and admitting the packages named in these references.
