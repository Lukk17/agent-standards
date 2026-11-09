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

Each tool keeps its own `LICENSE` file, the BSD Zero Clause License, Copyright Robert C. Martin.

---

### Why the code is copied unchanged

Fixes for running his tools in a project belong in the agent-standards wrapper beside them, never in his code. That keeps every update a plain copy of a newer commit, with no patch to carry forward and nothing to merge.

---

### How to update

Never edit anything under [crapper/](crapper/), [dryer/](dryer/) or [mutator/](mutator/) by hand. In agent-standards, the maintainer script `tools/update_quality_tools.py` copies a newer pinned commit of each repository, rewrites [VERSIONS](VERSIONS) and [constraints.txt](constraints.txt), and runs the checks. A project that imported agent-standards takes the new copy with its normal update, which checks out `.metrics/tools` again.
