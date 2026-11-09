# Reading the scores

What the three score files hold, how `summary` prints them, and the bands that decide what must be fixed. Start with `summary`, and open a file only for detail it leaves out.

---

### `summary`

`summary` prints three sections, worst first, each cut to `--limit` entries:

```text
CRAP (.metrics/crap.edn): 5 functions, 1 over 30, 1 from 10 to 30
     42.0  cc   6  cov   0.0%  sample.Rules.shippingCost  must fix, over 30
     12.0  cc   3  cov   0.0%  sample.Rules.basketTotal  over the goal of 10

Duplicates (.metrics/dry.edn): 1 pair at or above 0.82
  1.00  src/main/java/sample/Rules.java:39-48  and  src/main/java/sample/Rules.java:51-60

Mutants (.metrics/mutate/): 1 survived, 4 sites no test reaches
  src/main/java/sample/Rules.java:15  isAdult  >= -> >
```

A CRAP line names the function as namespace and name, with its complexity and coverage. A duplicate line names both spans. A mutant line names the file and line, the function, and the change mutator made that no test noticed.

---

### The bands

| Score | Band | Action |
|---|---|---|
| CRAP over 30 | complex and under-tested | Must fix |
| CRAP from 10 to 30 | worth a look | Fix in code the change touched, aiming under 10 |
| CRAP under 10 | fine | Leave it |
| A surviving mutant | a test the project is missing | None may survive in code the change touched |
| A site no test reaches | uncovered | Its CRAP score already shows it. Cover it when the function is in the change |
| A duplicate pair at or above 0.82 | candidate duplicate | Review it, merge only one rule |

CRAP is `CC^2 * (1 - coverage)^3 + CC`, with coverage as a fraction, so a function at 100% coverage scores its own complexity, and a complex function with no tests scores far over 30. Splitting the function lowers CC, and a test raises coverage. A score cannot go under the function's complexity.

---

### The files

All three are EDN, written by the tools and committed.

`.metrics/crap.edn` holds one entry per function, rewritten in full by every crapper run:

```clojure
{:entries [{:name "shippingCost", :namespace "sample.Rules", :complexity 6, :coverage 0.0, :crap 42.0}]}
```

The namespace is the dotted module path or the class, so find the file by searching for the function name. `:coverage nil` means coverage was not measured.

`.metrics/dry.edn` holds one candidate per pair, with both spans:

```clojure
{:candidates [{:score 1.0 :language "java" :left {:file "src/A.java", :start-line 39, :end-line 48} :right {...}}]}
```

`.metrics/mutate/` holds one file per namespace. `:forms` counts killed, survived and uncovered sites per function, and `:outcomes` maps each mutation to `:killed` or `:survived`. The mutation key is a JSON list: file, namespace, function, start and end byte offsets, the original text and the mutant. `summary` turns the offset into a line number.

---

### When a score looks wrong

- Every function of one language at 0% coverage: the coverage run failed. `measure` says "No <language> coverage report was written" and exits 1. Fix the build or the tests and measure again.
- A file missing from `.metrics/crap.edn`: it sits in a folder the tools skip, such as `test`, `tests`, `target`, `build`, `vendor` or `node_modules`, or its language is not supported.
- "Baseline failed" from mutator: a project test fails without any mutant. Fix it first.
