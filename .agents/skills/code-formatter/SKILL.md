---
name: code-formatter
description: 'Visual formatting and reading flow inside function bodies across Dart, Java, Python, Kotlin, TypeScript and Go: braced control-flow exits, blank lines marking phase transitions, comments above the line they describe, doc comments earning their place, one chain step per line. Use when you say "format this function", "why is this hard to read", "clean up the spacing here", or "break this method chain up". Not for naming and error handling, use `coding-standards`.'
---

# Code Formatter

Formatting rules that optimise for one thing: the next reader locating a function's control-flow exits and its async
phase transitions in a single scan. They deliberately diverge from what gofmt, dart format, black and
google-java-style produce in specific places, which each rule names.

| Task | Open |
|---|---|
| Applying or reviewing one rule, with wrong and right forms in every language it covers | [rules-by-language.md](references/rules-by-language.md) |

---

### When to activate

- Writing a new source file in Dart, Java, Python, Kotlin, TypeScript or Go
- Editing a file already written in this style
- Reviewing a branch or pull request and flagging readability problems
- Deciding whether a comment or a doc comment should exist at all

---

### When not to activate

- Naming, SOLID, immutability, error handling and architecture, use `coding-standards`
- Language-specific idiom and typing in Java, use `java-coding-standards`
- Language-specific idiom and typing in Python, use `python-patterns`
- Language-specific idiom in Go, use `golang-patterns`
- Auto-formatting an unrelated file the project has not adopted this style for
- Human-facing markdown rather than source code, use `markdown-writer`

---

### The rules

Each rule below has its full body, its reasoning, and its wrong-and-right forms per language in
[rules-by-language.md](references/rules-by-language.md). Open that file before applying one you are unsure about.

| Rule | What it requires |
|---|---|
| Brace every inline exit | A `return` or `throw` never shares a line with its `if`. Braced, body on its own indented line |
| Empty lines around try, catch and finally | A `try` is a control-flow landmark, so it gets a blank line before and after, and so does each clause body |
| Empty line above a standalone async call | A hand-off to network or disk is a phase transition and reads as its own beat. Not for an await inside an assignment |
| Empty line above a closing return | A `return` ending a multi-statement block gets a blank line above it. Not for single-expression bodies |
| Blank line below a return inside a try with clauses | The blank line marks the seam between the happy path and the failure or cleanup clauses |
| Empty line above an operation-terminating call | A call that ends a phase, such as a dismiss, a send, a publish or a navigation, separates from the arithmetic that set it up |
| Comments above the line, never trailing | A trailing comment gets truncated by line length and forces horizontal scrolling |
| Doc comments earn their place | Default to none. Extract and rename first. When one survives, prose is capped at five lines and every tag line at one |
| One concept per blank-separated paragraph | Related lines stay together with no blank between them, a topic change gets exactly one. Two blanks means extract a method |
| One chain step per line | Break before each `.` in a fluent or functional pipeline, so a step can be added, removed or diffed on its own |
| Single-expression bodies stay on one line | The blank-line rules govern blocks. Do not expand an arrow function or a one-line definition to satisfy them |

---

### What the rules look like together

Pass:

```java
public Optional<Receipt> settle(Order order) {
    if (order.isEmpty()) {
        return Optional.empty();
    }

    var total = pricing.total(order);
    var payload = mapper.toPayload(order, total);

    var response = paymentClient.send(payload);

    logger.info("settled order {}", order.id());

    return Optional.of(Receipt.from(response));
}
```

Fail:

```java
public Optional<Receipt> settle(Order order) {
    if (order.isEmpty()) return Optional.empty();
    var total = pricing.total(order); // price it
    var payload = mapper.toPayload(order, total);
    var response = paymentClient.send(payload);
    logger.info("settled order {}", order.id());
    return Optional.of(Receipt.from(response));
}
```

The failing version is what most default formatters produce and leave alone. Nothing in it is wrong to a compiler.
It is harder to read because the exit, the network call and the return all sit at the same visual weight as the
local arithmetic around them.

---

### What this skill does not cover

- Naming conventions, member ordering and import ordering, which vary per language. Use the language style guide and
  `coding-standards`
- Line length caps, which stay readable by extracting locals rather than wrapping. Each project sets its own budget
- Trailing commas, brace placement and indent width, which the default formatter for each language owns and this
  skill does not override

---

### Related skills

- `coding-standards` owns the engineering floor: SOLID, DRY, KISS, YAGNI, naming, error handling, architecture
- `java-coding-standards` owns Java idiom, Lombok, Optional, streams and Javadoc discipline
- `python-patterns` owns Python idiom, typing and package layout
- `golang-patterns` owns Go idiom and error conventions
- `dart-flutter-patterns` owns Dart and Flutter structure above the level of a function body
- `code-reviewer` owns the review pass where these rules get applied to somebody else's diff

---

### Checklist

- [ ] No control-flow exit shares a line with its condition
- [ ] Blank lines mark the try, the async hand-off and the terminating call as distinct beats
- [ ] Every comment sits above the line it describes
- [ ] Every doc comment that survived is justified, five prose lines or fewer, one line per tag
- [ ] No two consecutive blank lines inside a function body
- [ ] Fluent chains break before each dot
- [ ] Single-expression bodies were left on one line
- [ ] The file was already in this style, or the user asked for the conversion
