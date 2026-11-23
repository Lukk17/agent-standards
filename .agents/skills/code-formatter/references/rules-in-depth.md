# Formatting Rules in Depth

Contents:

- [Brace every inline exit](#brace-every-inline-exit)
- [Blank line after a wrapped signature](#blank-line-after-a-wrapped-signature)
- [Empty lines around try, catch and finally](#empty-lines-around-try-catch-and-finally)
- [Empty line above a standalone async call](#empty-line-above-a-standalone-async-call)
- [Empty line above a closing return](#empty-line-above-a-closing-return)
- [Blank line below a return inside a try with clauses](#blank-line-below-a-return-inside-a-try-with-clauses)
- [Empty line above an operation-terminating call](#empty-line-above-an-operation-terminating-call)
- [Comments above the line, never trailing](#comments-above-the-line-never-trailing)
- [Doc comments sit on their declaration](#doc-comments-sit-on-their-declaration)
- [One concept per blank-separated paragraph](#one-concept-per-blank-separated-paragraph)
- [One chain step per line](#one-chain-step-per-line)
- [Single-expression bodies stay on one line](#single-expression-bodies-stay-on-one-line)
- [What this skill does not cover](#what-this-skill-does-not-cover)

The full body of each formatting rule, with its reasoning. The wrong and right form of every rule is in the file of the
language in front of you: [dart.md](dart.md), [java.md](java.md) or [python.md](python.md). Load this file when
applying or reviewing a specific rule, or when a rule's intent is unclear from its one-line summary in SKILL.md.

The rules add what the default formatter of each language leaves to the author, mostly blank lines and braces: dart
format for Dart, google-java-format for Java, ruff format and black for Python. Where the project runs one of those
formatters and it rewrites a construct, its output wins and the rule yields.

---

### Brace every inline exit

A control-flow exit should never share a line with its condition, as in `if (x) return y;` or `if (x) throw z;`. The
reader's eye should land on a `return` or `throw` as a line, not as the tail of an `if`. Multi-line, braced, body
indented.

---

### Blank line after a wrapped signature

When a method, constructor or record parameter list is too long for one line and wraps, the last parameter line and the first body line sit at nearly the same indent, and the reader cannot see where the signature ends and the implementation starts. Put one blank line straight after the opening brace whenever the parameter list wraps. A signature on one line needs no blank line, and a record with no body has nothing to separate. Where the project's formatter removes the line, its output wins, as with every rule here.

---

### Empty lines around try, catch and finally

A `try` block is a control-flow landmark: it tells the reader "things can go wrong here." Give it room to breathe
before and after so the eye treats it as a phase, not buried text.

---

### Empty line above a standalone async call

When an async call marks a phase transition in a function (setup, then I/O, then cleanup), give it a blank line
above. The reader's eye should register "now we hand off to the network/disk" as a distinct beat. This applies to
standalone awaits and other significant async I/O, not awaits embedded in an assignment expression.

---

### Empty line above a closing return

When a function does several things and then returns, the `return` gets a blank line above so it reads as "and now
hand back the result" rather than blending into the last statement. Doesn't apply to single-statement bodies, arrow
functions, or one-line `def`s. The blank-line rules apply to blocks.

---

### Blank line below a return inside a try with clauses

When a `try` block ends with `return X;` and is followed by a `catch` or `finally` clause, leave a blank line between
the `return` and the closing `}` of the try. The blank line marks the hand-off from the happy-path body to the
failure / cleanup clauses, so the reader's eye can see the seam.

The same rule applies to a `throw` that ends a `try` body when a `catch` / `finally` follows it. The worked wrong and
right form is in [java.md](java.md#blank-line-below-a-return-inside-a-try-with-clauses).

---

### Empty line above an operation-terminating call

Calls that end a phase get a blank line above. The eye should see "the act" separated from the local-var arithmetic
that prepared for it. Each language file lists the operation-terminators of its language.

---

### Comments above the line, never trailing

Trailing comments get truncated by long lines and force horizontal scrolling. A comment is a sentence about the next
thing the reader is about to see, so write it on its own line, above.

Exception: short tag comments tied to an issue tracker (e.g. `// TODO(TICKET-001): drop after Q3`) sometimes trail by
team convention. Even then, prefer the comment above when there's room.

---

### Doc comments sit on their declaration

Whether a doc comment should exist at all, and what its prose and tags may say, is owned by `coding-standards`. This
rule covers only where the block sits and how its lines break.

1. The block sits directly on the declaration it documents. No blank line between the two, ever, and no doc comment on
   a line of its own floating above an annotation stack.
2. Every tag line is one physical line, whatever the language calls it. Each language file names its tags. A tag that
   does not fit on one line gets shortened or dropped, never wrapped to fit a width, which is the same rule this skill
   applies to code.

---

### One concept per blank-separated paragraph

Inside a function body, related lines stick together with no blank between them, and a topic transition gets one blank.
Two blank lines anywhere inside a function body is a smell, so extract a method.

In the example each language file gives, each paragraph reads as a phase: capture context, build and persist,
mounted-guard, invalidate dependents, exit.

---

### One chain step per line

Method chains break before each `.`. Fluent / functional pipelines (filter, map, reduce, take, toList, collect) read
top-down, one transformation per line. Easier to diff, easier to insert or remove a step.

This rule applies only where the project's formatter does not own line breaking. A formatter that owns it reflows a
chain to fit the line, joining a short one back onto a single line, so where one runs, its output wins and this rule
does not apply. Writing against the formatter only produces a diff it reverts on the next save and a `--check` failure
in CI. Each language file names the formatters of its language.

The prefer chains over loops part is a coding-standards rule, not a formatter one. The formatter point here is:
when you do chain and no formatter owns the wrapping, one step per line.

---

### Single-expression bodies stay on one line

The blank-line rules apply to blocks, not arrow functions or one-line `def`s. Don't expand a pure transformation
into a multi-line body just to satisfy a "blank line above return" rule that doesn't apply.

---

### What this skill does not cover

- Naming conventions, member ordering and import ordering, which vary per language. Use the language style guide and
  `coding-standards`
- Line length caps, which stay readable by extracting locals rather than wrapping. Each project sets its own budget
- Trailing commas, brace placement, indent width and line breaking, which the default formatter for each language owns
  and this skill does not override
