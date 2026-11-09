---
name: quality-loop
description: 'The measure-and-fix loop for agent-written code, after Robert C. Martin: CRAP scores from crapper, duplicate pairs from dryer and surviving mutants from mutator, fixed worst first until clean or three rounds. Use when the user says "clean up this code", "run the quality loop", "measure the CRAP scores" or "find surviving mutants". Not for writing the tests of a new feature, use `tdd-workflow`.'
---

# Quality Loop

Measure the code, fix the worst mess first, and measure again. The method and the three measuring tools are the work of Robert C. Martin (Uncle Bob): [crapper](https://github.com/unclebob/crapper) scores every function by complexity and coverage, [dryer](https://github.com/unclebob/dryer) lists functions with the same shape, and [mutator](https://github.com/unclebob/mutator) plants small bugs and reports the ones the tests miss. A project carries his tools unchanged under `.metrics/tools/`, with a wrapper that runs them, and keeps the scores in `.metrics/`.

| Task | Open |
|---|---|
| Running `measure`, `mutate --changed` and `summary`, the exit codes, the first run, getting the tools into a project, Windows, what to commit | [references/running-the-tools.md](references/running-the-tools.md) |
| Reading `.metrics/crap.edn`, `.metrics/dry.edn` and `.metrics/mutate/`, and the bands that decide what must be fixed | [references/reading-the-scores.md](references/reading-the-scores.md) |
| Fixing each kind of mess, per-language notes, and the before and after report | [references/fixing-the-worst.md](references/fixing-the-worst.md) |

---

### When to activate

- A feature is done and its code needs measuring before review, or the user says "run the quality loop"
- The user says "clean up this code", "measure the CRAP scores", "find surviving mutants" or "find duplicated code"
- A review cites a high CRAP score, a surviving mutant or a duplicate pair from `.metrics/`
- The project is in Clojure, Java with Maven or Gradle, Go, TypeScript or JavaScript, Rust, or Python

---

### When not to activate

- Writing the tests of a new feature first, use `tdd-workflow`
- Deciding whether two similar blocks are one rule, use `review-duplication`
- Reviewing a change without changing it, use `code-reviewer`, which reads `.metrics/` but never runs the tools
- Kotlin, C#, PHP, Dart or any other language the tools do not read: report it as not measured
- Profiling a slow path, use `performance-optimization`

---

### Rules

1. Run the tools only through the wrapper, `.metrics/tools/run` on Linux and macOS and `.metrics\tools\run.cmd` on Windows. Never edit anything under `.metrics/tools/crapper`, `dryer` or `mutator`, which is Robert C. Martin's code copied unchanged.
2. Start with `measure`, a full run of all three tools, and read the result with `summary`. Never run crapper on changed files only: a partial run replaces `.metrics/crap.edn` with a subset.
3. When `.metrics/tools/run` is missing, get the tools before anything else, the way the running reference says. Never write a tool of your own in their place.
4. Fix the worst first: a CRAP score over 30, then every surviving mutant in code the change touched, then the duplicate pairs at or above 0.82.
5. Fix a high CRAP score by splitting or simplifying the function, or by adding the test that covers it, whichever the function needs. Never raise coverage with a test that asserts nothing.
6. Kill a surviving mutant with a test that fails on the mutated code and passes on the real code. Never weaken, skip or delete a test to make a score look better.
7. Merge a duplicate pair only when both copies encode the same rule and change for the same reason. `review-duplication` and `coding-standards` decide, and a pair that only looks alike stays as it is.
8. After each round of fixes, run `mutate --changed` for the mutants and `measure` for the full scores, and keep the project's own tests green.
9. Stop when nothing is over the limits, or after three rounds, and report what is left with the reason it is left.
10. Commit the fixes and the full-run scores in `.metrics/` only when the caller asked for commits, with a JaCoCo block the wrapper added to a Gradle build file in its own commit. Otherwise leave them staged for the caller.

---

### Limits

| Score | Limit |
|---|---|
| CRAP | Over 30 must be fixed. A function the change touched aims under 10 |
| Surviving mutants | None in code the change touched |
| Duplicate pairs | Every pair at or above 0.82 is reviewed, not merged blindly |

---

### Related skills

- `tdd-workflow` owns the red-green loop each new test follows
- `coding-standards` owns how a function is split and named
- `review-duplication` owns the call on whether a duplicate pair is one rule
- `code-reviewer` reads `.metrics/` and turns the worst scores into review findings

---

### Checklist

- [ ] The wrapper ran `measure` and `summary`, and no tool ran on its own
- [ ] Nothing under `.metrics/tools/crapper`, `dryer` or `mutator` changed
- [ ] Every CRAP score over 30 was fixed or reported with its reason
- [ ] No surviving mutant is left in code the change touched, or each one left is reported
- [ ] Every duplicate pair at or above 0.82 was reviewed, and merged only when both copies are one rule
- [ ] No test was weakened, skipped or deleted
- [ ] The project's own tests pass after the last round
- [ ] The full-run scores in `.metrics/` are committed when the caller asked, staged otherwise, and the report shows them before and after
