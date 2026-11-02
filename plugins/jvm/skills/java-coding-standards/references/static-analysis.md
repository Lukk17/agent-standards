# Static Analysis and Build Output

The tools that enforce this style automatically, and how to keep their output readable. Open this when setting the
gates up on a new project, or when a finding needs a decision rather than a suppression.

---

### The three tools and what each one is for

| Tool | What it catches | Gate |
| --- | --- | --- |
| Checkstyle | Formatting and naming, against Google Java Style or the project ruleset. | Fail the build. |
| SpotBugs | Bug patterns in bytecode: null dereferences, resource leaks, bad equals contracts. | Fail on `HIGH` and `MEDIUM`. |
| PMD | Copy-paste detection and the code smells the other two miss. | Fail the build. |

Wire them into the build with the plugin identifiers below, and take every version from the project version
catalog rather than writing it into a module build file. `build-dependency-management` owns that rule, and a
version pinned here is a version nobody remembers to bump.

```kotlin
plugins {
    checkstyle
    pmd
    id("com.github.spotbugs")
}
```

```kotlin
checkstyle {
    toolVersion = libs.versions.checkstyle.get()
    isIgnoreFailures = false
}
```

```kotlin
spotbugs {
    effort = com.github.spotbugs.snom.Effort.MAX
    reportLevel = com.github.spotbugs.snom.Confidence.MEDIUM
}
```

```kotlin
pmd {
    isIgnoreFailures = false
    ruleSetFiles = files("config/pmd/ruleset.xml")
}
```

---

### Treat a finding as a decision, not as noise

A finding gets fixed, or it gets a suppression that names the reason and carries an expiry. A suppression file that
grows every sprint is the gate failing quietly, which is worse than not having it.

Turn a rule off project-wide only when the team has decided the rule does not apply to this codebase, and record
that decision where architecture decisions live rather than in a comment beside the suppression.

---

### Keep build output readable

A full Gradle run floods a terminal and buries the one line that matters. Redirect it to a file and read the file.

```bash
./gradlew build > build_log.txt 2>&1
```

The redirect overwrites the file, so it always holds exactly the most recent run and there is no ambiguity about
which failure you are looking at. Add the log file to the ignore list, since it is build output.
