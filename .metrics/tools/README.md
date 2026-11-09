# Quality tools

The three measuring tools of the quality loop, by Robert C. Martin (Uncle Bob), copied here unchanged so every project measures its code the same way. The method and the tools are his work. agent-standards only packages them.

---

### What is here

| Path | What it is | Author |
| --- | --- | --- |
| [crapper/](crapper/) | Scores every function by complexity and test coverage, the CRAP metric, into `.metrics/crap.edn`. Source: [github.com/unclebob/crapper](https://github.com/unclebob/crapper) | Robert C. Martin, 0BSD |
| [dryer/](dryer/) | Lists pairs of functions with the same structure into `.metrics/dry.edn`. Source: [github.com/unclebob/dryer](https://github.com/unclebob/dryer) | Robert C. Martin, 0BSD |
| [mutator/](mutator/) | Plants small bugs, runs the tests, and records every mutant the tests miss under `.metrics/mutate/`. Source: [github.com/unclebob/mutator](https://github.com/unclebob/mutator) | Robert C. Martin, 0BSD |
| [VERSIONS](VERSIONS) | The upstream repository and the pinned commit of each tool | agent-standards |
| [constraints.txt](constraints.txt) | The pinned Python library versions every tool environment is installed with | agent-standards |
| [.gitignore](.gitignore) | Keeps each tool's `.venv`, caches and build metadata out of git | agent-standards |
| [.gitattributes](.gitattributes) | Checks `run.cmd` out with CRLF and `run` with LF in any project, and marks the folder vendored for GitHub | agent-standards |
| [run](run), [run.cmd](run.cmd), [run.py](run.py), [quality_loop/](quality_loop/) | The wrapper that builds each tool's environment, readies the project and runs the tools | agent-standards |

Each tool keeps its own `LICENSE` file, the BSD Zero Clause License, Copyright Robert C. Martin.

---

### How to run

The `quality-loop` subagent runs these. Each command works from any folder and measures the project that holds this `.metrics/` folder. On Linux and macOS:

```bash
.metrics/tools/run measure
```

```bash
.metrics/tools/run summary
```

```bash
.metrics/tools/run mutate --changed
```

On Windows, from PowerShell or cmd:

```powershell
.metrics\tools\run.cmd measure
```

From Git Bash, the shell Claude Code's Bash tool uses on Windows, run `.metrics/tools/run measure`. With only the `py` launcher installed, `run` stops with exit 2, so go through `cmd`:

```bash
cmd //c .metrics\\tools\\run.cmd measure
```

| Command | What it does |
| --- | --- |
| `measure` | Runs crapper and dryer over the whole project and mutator on the coverage crapper wrote, and writes `.metrics/crap.edn`, `.metrics/dry.edn` and `.metrics/mutate/` |
| `mutate --changed` | Runs mutator alone, with fresh coverage, on the source files git reports as changed |
| `summary` | Prints the worst entries of the three score files as plain text. `--limit N` sets how many per section |

Exit status: 0 the run finished, 1 a tool or a setup step failed, 2 a usage error or no Python 3.11, 3 `mutate` left a surviving mutant.

The first run on a machine needs network access. It builds `<tool>/.venv` for each tool with the pinned [constraints.txt](constraints.txt), and the parsing library downloads about 23 MB of grammars into the machine's shared cache, once per machine. It also readies the project: a `target/` line in `.gitignore`, because the tools write their working files there, a `.venv` beside a Python project that has none, with its own `.gitignore` line, `npm ci` when `node_modules` is missing, and for Gradle a JaCoCo report block appended to `build.gradle` or `build.gradle.kts` once.

---

### What the wrapper fixes

| Problem in running the tools | What the wrapper does |
| --- | --- |
| Each tool's launcher is a POSIX `sh` script that installs loose library versions | Builds each environment itself with the pinned versions, `Scripts\python.exe` on Windows and `bin/python` elsewhere, and starts each tool as `python -m <tool>` |
| Neither crapper nor mutator knows Gradle | Adds the JaCoCo report block and passes `gradle --no-daemon test jacocoTestReport` and `gradle --no-daemon -q --offline --rerun-tasks test`, through `gradlew` when the project has one |
| A Gradle daemon started by a mutant's build outlives it and keeps writing into the worker folder mutator then deletes, which crashes mutator with "Directory not empty" | Passes `--no-daemon` to every Gradle command it builds, on every system |
| A Java mutant whose fresh worker compiles from scratch can outrun ten times an up-to-date baseline, and count as killed | Passes `--rerun-tasks` to Gradle and `--timeout-factor 30` for Java |
| A failed coverage command makes crapper score every function at 0% without failing | Removes stale reports first, and fails the run when no new report was written |
| A partial crapper run replaces `.metrics/crap.edn` with a subset, and `crapper --changed` scans this folder | Runs crapper in full every time, never with `--changed` |
| mutator runs Python tests with its own interpreter when the project has no `.venv` | Creates the project's `.venv` with the pinned `coverage` and `pytest`, and adds it to the root `.gitignore` unless git already ignores it |
| On Windows the tools start `mvn`, `npm` and `npx` without a shell, which cannot run `mvn.cmd` or `npm.cmd`, and look for the project's Python only under `.venv/bin` | Passes the Maven, npm and Python commands through `--coverage-command` and `--test-command`, which run in a shell |
| On Windows mutator stops a timed-out mutant with `os.killpg` and `signal.SIGKILL`, which Python offers on Unix only | Starts mutator through [quality_loop/mutator_windows.py](quality_loop/mutator_windows.py), which kills the process tree with `taskkill` instead |

---

### Windows

mutator runs every mutant in a copy of the project built from symbolic links, and Windows lets an account create one only with Developer Mode on or from a terminal started as administrator: an unelevated process may create one only once "[Developer Mode](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createsymboliclinkw) must first be enabled on the machine". The wrapper tries one first and, when Windows refuses, prints the fix, skips mutator and exits 1. Turn on Developer Mode in Settings, System, For developers, then open a new terminal. The GitHub Windows runner the agent-standards checks use runs as an elevated administrator, so it needs neither.

The agent-standards checks run Python and Java with Gradle on Windows. Maven, TypeScript and JavaScript take the wrapper's shell commands and Go and Rust ship real executables, but none of them is checked on Windows, and Clojure needs a `clj` executable on `PATH`. On Windows a Python project tested from more than one folder gets no working mutator run, and the wrapper says so.

---

### If your linters see it

This folder holds about 15,700 lines of Python, Robert C. Martin's and the wrapper's, written to their own style rather than your project's. [.gitattributes](.gitattributes) marks every file here `linguist-vendored`, which keeps it out of GitHub's language statistics, but a linter or a scanner pointed at the whole project still reads it. Leave it out in each tool's own setting:

| Tool | Setting | Source |
| --- | --- | --- |
| Ruff | `extend-exclude = [".metrics"]` under `[tool.ruff]` | [extend-exclude](https://docs.astral.sh/ruff/settings/#extend-exclude) |
| Black | `extend-exclude = '^/\.metrics/'` under `[tool.black]` | [--extend-exclude](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#extend-exclude) |
| mypy | `exclude = ['^\.metrics/']` under `[tool.mypy]` | [exclude](https://mypy.readthedocs.io/en/stable/config_file.html#confval-exclude) |
| CodeQL | `paths-ignore: [.metrics/tools]` in the code scanning configuration file | [Specifying directories to scan](https://docs.github.com/en/code-security/code-scanning/creating-an-advanced-setup-for-code-scanning/customizing-your-advanced-setup-for-code-scanning#specifying-directories-to-scan) |

mypy already skips a folder whose name starts with a dot when it walks a directory, so its `exclude` matters only when its `files` setting or its command line names `.metrics`. CodeQL honours `paths-ignore` for Python, JavaScript and TypeScript, and for a compiled language only when it analyses without building.

---

### Why the code is copied unchanged

Fixes for running his tools in a project belong in the agent-standards wrapper beside them, never in his code. That keeps every update a plain copy of a newer commit, with no patch to carry forward and nothing to merge.

---

### How to update

Never edit anything under [crapper/](crapper/), [dryer/](dryer/) or [mutator/](mutator/) by hand. In agent-standards, the maintainer script `tools/update_quality_tools.py` copies a newer pinned commit of each repository, rewrites [VERSIONS](VERSIONS) and [constraints.txt](constraints.txt), and runs the checks. A project that imported agent-standards takes the new copy with its normal update, which removes the three tool folders and checks out `.metrics/tools` again, so a file upstream deleted goes too. The script replaces only the three tool folders and keeps every other file here.
