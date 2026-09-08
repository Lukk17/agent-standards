---
name: springboot-verification
description: "Six-phase verification pipeline for a Spring Boot service: build, static analysis, tests with coverage, dependency and secret scanning, format gate, and diff review, ending in a go or no-go report. Use when you say \"verify this before I open the PR\", \"run the full check pipeline\", \"is this ready to deploy\", \"scan for CVEs and committed secrets\", or \"give me a verification report\". Not for writing the tests this pipeline runs, use `springboot-tdd`."
license: Apache-2.0
---

# Spring Boot Verification Loop

The command pipeline that decides whether a Spring Boot change is ready to leave your machine. It runs the gates
and reports the result, and it defers to `springboot-tdd` for what the tests themselves should look like.

---

### When to activate

- Before opening a pull request for a Spring Boot service.
- After a large refactor or a dependency upgrade.
- Before a deployment to staging or production.
- When somebody asks whether a change is ready, and the answer needs evidence.

---

### When not to activate

- Writing or restructuring the tests, use `springboot-tdd`.
- Reviewing the code itself for design and correctness, use `code-reviewer`.
- Fixing a security finding this pipeline surfaces, use `springboot-security`.
- Choosing or bumping the plugin versions the phases invoke, use `build-dependency-management`.
- Shipping the artifact once the report is green, use `deployment-patterns`.

---

### Run the phases in order and stop at the first hard failure

Each phase is cheaper than the one after it, so a broken build never burns a Testcontainers startup. Phases 1
through 4 and phase 6 are hard gates. Phase 5 is a gate only in projects that have adopted a formatter.

Pass: phase 1 fails, you fix the compilation error, and you restart from phase 1.

Fail: the build is broken so you skip ahead to the diff review and report "tests not run" as if it were a result.

---

### Phase 1: build

Maven:

```bash
mvn -T 4 clean verify -DskipTests
```

Gradle:

```bash
./gradlew clean assemble -x test
```

Pass: the artifact builds from a clean state.

Fail: a build that only succeeds incrementally, because the failure is hiding in a stale output directory.

---

### Phase 2: static analysis

Maven:

```bash
mvn -T 4 spotbugs:check pmd:check checkstyle:check
```

Gradle:

```bash
./gradlew checkstyleMain pmdMain spotbugsMain
```

Pass: zero findings at the severity the project treats as an error, per `java-coding-standards`.

Fail: findings acknowledged in the report and left in place, or a rule suppressed to clear the gate.

---

### Phase 3: tests and coverage

Maven:

```bash
mvn -T 4 verify
```

Gradle:

```bash
./gradlew test jacocoTestReport
```

Record the total test count, the pass and fail split, and line and branch coverage. The target is around 90% of
real logic.

Pass: the whole suite runs green and coverage clears the threshold on its own.

Fail: a failing test annotated `@Disabled` to get the phase green, or a coverage threshold lowered in the same
commit.

This skill defers to `springboot-tdd` for test shape. Anything about which slice a test belongs in, how to mock a
Spring bean, how to wire Testcontainers, or how to build test data lives there, and is not repeated here.

---

### Phase 4: security scan

Dependency vulnerabilities, Maven:

```bash
mvn org.owasp:dependency-check-maven:check
```

Dependency vulnerabilities, Gradle:

```bash
./gradlew dependencyCheckAnalyze
```

Committed credentials in the working tree:

```bash
grep -rnE "(password|secret|api[_-]?key)\s*[:=]\s*[\"'][^\"']+" src/ --include="*.java" --include="*.yml" --include="*.properties"
```

Credentials in history, where the tool is configured:

```bash
git secrets --scan
```

Two more greps catch the findings that show up most often in review.

```bash
grep -rn "System\.out\.print" src/main/ --include="*.java"
```

```bash
grep -rn "allowedOrigins.*\*" src/main/ --include="*.java"
```

Pass: no new CVE at or above the project's fail threshold, and no credential outside an environment variable or a
vault reference.

Fail: a CVE suppressed with no expiry and no ticket, or a hardcoded password explained away as test-only.

Anything this phase finds is fixed under `springboot-security`, not patched over here.

---

### Phase 5: format gate

```bash
mvn spotless:apply
```

```bash
./gradlew spotlessApply
```

Pass: the formatter runs and produces no diff, meaning the tree was already formatted.

Fail: a formatting run that rewrites files unrelated to the change, which buries the real diff in whitespace.

---

### Phase 6: diff review

```bash
git diff --stat
```

```bash
git diff
```

Read the whole diff before reporting. The gates cannot see an accidentally committed debug branch or a config
change nobody documented.

Pass: every changed file is one the task required, with no leftover debugging output, meaningful HTTP statuses,
transactions and validation where they belong, and config changes documented.

Fail: an unrelated reformat, a stray `System.out`, or a commented-out block left as a note to self.

---

### Report the result in this template

Keep the output identical every run so a reader can compare two runs at a glance.

```text
VERIFICATION REPORT
===================
Build:     [PASS/FAIL]
Static:    [PASS/FAIL] (spotbugs/pmd/checkstyle)
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (CVE findings: N)
Format:    [PASS/FAIL]
Diff:      [X files changed]

Overall:   [READY / NOT READY]

Issues to Fix:
1. ...
2. ...
```

Pass: every line carries a real measured value, and NOT READY when any gate failed.

Fail: READY declared with a phase marked "skipped", or a coverage number quoted from an earlier run.

---

### Re-run on a short loop during long sessions

Re-run the full pipeline after any significant change, and roughly every thirty to sixty minutes in a long
session. Between full runs, a fast loop of the test phase plus static analysis gives feedback without the wait.

Pass: failures surface minutes after the change that caused them.

Fail: one verification run at the end of a day's work, where the bisect space is now forty files wide.

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `springboot-tdd` | The shape and structure of every test this pipeline runs. |
| `springboot-security` | Fixing whatever phase 4 finds, and the release security checklist. |
| `java-coding-standards` | The static analysis rules phase 2 enforces. |
| `build-dependency-management` | Where the plugin versions in these commands are declared. |
| `code-reviewer` | Human-grade review of the diff phase 6 prints. |
| `deployment-patterns` | What happens after the report says READY. |

---

### Checklist

- [ ] Phases ran in order, and the first hard failure stopped the run.
- [ ] The build ran from clean, not incrementally.
- [ ] Static analysis is at zero findings, with nothing newly suppressed.
- [ ] The full suite is green and coverage cleared the threshold without the threshold moving.
- [ ] Dependency and secret scans are clean, and any suppression has an expiry and a ticket.
- [ ] The formatter produces no diff.
- [ ] The whole diff was read, and every changed file belongs to the task.
- [ ] The report uses the template, every value is measured, and the verdict matches the gates.
