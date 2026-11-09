# Fixing the worst

How to fix each kind of mess the tools report, the language notes that change how, and the report that closes the loop.

---

### The round

1. `measure`, then `summary`. Write down the before numbers: functions over 30, from 10 to 30, surviving mutants, duplicate pairs.
2. Pick the worst item that is in scope: the change under work, or the whole project when the user asked for a cleanup.
3. Fix it, run the project's own tests, then `mutate --changed`.
4. Repeat with the next item. When the round's list is done, `measure` again.
5. Stop when nothing is over the limits, or after three rounds.

---

### A high CRAP score

Read the function first. Complexity and missing coverage need different fixes:

- High complexity at good coverage: split the function along its decisions, replace a branch cascade with a lookup or guard clauses, and keep each piece named for what it decides. The tests already pin the behaviour, so they stay green through the split.
- Good complexity at low coverage: write the tests the function lacks, one per behaviour, through `tdd-workflow`.
- Both: add the tests first, so the split happens under green, then split.

A test that only calls the function, or asserts something that cannot fail, raises coverage without proving anything, and mutator will show it.

---

### A surviving mutant

The mutant shows the exact change no test noticed, such as `>= -> >` on one line. Write the test that tells the two apart: for `age >= 18`, a test with an age of exactly 18. Run it against the real code, where it passes, and let `mutate --changed` confirm the mutant is now killed.

A mutant that cannot change behaviour, such as a different constant in a log message, is equivalent. Report it with the reason rather than writing a test that pins a log line.

---

### A duplicate pair

dryer compares shape, not meaning. Two copies are one rule when they change for the same reason. Then extract one function and call it from both places. Two copies that only look alike, such as an order total and a refund total that happen to share a loop today, stay apart. `review-duplication` makes the call, and a pair left apart is reported with its reason.

---

### Language notes

| Language | Tests and coverage the tools use | Notes |
|---|---|---|
| Python | coverage.py around pytest, or unittest, with the project's `.venv` | Add the test under the project's test folder. The wrapper creates `.venv` when it is missing |
| Java, Maven | JaCoCo through Maven, `mvn test` per mutant | Mutants take seconds each, because every worker compiles |
| Java, Gradle | `gradle test jacocoTestReport`, then `gradle --rerun-tasks test` per mutant | Needs the JaCoCo block the wrapper adds once |
| TypeScript, JavaScript | `npm run coverage`, else Vitest's own report, else c8 around `npm test` | A `coverage` script must write LCOV into `coverage/` |
| Go | `go test ./... -coverprofile` | Table-driven cases kill boundary mutants cheaply |
| Rust | cargo-llvm-cov, else cargo-tarpaulin | crapper installs cargo-llvm-cov when neither is present |
| Clojure | `clj -M:cov --lcov` and the `:test` or `:spec` alias | Needs a `:cov` alias in `deps.edn` |

Kotlin, C#, PHP, Dart and other languages are not measured. Say so in the report rather than measuring nothing.

---

### The report

End the loop with the numbers before and after, and every item left with its reason:

```markdown
## Quality loop: <scope>

| Score | Before | After |
|---|---|---|
| Functions over CRAP 30 | 3 | 0 |
| Functions from CRAP 10 to 30 | 5 | 2 |
| Surviving mutants in changed code | 7 | 0 |
| Duplicate pairs at or above 0.82 | 2 | 1 |

### Left as it is
- `src/billing/refund.py:12` and `src/billing/order.py:30`, duplicate 0.91: different rules that share a loop today.

### Rounds
- 2 rounds. Scores committed in `.metrics/`.
```
