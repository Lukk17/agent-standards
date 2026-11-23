# Scope

Companion reference for the [quality-loop](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

The loop is for agent-written code: measure it, fix the worst first, and stop when it is clean or after three rounds. It applies when:

- A feature is done and its code needs measuring before review, or the user says "run the quality loop"
- The user says "clean up this code", "measure the CRAP scores", "find surviving mutants" or "find duplicated code"
- A review cites a high CRAP score, a surviving mutant or a duplicate pair from `.metrics/`
- The project is in Clojure, Java with Maven or Gradle, Go, TypeScript or JavaScript, Rust, or Python

Kotlin, C#, PHP, Dart or any other language the tools do not read: report it as not measured.

---

### When not to activate

- Writing the tests of a new feature first, use `tdd-workflow`
- Deciding whether two similar blocks are one rule, use `review-duplication`
- Reviewing a change without changing it, use `code-reviewer`, which reads `.metrics/` but never runs the tools
- Kotlin, C#, PHP, Dart or any other language the tools do not read: report it as not measured
- Profiling a slow path, use `performance-optimization`

---

### Related skills

- `tdd-workflow` owns the red-green loop each new test follows
- `coding-standards` owns how a function is split and named
- `review-duplication` owns the call on whether a duplicate pair is one rule
- `code-reviewer` reads `.metrics/` and turns the worst scores into review findings
