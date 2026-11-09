# Running the tools

How to run Robert C. Martin's crapper, dryer and mutator through the wrapper in `.metrics/tools/`, and what each run leaves behind.

---

### The three commands

Every command measures the project that holds the `.metrics/` folder, from any working directory. On Linux and macOS:

```bash
.metrics/tools/run measure
```

```bash
.metrics/tools/run summary
```

```bash
.metrics/tools/run mutate --changed
```

On Windows, from PowerShell or cmd, call `run.cmd` instead:

```powershell
.metrics\tools\run.cmd measure
```

From Git Bash, which is the shell Claude Code's Bash tool runs on Windows, call the POSIX launcher, `.metrics/tools/run measure`, which hands the path to `run.py` through Git Bash's own path conversion. When it stops with exit 2 because only the `py` launcher is installed, go through `cmd` instead:

```bash
cmd //c .metrics\\tools\\run.cmd measure
```

| Command | Use it for |
|---|---|
| `measure` | The first run and the last one: crapper and dryer over the whole project, then mutator on the coverage crapper wrote. Writes `.metrics/crap.edn`, `.metrics/dry.edn` and `.metrics/mutate/` |
| `mutate --changed` | Each fix round: mutator alone with fresh coverage, on the source files git reports as changed |
| `mutate` | mutator alone on every file. Once a snapshot exists it reruns the survivors and the functions whose text changed |
| `summary` | The worst entries of all three score files as plain text. `--limit N` sets how many per section, 10 by default |

---

### Exit codes

| Code | Meaning | What to do |
|---|---|---|
| 0 | The run finished | Read `summary`. Surviving mutants after `measure` are data, not an error |
| 1 | A tool or a setup step failed | Read the output above the last line: a failing baseline test, a build error, a missing coverage report, or no network for the first run |
| 2 | Usage error, or no Python 3.11 or newer | Fix the command, or install Python |
| 3 | `mutate` left a surviving mutant | Write the test that kills it |

A failing project test makes mutator stop with "Baseline failed". Fix the tests first, because no mutant can be judged against a red suite.

---

### The first run on a machine

The first run needs network access to PyPI and to GitHub releases. The wrapper builds one virtual environment per tool, under `.metrics/tools/<tool>/.venv`, from the pinned `constraints.txt`, and the parsing library downloads its grammars, about 23 MB, into the machine's shared cache once. Later runs reuse both, and a newer Python or a newer pinned version rebuilds them.

It also readies the project without asking:

- one `target/` line in the root `.gitignore`, because the tools write coverage data and mutation workers into `target/`, unless the project already ignores it
- a `.venv` beside a Python project that has none, with the project's requirements and the pinned `coverage` and `pytest`, because mutator otherwise runs the tests with its own interpreter, and a line for it in the root `.gitignore`, such as `.venv/` or `services/api/.venv/`, unless the project already ignores it
- `npm ci`, or `npm install` without a lockfile, when `node_modules` is missing
- for Gradle, a JaCoCo report block appended once to `build.gradle` or `build.gradle.kts`, which writes the XML where crapper and mutator read it. Commit that change on its own
- the coverage tool a language needs, such as coverage.py, the Vitest coverage provider or cargo-llvm-cov, which crapper installs itself

---

### When the tools are missing

`.metrics/tools/run` missing means the project has the skill but not the tools. Get them before anything else, in this order:

1. Installed as a Claude Code plugin, this skill's own folder holds them under `tools/`. Copy that folder to `.metrics/tools/` in the project. With a POSIX shell, from the project root: `mkdir -p .metrics && cp -R "<this skill's folder>/tools" .metrics/tools`. With PowerShell: `New-Item -ItemType Directory -Force .metrics; Copy-Item -Recurse "<this skill's folder>\tools" .metrics\tools`.
2. A project that imports agent-standards with git takes them from its `agent-standards` remote: `git checkout agent-standards/master -- .metrics/tools`.
3. Neither works: stop and return the question to the caller. Never fetch the tools from anywhere else or write a substitute.

---

### Windows

The wrapper runs on Windows, and builds each tool's environment with `Scripts\python.exe`. Two things differ:

- mutator runs each mutant in a copy of the project built from symbolic links, and Windows lets an account create one only with Developer Mode on (Settings, System, For developers) or from a terminal started as administrator. The wrapper tries one first. When Windows refuses, it prints the Developer Mode fix, skips mutator and exits 1. Report that message to the caller as the fix, because a subagent cannot change the setting.
- The tools start `mvn`, `npm` and `npx` in a way Windows cannot run, so the wrapper passes its own Maven, npm and Python commands to the tools. A Python project tested from more than one folder gets no working mutator run on Windows, and the wrapper says so.

---

### What to commit

| Path | Commit it |
|---|---|
| `.metrics/crap.edn`, `.metrics/dry.edn`, `.metrics/mutate/` | Yes, from a `measure` run, so later reviews can cite them |
| `.metrics/tools/` | Yes, as the import delivered it, never edited |
| The JaCoCo block in a Gradle build file | Yes, in its own commit |
| The `target/` and `.venv/` lines the wrapper added to the root `.gitignore` | Yes, with the first scores |
| `target/`, the project `.venv` the wrapper created, each tool's `.venv` | Never. The ignore lines keep them out |
